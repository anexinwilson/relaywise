import json
import re
import boto3
import logging
import time
import asyncio
import os
from typing import List, Any, Literal, Optional, Dict
from pydantic import BaseModel, Field
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from composio import Composio
from composio_langgraph import LanggraphProvider

from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver
import instructor

from .client import get_bedrock_client, get_memory_client, get_pinecone_index, get_composio_client, get_redis_client, get_executor
from .sync import sync_connections_to_redis, disconnect_app, check_app_limit
from rag.client import RAGClient, RAGTool
from .prompts import (
    ANALYSIS_SYSTEM_PROMPT, 
    EXECUTION_SYSTEM_PROMPT, 
    COGNIVE_INTRO, 
    COGNIVE_CAPABILITIES_GENERAL,
    COGNIVE_FAQ,
    NO_TOOLS_FOUND,
    TOOLKIT_INIT_FAILED,
    NO_TOOLS_IN_TOOLKIT,
    ANALYSIS_FALLBACK_REASONING,
    GENERIC_ERROR_MESSAGE
)

from config import settings
from utils import get_logger
from memory import ChatMemory
from agent.chat_namer import ChatNamer
from agent.event_streaming import stream_event
from langchain_core.callbacks import AsyncCallbackHandler

logger = get_logger(__name__)

_executor = get_executor()

class AnalysisOutput(BaseModel):
    relevant_toolkits: List[str] = Field(description="List of toolkits to use for this task")
    selected_slugs: List[str] = Field(description="List of up to 5 best tool slugs to use")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level")
    reasoning: str = Field(description="Why this toolkit and these tools were chosen")
    intent: str = Field(description="What user wants to accomplish")

class IntentOutput(BaseModel):
    intent: Literal["identity", "capabilities", "task"]
    toolkits: List[str] = Field(description="List of up to 2 best matching toolkit slugs from the catalog")


class AnalysisAgent:
    def __init__(self):
        bedrock_client = get_bedrock_client()
        self.client = instructor.from_bedrock(bedrock_client, model=settings.BEDROCK_MODEL_ID)
        self.memory_client = get_memory_client()
    
    async def _retrieve_memories(self, namespace: str, query: str) -> List:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                self.memory_client.retrieve_memories,
                settings.AGENTCORE_MEMORY_ID,
                namespace,
                query,
                3
            )
        except:
            return []
    
    async def analyze(self, user_message: str, user_id: str, rag_tools: List[RAGTool], preferences: List = None, semantic_context: List = None) -> AnalysisOutput:
        if not rag_tools:
            return AnalysisOutput(relevant_toolkits=[], selected_slugs=[], confidence="low", reasoning="No tools found in RAG.", intent=user_message)

        candidates = []
        for i, tool in enumerate(rag_tools, 1):
            candidates.append(f"### Tool {i} | Slug: {tool.tool_slug} | App: {tool.toolkit}\n{tool.description}")

        tools_context = "\n---\n".join(candidates)
        
        system_prompt = ANALYSIS_SYSTEM_PROMPT.format(tools_formatted=tools_context)
        
        try:
            return self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                response_model=AnalysisOutput,
            )
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            # Fallback: Pick top app and first 3 slugs
            top_toolkit = list(set(t.toolkit for t in rag_tools))[:1]
            top_slugs = [t.tool_slug for t in rag_tools][:3]
            return AnalysisOutput(
                relevant_toolkits=top_toolkit,
                selected_slugs=top_slugs,
                confidence="low",
                reasoning=f"Fallback due to analysis error: {str(e)}",
                intent=user_message
            )

class BroadcastCallbackHandler(AsyncCallbackHandler):
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id

    async def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> Any:
        tool_name = serialized.get("name", "tool")
        stream_event(self.conversation_id, "execute", f"Executing action: {tool_name}...")
    
    async def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        stream_event(self.conversation_id, "execute", "Tool execution completed.")

class ExecutionAgent:
    def __init__(self):
        self.llm = ChatBedrockConverse(
            client=get_bedrock_client(),
            model_id=settings.BEDROCK_MODEL_ID,
            temperature=0,
            max_tokens=4096,
        )
        self.memory_client = get_memory_client()
    
    async def _create_event(self, actor_id: str, session_id: str, messages: List):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _executor,
                self.memory_client.create_event,
                settings.AGENTCORE_MEMORY_ID,
                actor_id,
                session_id,
                messages
            )
        except:
            pass

    async def execute(self, user_message: str, tools: List[Any], user_id: str, conversation_id: str) -> str:
        checkpointer = AgentCoreMemorySaver(
            memory_id=settings.AGENTCORE_MEMORY_ID,
            region_name=settings.AWS_REGION
        )
        
        system_prompt = EXECUTION_SYSTEM_PROMPT.format(user_message=user_message)

        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=checkpointer,
            prompt=system_prompt
        )

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=user_message)]},
            config={
                "configurable": {"thread_id": conversation_id, "actor_id": user_id},
                "cache": "enabled",
                "callbacks": [BroadcastCallbackHandler(conversation_id)]
            }
        )

        final = result["messages"][-1].content
        if isinstance(final, list):
            final = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in final])

        chat_memory = ChatMemory()
        chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
        chat_memory.store_message(user_id, conversation_id, final, 'ASSISTANT')

        return final

class AgentService:
    def __init__(self):
        self.rag = RAGClient()
        self.sdk = Composio(provider=LanggraphProvider())
        self.analysis_agent = AnalysisAgent()
        self.execution_agent = ExecutionAgent()
        self.chat_memory = ChatMemory()
        self.chat_namer = ChatNamer()
        self._router_llm = instructor.from_bedrock(
            get_bedrock_client(), 
            model=settings.BEDROCK_MODEL_ID
        )
        
        # Load toolkits catalog
        catalog_path = os.path.join(os.path.dirname(__file__), "toolkits_catalog.json")
        try:
            with open(catalog_path, "r") as f:
                self.toolkits_catalog = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load toolkits catalog: {e}")
            self.toolkits_catalog = []


    def _classify_intent(self, user_message: str) -> IntentOutput:
        system_prompt = f"""You are a high-performance intent classifier and app router.
Your job is to:
1. Classify the user's intent: 'identity' (who you are), 'capabilities' (what you can do), or 'task' (actions/searches).
2. Extract the best matching toolkit slugs from the CATALOG. Return 1 slug if only one app is clearly meant, or 2 if the user mentions a brand that has both a user-facing app AND a bot variant (e.g., Slack + Slackbot, Discord + Discordbot).

RULES:
- **Precision First**: If a user names a specific app, return ONLY that app's slug. Do NOT pad with loosely related apps.
- **Bot Variants Only**: Return 2 slugs ONLY when the brand has a known user+bot pair (e.g., Slack→['slack','slackbot'], Discord→['discord','discordbot']).
- **Valid Slugs Only**: Return EXACT slugs from the CATALOG.

CATALOG:
{json.dumps(self.toolkits_catalog)}

EXAMPLES:
- User: "Fetch discord messages" -> intent="task", toolkits=["discord", "discordbot"]
- User: "Search my spreadsheet" -> intent="task", toolkits=["googlesheets"]
- User: "Send a LinkedIn message" -> intent="task", toolkits=["linkedin"]
- User: "Who are you?" -> intent="identity", toolkits=[]
"""
        try:
            return self._router_llm.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                response_model=IntentOutput,
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentOutput(intent="task", toolkits=[])

    async def execute_task(self, user_message: str, user_id: str, conversation_id: str, chat_name: str = None) -> dict:
        start = time.time()
        try:
            try:
                chat_name = self.chat_memory.get_chat_name(user_id, conversation_id)
            except Exception as e:
                logger.error(f"Failed to retrieve chat name from STM: {e}")
            
            # Sync connections to Redis asynchronously
            asyncio.create_task(sync_connections_to_redis(user_id))
            
            # Step 1: Merged Routing & RAG
            intent_output = self._classify_intent(user_message)
            logger.info(f"Intent: {intent_output.intent} toolkits={intent_output.toolkits}")

            # --- Personality Routing (before RAG to avoid wasted work) ---
            if intent_output.intent == 'identity':
                # Check for FAQ match first
                msg_lower = user_message.lower()
                faq_response = None
                for key, answer in COGNIVE_FAQ.items():
                    if key in msg_lower or any(word in msg_lower for word in key.split('_')):
                        faq_response = answer
                        break
                response = faq_response if faq_response else COGNIVE_INTRO
                self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
                self.chat_memory.store_message(user_id, conversation_id, response, 'ASSISTANT')
                return {
                    "response": response,
                    "awaiting_user": False,
                    "rag_tools_found": 0,
                    "rag_tool_names": [],
                    "success": True,
                    "chatName": chat_name,
                    "personality_response": True
                }

            if intent_output.intent == 'capabilities':
                self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
                self.chat_memory.store_message(user_id, conversation_id, COGNIVE_CAPABILITIES_GENERAL, 'ASSISTANT')
                return {
                    "response": COGNIVE_CAPABILITIES_GENERAL,
                    "awaiting_user": False,
                    "rag_tools_found": 0,
                    "rag_tool_names": [],
                    "success": True,
                    "chatName": chat_name,
                    "personality_response": True
                }

            # --- Task Routing: RAG + Analysis ---
            stream_event(conversation_id, "init", "Searching knowledge base for accessible tools...")

            rag_tools = []
            if intent_output.toolkits:
                rag_tools = await self.rag.search_tools(
                    user_message,
                    top_k=15,
                    filter={"toolkit": {"$in": intent_output.toolkits[:2]}}
                )
                logger.info(f"RAG: Found {len(rag_tools)} tools in {intent_output.toolkits[:2]}")
            else:
                rag_tools = await self.rag.search_tools(user_message, top_k=15)

            pref_task = self.analysis_agent._retrieve_memories(f"/users/{user_id}/preferences", "user preferences")
            context_task = self.analysis_agent._retrieve_memories(f"/semantic/{user_id}", user_message)

            preferences, semantic_context = await asyncio.gather(pref_task, context_task)

            # Map intent for downstream log messages
            intent_str = intent_output.intent
            
            if not rag_tools:
                return {
                    "response": NO_TOOLS_FOUND,
                    "awaiting_user": False,
                    "rag_tools_found": 0,
                    "rag_tool_names": [],
                    "success": True,
                    "chatName": chat_name
                }
            
            logger.info(f"RAG: {len(rag_tools)} tools")
            
            # COLLAPSED LLM ANALYSIS 
            stream_event(conversation_id, "init", f"Identified '{intent_str}' intent. Selecting optimal tools & strategies...")
            analysis = await self.analysis_agent.analyze(
                user_message, user_id, rag_tools, 
                preferences=preferences, 
                semantic_context=semantic_context
            )
            logger.info(f"Analysis: {analysis.relevant_toolkits} ({analysis.confidence})")
            
            primary_toolkit = analysis.relevant_toolkits[0] if analysis.relevant_toolkits else "unknown"
            selected_slugs = analysis.selected_slugs

            try:
                stream_event(conversation_id, "init", f"Initializing Native Tools for {primary_toolkit.title()}...")
                
                # 1. Create session with all relevant toolkits
                session = self.sdk.create(
                    user_id=user_id, 
                    toolkits=analysis.relevant_toolkits,
                    manage_connections={"callback_url": settings.CALLBACK_URL}
                )

                # 2. Check connection status for ALL relevant toolkits
                toolkits_data = session.toolkits()
                for tk in analysis.relevant_toolkits:
                    is_connected = any(
                        t.slug.lower() == tk.lower() and t.connection and t.connection.is_active 
                        for t in toolkits_data.items
                    )
                    
                    if not is_connected:
                        # Check 5-app limit before authorizing new connection
                        if check_app_limit(user_id):
                            logger.info(f"User {user_id} hit 5-app limit")
                            return {
                                "response": "You've reached the limit of 5 connected apps. Please disconnect an app from the [Integrations Page](/integrations) before connecting a new one.",
                                "awaiting_user": False,
                                "rag_tools_found": len(rag_tools),
                                "rag_tool_names": [t.tool_slug for t in rag_tools],
                                "success": True,
                                "chatName": chat_name
                            }

                        stream_event(conversation_id, "init", f"Requesting connection for {tk.title()}...")
                        auth_request = session.authorize(tk.lower())
                        if auth_request and auth_request.redirect_url:
                            logger.info(f"Account {tk} disconnected. Auth URL: {auth_request.redirect_url}")
                            return {
                                "response": f"I need to connect your {tk.title()} account to proceed. Please authenticate using the link below:\n\n**[Connect {tk.title()}]({auth_request.redirect_url})**",
                                "awaiting_user": True,
                                "rag_tools_found": len(rag_tools),
                                "rag_tool_names": [t.tool_slug for t in rag_tools],
                                "success": False,
                                "chatName": chat_name,
                                "connection_url": auth_request.redirect_url
                            }
                
                # 3. Fetch ONLY the exact RAG-selected tool slugs directly as LangChain tools
                if selected_slugs:
                    try:
                        tools = [*self.sdk.tools.get(user_id=user_id, tools=selected_slugs)]
                        logger.info(f"Loaded {len(tools)} precise tools: {selected_slugs}")
                    except Exception as e:
                        logger.error(f"Failed to fetch precise tools {selected_slugs}, falling back to toolkit tools: {e}")
                        tools = [*self.sdk.tools.get(user_id=user_id, toolkits=analysis.relevant_toolkits)][:5]
                else:
                    tools = [*self.sdk.tools.get(user_id=user_id, toolkits=analysis.relevant_toolkits)][:5]

            except Exception as e:
                logger.error(f"Composio Tool retrieval failed: {e}")
                return {
                    "response": TOOLKIT_INIT_FAILED.format(toolkit=primary_toolkit),
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False,
                    "chatName": chat_name
                }
            
            if not tools:
                return {
                    "response": NO_TOOLS_IN_TOOLKIT.format(toolkit=primary_toolkit),
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False,
                    "chatName": chat_name
                }
            
            logger.info(f"Loaded {len(tools)} tools for {primary_toolkit}")
            
            stream_event(conversation_id, "execute", f"Loading '{primary_toolkit}' functionality and initializing Execution Agent...")
            
            final = await self.execution_agent.execute(user_message, tools, user_id, conversation_id)
            
            stream_event(conversation_id, "completed", "Task completed.")
            logger.info(f"Completed in {time.time() - start:.2f}s")
            
            return {
                "response": final,
                "awaiting_user": False,
                "rag_tools_found": len(rag_tools),
                "rag_tool_names": [t.tool_slug for t in rag_tools],
                "toolkits_used": analysis.relevant_toolkits,
                "success": True,
                "chatName": chat_name
            }
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            return {
                "response": GENERIC_ERROR_MESSAGE.format(error_msg=str(e)),
                "awaiting_user": False,
                "rag_tools_found": 0,
                "rag_tool_names": [],
                "success": False,
                "chatName": chat_name
            }

_agent_service = None

def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service