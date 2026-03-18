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
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langfuse import observe

from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver
import instructor

from .client import get_bedrock_client, get_memory_client, get_pinecone_index, get_composio_client, get_redis_client, get_executor
from .sync import sync_connections_to_redis, disconnect_app, check_app_limit
from rag.client import RAGClient, RAGTool
from .prompts import (
    INTENT_SYSTEM_PROMPT,
    ANALYSIS_SYSTEM_PROMPT, 
    EXECUTION_SYSTEM_PROMPT, 
    NO_TOOLS_FOUND,
    TOOLKIT_INIT_FAILED,
    NO_TOOLS_IN_TOOLKIT,
    ANALYSIS_FALLBACK_REASONING,
    GENERIC_ERROR_MESSAGE,
)

from config import settings
from utils import get_logger
from memory import ChatMemory
from memory.context_manager import ContextManager
from agent.chat_namer import ChatNamer
from agent.event_streaming import stream_event
from agent.personality import PersonalityHandler
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
    intent: Literal["greeting", "identity", "user_identity", "capabilities", "task"]
    app_mentioned: bool = Field(description="True if user explicitly mentioned an app name")
    app_slugs: List[str] = Field(default_factory=list, description="List of app slugs if user mentioned specific apps")
    relevant_categories: List[str] = Field(default_factory=list, description="Relevant app categories (email, team chat, etc.)")


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
                lambda: self.memory_client.retrieve_memories(
                    memoryId=settings.AGENTCORE_MEMORY_ID,
                    namespace=namespace,
                    query=query,
                    maxResults=3
                )
            )
        except:
            return []
    
    @observe(name="analysis")
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
        self.langfuse_handler = LangfuseCallbackHandler()
    
    @observe(name="execution")
    async def execute(self, user_message: str, tools: List[Any], user_id: str, conversation_id: str, memory_context: str = "") -> str:
        checkpointer = AgentCoreMemorySaver(
            memory_id=settings.AGENTCORE_MEMORY_ID,
            region_name=settings.AWS_REGION
        )
        
        system_prompt = EXECUTION_SYSTEM_PROMPT.format(memory_context=memory_context)

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
                "callbacks": [BroadcastCallbackHandler(conversation_id), self.langfuse_handler],
                "metadata": {"user_id": user_id, "conversation_id": conversation_id},
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
        self.memory_client = get_memory_client()
        self._router_llm = instructor.from_bedrock(
            get_bedrock_client(), 
            model=settings.BEDROCK_MODEL_ID
        )
        
        catalog_path = os.path.join(os.path.dirname(__file__), "toolkits_catalog.json")
        try:
            with open(catalog_path, "r") as f:
                self.toolkits_catalog = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load toolkits catalog: {e}")
            self.toolkits_catalog = []
        
        # Initialize context manager and personality handler
        self.context_manager = ContextManager(self.memory_client, self.toolkits_catalog)
        self.personality_handler = PersonalityHandler(
            self.execution_agent.llm, 
            self.chat_memory, 
            self.memory_client
        )
    
    
    @observe(name="intent_classification")
    def _classify_intent(self, user_message: str) -> IntentOutput:

        catalog_str = "\n".join([f"{a['slug']} | {a['name']} | {a['description']} | {a['category']}" for a in self.toolkits_catalog])
        system_prompt = INTENT_SYSTEM_PROMPT.format(catalog=catalog_str)
        try:
            return self._router_llm.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                response_model=IntentOutput,
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentOutput(intent="task", app_mentioned=False, app_slugs=[], relevant_categories=[])

    @observe(name="execute_task")
    async def execute_task(self, user_message: str, user_id: str, conversation_id: str, chat_name: str = None) -> dict:
        start = time.time()
        try:
            try:
                chat_name = self.chat_memory.get_chat_name(user_id, conversation_id)
            except Exception as e:
                logger.error(f"Failed to retrieve chat name from STM: {e}")
            
            # Step 1: Intent classification
            intent_output = await asyncio.get_event_loop().run_in_executor(
                _executor, lambda: self._classify_intent(user_message)
            )
            logger.info(f"Intent: {intent_output.intent}, app_mentioned={intent_output.app_mentioned}, app_slugs={intent_output.app_slugs}")

            original_message = user_message
            
            if intent_output.app_mentioned and intent_output.app_slugs and len(user_message.strip().split()) <= 3:
                logger.info("Short message with app mention detected, checking for original request...")
                original_request = self.chat_memory.get_original_request(user_id, conversation_id)
                
                if original_request:
                    app_names = [app['name'] for app in self.toolkits_catalog if app['slug'] in intent_output.app_slugs]
                    app_name = app_names[0] if app_names else intent_output.app_slugs[0]
                    user_message = f"{original_request} using {app_name}"
                    logger.info(f"Combined request: '{user_message}'")

            # Personality routing
            if intent_output.intent == 'greeting':
                return await self.personality_handler.handle_greeting(
                    original_message, user_id, conversation_id, chat_name
                )

            if intent_output.intent == 'identity':
                return await self.personality_handler.handle_identity(
                    original_message, user_id, conversation_id, chat_name
                )

            if intent_output.intent == 'user_identity':
                return await self.personality_handler.handle_user_identity(
                    original_message, user_id, conversation_id, chat_name
                )

            if intent_output.intent == 'capabilities':
                return await self.personality_handler.handle_capabilities(
                    original_message, user_id, conversation_id, chat_name
                )

            toolkits = []
            
            if intent_output.app_mentioned and intent_output.app_slugs:
                toolkits = intent_output.app_slugs
                logger.info(f"User mentioned: {toolkits}")
            else:
                logger.info("No app mentioned, checking context...")
                context_apps = await self.context_manager.get_app_from_context(user_id, conversation_id)
                
                if context_apps:
                    toolkits = context_apps
                    logger.info(f"Found in context: {toolkits}")
                else:
                    logger.info("No context, asking user...")
                    stream_event(conversation_id, "init", "Finding relevant apps...")
                    
                    relevant_apps = []
                    if intent_output.relevant_categories:
                        for app in self.toolkits_catalog:
                            if any(cat.lower() in app.get('raw_category', '').lower() for cat in intent_output.relevant_categories):
                                relevant_apps.append(app)
                    
                    if not relevant_apps:
                        rag_tools_temp = await self.rag.search_tools(user_message, top_k=10)
                        seen_slugs = set()
                        for tool in rag_tools_temp:
                            if tool.toolkit not in seen_slugs:
                                app_info = next((a for a in self.toolkits_catalog if a["slug"] == tool.toolkit), None)
                                if app_info:
                                    relevant_apps.append(app_info)
                                    seen_slugs.add(tool.toolkit)
                    
                    if relevant_apps:
                        app_list = "\n".join([f"- **{app['name']}** ({app['description']})" for app in relevant_apps[:8]])
                        clarification_response = f"I can help with that! Which app would you like me to use?\n\n{app_list}"
                        
                        self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER', event_type='original_request')
                        self.chat_memory.store_message(user_id, conversation_id, clarification_response, 'ASSISTANT')
                        
                        return {
                            "response": clarification_response,
                            "awaiting_user": True,
                            "rag_tools_found": 0,
                            "rag_tool_names": [],
                            "toolkits_used": [],
                            "success": True,
                            "chatName": chat_name,
                            "personality_response": False,
                            "needs_clarification": True,
                            "connection_url": ""
                        }
            
            logger.info(f"Using toolkits: {toolkits}")
            
            stream_event(conversation_id, "init", "Searching knowledge base for accessible tools...")

            if toolkits:
                expanded_toolkits = self.context_manager.expand_toolkit_names(toolkits[:2])
                logger.info(f"Expanded toolkits: {expanded_toolkits}")
                rag_task = self.rag.search_tools(
                    user_message,
                    top_k=15,
                    filter={"toolkit": {"$in": expanded_toolkits}}
                )
            else:
                rag_task = self.rag.search_tools(user_message, top_k=10)

            pref_task = self.analysis_agent._retrieve_memories(f"/users/{user_id}/preferences", "user preferences")
            context_task = self.analysis_agent._retrieve_memories(f"/semantic/{user_id}", user_message)

            rag_tools, preferences, semantic_context = await asyncio.gather(rag_task, pref_task, context_task)

            if toolkits:
                logger.info(f"RAG: Found {len(rag_tools)} tools in {toolkits[:2]}")

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
            
            stream_event(conversation_id, "init", f"Analyzing tools and planning execution strategy...")
            analysis = await self.analysis_agent.analyze(
                user_message, user_id, rag_tools, 
                preferences=preferences, 
                semantic_context=semantic_context
            )
            logger.info(f"Analysis: selected {len(analysis.selected_slugs)} tools ({analysis.confidence})")
            logger.info(f"Selected tools: {analysis.selected_slugs}")
            
            if toolkits:
                primary_toolkit = toolkits[0]
            else:
                toolkits = analysis.relevant_toolkits
                primary_toolkit = toolkits[0] if toolkits else "unknown"
            
            selected_slugs = analysis.selected_slugs

            if not toolkits:
                return {
                    "response": "I couldn't find the right tools for your request.",
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "toolkits_used": [],
                    "success": False,
                    "chatName": chat_name,
                    "personality_response": False,
                    "needs_clarification": False,
                    "connection_url": ""
                }

            # Step 4: Composio tool loading
            try:
                stream_event(conversation_id, "init", f"Initializing Native Tools for {primary_toolkit.title()}...")
                
                session = self.sdk.create(
                    user_id=user_id, 
                    toolkits=toolkits,
                    manage_connections={"callback_url": settings.CALLBACK_URL}
                )

                toolkits_data = session.toolkits()
                for tk in toolkits:
                    is_connected = any(
                        t.slug.lower() == tk.lower() and t.connection and t.connection.is_active 
                        for t in toolkits_data.items
                    )
                    
                    if not is_connected:
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
                
                if selected_slugs:
                    try:
                        tools = [*self.sdk.tools.get(user_id=user_id, tools=selected_slugs)]
                        loaded_slugs = [t.name for t in tools]
                        logger.info(f"Requested slugs: {selected_slugs}")
                        logger.info(f"Loaded {len(tools)} tools with slugs: {loaded_slugs}")
                        for tool in tools:
                            logger.info(f"Tool {tool.name}: description={getattr(tool, 'description', 'NO DESCRIPTION')[:100]}")
                    except Exception as e:
                        logger.error(f"Failed to fetch precise tools {selected_slugs}, falling back: {e}")
                        tools = [*self.sdk.tools.get(user_id=user_id, toolkits=toolkits)][:5]
                        loaded_slugs = [t.name for t in tools]
                        logger.info(f"Fallback loaded {len(tools)} tools: {loaded_slugs}")
                else:
                    tools = [*self.sdk.tools.get(user_id=user_id, toolkits=toolkits)][:5]
                    loaded_slugs = [t.name for t in tools]
                    logger.info(f"No slugs selected, loaded {len(tools)} tools from toolkits: {loaded_slugs}")

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

            # Build and inject full memory context into the execution agent's system prompt
            memory_context = await self.context_manager.build_memory_context(user_id, conversation_id)

            final = await self.execution_agent.execute(user_message, tools, user_id, conversation_id, memory_context=memory_context)
            
            stream_event(conversation_id, "completed", "Task completed.")
            logger.info(f"Completed in {time.time() - start:.2f}s")
            
            return {
                "response": final,
                "awaiting_user": False,
                "rag_tools_found": len(rag_tools),
                "rag_tool_names": [t.tool_slug for t in rag_tools],
                "toolkits_used": toolkits,
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