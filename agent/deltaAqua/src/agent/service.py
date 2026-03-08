import json
import boto3
import time
import asyncio
from typing import List, Any, Literal
from pydantic import BaseModel, Field
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver
import instructor

from .client import get_bedrock_client, get_memory_client, get_pinecone_index, get_composio_client, get_executor
from rag.client import RAGClient, RAGTool

from config import settings
from utils import get_logger
from memory import ChatMemory
from agent.chat_namer import ChatNamer

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
            best_score = max(t.score for t in tools)
            toolkit_summary = next((t.summary for t in tools if t.summary), "")
            tools_formatted.append(f"\n\nToolkit: {toolkit_name} (score: {best_score:.3f})")
            if toolkit_summary:
                tools_formatted.append(f"Summary: {toolkit_summary[:200]}")
            for t in sorted(tools, key=lambda x: x.score, reverse=True)[:3]:
                tools_formatted.append(f"  - {t.tool_slug}: {t.description[:80]}")
        
        system_prompt = """You are an intelligent toolkit and tool selector for an automation platform.

Analyze the user's request and select the ONE best toolkit AND up to 5 specific tool slugs to use.

SELECTION LOGIC:
- If user explicitly mentions an app name → prioritize that toolkit.
- Select the specific tool slugs (max 5) that are most likely to solve the request.
- Only use ONE toolkit.
- RAG scores help, but user intent is more important.

OUTPUT:
Return the toolkit, the specific slugs, and a confidence level."""

        user_prompt = f"""USER REQUEST: "{user_message}"

CONTEXT: {user_context}

RAG RESULTS:
{''.join(tools_formatted)}

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
                reasoning="Fallback: selected highest RAG score",
                intent=user_message
            )

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
        # Modern Agent Factory with Node Caching
        checkpointer = AgentCoreMemorySaver(
            memory_id=settings.AGENTCORE_MEMORY_ID,
            region_name=settings.AWS_REGION
        )
        
        system_prompt = f"""You are a helpful automation assistant with access to tools.
USER REQUEST: "{user_message}"

INSTRUCTIONS:
1. Analyze request and extract specific values (like "#social", names, IDs).
2. Use tools to find info, then provide a direct answer.
3. STOP once you have the data.

PARAMETER EXTRACTION:
- Extract values like channel names or IDs directly from the request above."""

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
                "cache": "enabled"
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
        self.composio = get_composio_client()
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

    async def execute_task(self, user_message: str, user_id: str, conversation_id: str, chat_name: str = None) -> dict:
        start = time.time()
        try:
            try:
                chat_name = self.chat_memory.get_chat_name(user_id, conversation_id)
            except Exception as e:
                logger.error(f"Failed to retrieve chat name from LTM: {e}")
            
            # PARALLEL PREP PHASE
            rag_task = self.rag.search_tools(user_message, top_k=3)
            pref_task = self.analysis_agent._retrieve_memories(f"/users/{user_id}/preferences", "user preferences")
            context_task = self.analysis_agent._retrieve_memories(f"/semantic/{user_id}", user_message)

            rag_tools, preferences, semantic_context = await asyncio.gather(
                rag_task, pref_task, context_task
            )
            
            if not rag_tools:
                return {
                    "response": "No tools found.",
                    "awaiting_user": False,
                    "rag_tools_found": 0,
                    "rag_tool_names": [],
                    "success": True,
                    "chatName": chat_name
                }
            
            logger.info(f"RAG: {len(rag_tools)} tools")
            
            # COLLAPSED LLM ANALYSIS (with pre-fetched context)
            analysis = await self.analysis_agent.analyze(
                user_message, user_id, rag_tools, 
                preferences=preferences, 
                semantic_context=semantic_context
            )
            logger.info(f"Analysis: {analysis.relevant_toolkit} ({analysis.confidence})")
            
            toolkit = analysis.relevant_toolkit
            selected_slugs = analysis.selected_slugs

            try:
                session = self.composio.create(
                    user_id=user_id,
                    toolkits=[toolkit],
                    manage_connections={"callback_url": settings.CALLBACK_URL}
                )
                
                mcp_client = MultiServerMCPClient({
                    "composio": {
                        "transport": "streamable_http",
                        "url": session.mcp.url,
                        "headers": session.mcp.headers,
                    }
                })
                
                all_tools = await mcp_client.get_tools()

                # Optimized Context: Exactly the top 5 (or fewer) selected slugs
                tools = [t for t in all_tools if t.name in selected_slugs]
                if not tools:
                    tools = all_tools[:5]
                
            except Exception as e:
                logger.error(f"Composio failed: {e}")
                return {
                    "response": f"Failed to initialize {toolkit}. Connect your account.",
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False,
                    "chatName": chat_name
                }
            
            if not tools:
                return {
                    "response": f"No tools for {toolkit}. Connect your account.",
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False,
                    "chatName": chat_name
                }
            
            logger.info(f"Loaded {len(tools)} tools for {toolkit}")
            
            final = await self.execution_agent.execute(user_message, tools, user_id, conversation_id)
            
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
                "response": f"Error: {str(e)}",
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