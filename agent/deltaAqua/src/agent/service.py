import json
import re
import boto3
import time
import asyncio
from typing import List, Any, Literal, Optional, Dict
from pydantic import BaseModel, Field
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from composio import Composio
from composio_langgraph import LanggraphProvider

from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver
import instructor

from .client import get_bedrock_client, get_memory_client, get_pinecone_index, get_composio_client, get_executor
from rag.client import RAGClient, RAGTool
from .prompts import (
    ANALYSIS_SYSTEM_PROMPT, 
    EXECUTION_SYSTEM_PROMPT, 
    COGNIVE_INTRO, 
    COGNIVE_CAPABILITIES_GENERAL,
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
    relevant_toolkit: str = Field(description="The ONE best toolkit to use")
    selected_slugs: List[str] = Field(description="List of up to 5 best tool slugs to use")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level")
    reasoning: str = Field(description="Why this toolkit and these tools were chosen")
    intent: str = Field(description="What user wants to accomplish")


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
        context_parts = []
        if preferences:
            context_parts.append(f"Preferences: {preferences}")
        if semantic_context:
            context_parts.append(f"Context: {semantic_context}")
        
        user_context = "\n".join(context_parts) if context_parts else "No prior context"
        
        tools_by_toolkit = {}
        for t in rag_tools:
            if t.toolkit not in tools_by_toolkit:
                tools_by_toolkit[t.toolkit] = []
            tools_by_toolkit[t.toolkit].append(t)
        
        tools_formatted = []
        for toolkit_name, tools in sorted(tools_by_toolkit.items(), key=lambda x: max(t.score for t in x[1]), reverse=True):
            tools_formatted.append(f"\n--- TOOLKIT: {toolkit_name.upper()} ---")
            for t in sorted(tools, key=lambda x: x.score, reverse=True):
                tools_formatted.append(f"Slug: {t.tool_slug}")
                tools_formatted.append(f"Description: {t.description}")
                if t.feature:
                    tools_formatted.append(f"Feature: {t.feature}")
                tools_formatted.append("") 
        
        system_prompt = ANALYSIS_SYSTEM_PROMPT

        user_prompt = f"""USER REQUEST: "{user_message}"

CONTEXT: {user_context}

RAG RESULTS:
{'\n'.join(tools_formatted)}

Choose ONE toolkit that best matches the request."""
        
        try:
            return self.client.chat.completions.create(
                model=settings.BEDROCK_MODEL_ID,
                response_model=AnalysisOutput,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000
            )
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            best_toolkit = max(tools_by_toolkit.items(), key=lambda x: max(t.score for t in x[1]))[0]
            top_slugs = [t.tool_slug for t in sorted(tools_by_toolkit[best_toolkit], key=lambda x: x.score, reverse=True)[:5]]
            return AnalysisOutput(
                relevant_toolkit=best_toolkit,
                selected_slugs=top_slugs,
                confidence="low",
                reasoning=ANALYSIS_FALLBACK_REASONING,
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
        self._router_llm = ChatBedrockConverse(
            client=get_bedrock_client(),
            model_id=settings.BEDROCK_MODEL_ID,
            temperature=0,
            max_tokens=256,
        )
        logger.info("Initialized 2-agent system with Collapsed Analysis and AgentCore Memory")

    def _classify_intent(self, user_message: str) -> str:
        system_prompt = "You are an intent classifier. Reply with exactly one word only, no punctuation, no explanation. Your only valid responses are: identity, capabilities, task. identity = user is asking who or what you are. capabilities = user is asking what you can do or help with. task = anything else."
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Classify this message: {user_message}")
        ]
        try:
            response = self._router_llm.invoke(messages)
            content = response.content
            if isinstance(content, list):
                content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
            
            content = str(content).strip().lower()
            if "identity" in content:
                return "identity"
            if "capabilities" in content or "capability" in content:
                return "general_capabilities"
            return "task"
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "task"

    async def execute_task(self, user_message: str, user_id: str, conversation_id: str, chat_name: str = None) -> dict:
        start = time.time()
        try:
            try:
                chat_name = self.chat_memory.get_chat_name(user_id, conversation_id)
            except Exception as e:
                logger.error(f"Failed to retrieve chat name from STM: {e}")
            
            # PERSONALITY ROUTING
            stream_event(conversation_id, "init", "Classifying conversational intent...")
            intent = await asyncio.get_event_loop().run_in_executor(
                _executor, lambda: self._classify_intent(user_message)
            )
            logger.info(f"Intent: {intent}")

            if intent == "identity":
                response = COGNIVE_INTRO
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

            if intent == "general_capabilities":
                response = COGNIVE_CAPABILITIES_GENERAL
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
            
            # PARALLEL PREP PHASE
            stream_event(conversation_id, "init", "Searching knowledge base for accessible tools...")
            rag_task = self.rag.search_tools(user_message, top_k=5)
            pref_task = self.analysis_agent._retrieve_memories(f"/users/{user_id}/preferences", "user preferences")
            context_task = self.analysis_agent._retrieve_memories(f"/semantic/{user_id}", user_message)

            rag_tools, preferences, semantic_context = await asyncio.gather(
                rag_task, pref_task, context_task
            )
            
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
            stream_event(conversation_id, "init", f"Identified '{intent}' intent. Selecting optimal tools & strategies...")
            analysis = await self.analysis_agent.analyze(
                user_message, user_id, rag_tools, 
                preferences=preferences, 
                semantic_context=semantic_context
            )
            logger.info(f"Analysis: {analysis.relevant_toolkit} ({analysis.confidence})")
            
            toolkit = analysis.relevant_toolkit
            selected_slugs = analysis.selected_slugs

            try:
                stream_event(conversation_id, "init", f"Initializing Native Tools for {toolkit.title()}...")
                
                # 1. Create session - manage_connections=False prevents intercepting output
                session = self.sdk.create(
                    user_id=user_id, 
                    toolkits=[toolkit],
                    manage_connections={"callback_url": settings.CALLBACK_URL}
                )

                # 2. Check connection status BEFORE fetching tools to avoid 400 error
                toolkits_data = session.toolkits()
                is_connected = any(
                    t.slug.lower() == toolkit.lower() and t.connection and t.connection.is_active 
                    for t in toolkits_data.items
                )
                
                if not is_connected:
                    stream_event(conversation_id, "init", f"Requesting connection for {toolkit.title()}...")
                    auth_request = session.authorize(toolkit.lower())
                    if auth_request and auth_request.redirect_url:
                        logger.info(f"Account {toolkit} disconnected. Auth URL: {auth_request.redirect_url}")
                        return {
                            "response": f"I need to connect your {toolkit.title()} account to proceed. Please authenticate using the link below:\n\n**[Connect {toolkit.title()}]({auth_request.redirect_url})**",
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
                        tools = [*self.sdk.tools.get(user_id=user_id, toolkits=[toolkit])][:5]
                else:
                    tools = [*self.sdk.tools.get(user_id=user_id, toolkits=[toolkit])][:5]

            except Exception as e:
                logger.error(f"Composio Tool retrieval failed: {e}")
                return {
                    "response": TOOLKIT_INIT_FAILED.format(toolkit=toolkit),
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False,
                    "chatName": chat_name
                }
            
            if not tools:
                return {
                    "response": NO_TOOLS_IN_TOOLKIT.format(toolkit=toolkit),
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False,
                    "chatName": chat_name
                }
            
            logger.info(f"Loaded {len(tools)} tools for {toolkit}")
            
            stream_event(conversation_id, "execute", f"Loading '{toolkit}' functionality and initializing Execution Agent...")
            
            final = await self.execution_agent.execute(user_message, tools, user_id, conversation_id)
            
            stream_event(conversation_id, "completed", "Task completed.")
            logger.info(f"Completed in {time.time() - start:.2f}s")
            
            return {
                "response": final,
                "awaiting_user": False,
                "rag_tools_found": len(rag_tools),
                "rag_tool_names": [t.tool_slug for t in rag_tools],
                "toolkits_used": [toolkit],
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