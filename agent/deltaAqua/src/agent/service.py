import json
import boto3
import time
import asyncio
from typing import List, Any, Literal
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field

from composio import Composio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from bedrock_agentcore.memory import MemoryClient
from langgraph_checkpoint_aws import AgentCoreMemorySaver
from pinecone import Pinecone
import instructor

from config import settings
from utils import get_logger

logger = get_logger(__name__)

_bedrock_client = None
_pinecone_index = None
_composio_client = None
_memory_client = None
_executor = ThreadPoolExecutor(max_workers=4)

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)
    return _bedrock_client

def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index

def get_composio_client():
    global _composio_client
    if _composio_client is None:
        _composio_client = Composio(api_key=settings.COMPOSIO_API_KEY)
    return _composio_client

def get_memory_client():
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryClient(region_name=settings.AWS_REGION)
    return _memory_client

class RAGTool(BaseModel):
    tool_slug: str
    tool_id: str
    toolkit: str
    version: str
    description: str
    required_params: List[str] = []
    optional_params: List[str] = []
    score: float

class AnalysisOutput(BaseModel):
    relevant_toolkits: List[str] = Field(description="List of all relevant toolkits to load")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level")
    reasoning: str = Field(description="Why these toolkits were chosen")
    intent: str = Field(description="What user wants to accomplish")

class RAGClient:
    def __init__(self):
        self.index = get_pinecone_index()
        self.bedrock = get_bedrock_client()
    
    def search_tools(self, query: str, top_k: int = 10) -> List[RAGTool]:
        try:
            embedding = self._get_embedding(query)
            if not embedding:
                return []
            
            results = self.index.query(vector=embedding, top_k=top_k, include_metadata=True)
            
            tools = []
            for match in results.matches:
                meta = match.metadata
                if isinstance(meta, str):
                    meta = json.loads(meta)
                
                req_params = meta.get("required_params", "")
                opt_params = meta.get("optional_params", "")
                
                tools.append(RAGTool(
                    tool_slug=meta.get("slug", ""),
                    tool_id=meta.get("tool_id", ""),
                    toolkit=meta.get("toolkit", ""),
                    version=meta.get("version", ""),
                    description=meta.get("text", ""),
                    required_params=req_params.split(",") if req_params else [],
                    optional_params=opt_params.split(",") if opt_params else [],
                    score=match.score
                ))
            
            return tools
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    def _get_embedding(self, text: str) -> List[float]:
        response = self.bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
        )
        return json.loads(response['body'].read()).get('embedding', [])

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
    
    async def analyze(self, user_message: str, user_id: str, rag_tools: List[RAGTool]) -> AnalysisOutput:
        preferences = await self._retrieve_memories(f"/users/{user_id}/preferences", "user preferences")
        semantic_context = await self._retrieve_memories(f"/semantic/{user_id}", user_message)
        
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
            tools_formatted.append(f"\nToolkit: {toolkit_name} (score: {best_score:.3f})")
            for t in sorted(tools, key=lambda x: x.score, reverse=True)[:3]:
                tools_formatted.append(f"  - {t.tool_slug}: {t.description[:80]}")
        
        system_prompt = """You are an intelligent toolkit selector for an automation platform.

Analyze the user's request and select the ONE best toolkit to use.

SELECTION LOGIC:
- If user explicitly mentions an app name → prioritize exact name match
- If multiple toolkits for same app (e.g., "app" + "app_utility") → choose the main one
- Only use ONE toolkit
- RAG scores help, but user intent is more important

OUTPUT:
Return ONE toolkit with confidence level based on how clear the match is."""

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
            return AnalysisOutput(
                relevant_toolkits=[best_toolkit],
                confidence="low",
                reasoning="Fallback: selected highest RAG score",
                intent=user_message
            )

class ExecutionAgent:
    def __init__(self):
        self.llm = ChatBedrock(
            client=get_bedrock_client(),
            model_id=settings.BEDROCK_MODEL_ID,  
            model_kwargs={"max_tokens": 4096, "temperature": 0}
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
        model_with_tools = self.llm.bind_tools(tools)
        tool_call_tracker = {"count": 0, "max_calls": 15}
        
        base_tool_node = ToolNode(tools)
        
        async def tool_node_wrapper(state: MessagesState):
            result = await base_tool_node.ainvoke(state)
            cleaned_messages = []
            for msg in result.get("messages", []):
                if hasattr(msg, 'content') and isinstance(msg.content, list):
                    text_parts = []
                    for block in msg.content:
                        if isinstance(block, dict):
                            if 'text' in block:
                                text_parts.append(block['text'])
                            elif 'content' in block:
                                text_parts.append(str(block['content']))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    msg.content = '\n'.join(text_parts) if text_parts else str(msg.content)
                cleaned_messages.append(msg)
            return {"messages": cleaned_messages}
        
        system_prompt = f"""You are a helpful automation assistant with access to tools.

USER REQUEST: "{user_message}"

INSTRUCTIONS:
1. Analyze the user's request and extract specific values (like "#social", names, dates, IDs)
2. If you need to find something (like a channel ID), use the search/find tools with those extracted values
3. Once you have the data, STOP and provide a direct answer
4. Do NOT make additional tool calls after getting the information

PARAMETER EXTRACTION:
- If user mentions "#social", use "social" or "#social" as your query parameter
- If user mentions a name, use that exact name
- Extract values from the USER REQUEST above"""
        
        async def call_model(state: MessagesState):
            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await model_with_tools.ainvoke(messages)
            return {"messages": [response]}
        
        def should_continue(state: MessagesState) -> Literal["continue", "end"]:
            last_message = state["messages"][-1]
            
            if tool_call_tracker["count"] >= tool_call_tracker["max_calls"]:
                return "end"
            
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return "end"
            
            tool_call_tracker["count"] += len(last_message.tool_calls)
            return "continue"
        
        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node_wrapper)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
        workflow.add_edge("tools", "agent")
        
        checkpointer = AgentCoreMemorySaver(
            memory_id=settings.AGENTCORE_MEMORY_ID,
            region_name=settings.AWS_REGION
        )
        
        agent = workflow.compile(checkpointer=checkpointer)
        
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={
                "configurable": {"actor_id": user_id, "thread_id": conversation_id},
                "recursion_limit": 50
            }
        )
        
        final = result["messages"][-1].content
        if isinstance(final, list):
            final = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in final])
        
        asyncio.create_task(self._create_event(user_id, conversation_id, [(user_message, "USER"), (final, "ASSISTANT")]))
        
        return final

class AgentService:
    def __init__(self):
        self.rag = RAGClient()
        self.composio = get_composio_client()
        self.analysis_agent = AnalysisAgent()
        self.execution_agent = ExecutionAgent()
        logger.info("Initialized 2-agent system with AgentCore Memory")
    
    async def execute_task(self, user_message: str, user_id: str, conversation_id: str) -> dict:
        start = time.time()
        
        try:
            rag_tools = self.rag.search_tools(user_message, top_k=15)
            
            if not rag_tools:
                return {
                    "response": "No tools found.",
                    "awaiting_user": False,
                    "rag_tools_found": 0,
                    "rag_tool_names": [],
                    "success": True
                }
            
            logger.info(f"RAG: {len(rag_tools)} tools")
            
            analysis = await self.analysis_agent.analyze(user_message, user_id, rag_tools)
            logger.info(f"Analysis: {analysis.relevant_toolkits} ({analysis.confidence})")
            
            try:
                session = self.composio.create(
                    user_id=user_id,
                    toolkits=analysis.relevant_toolkits,
                    manage_connections={"callback_url": settings.CALLBACK_URL}
                )
                
                mcp_client = MultiServerMCPClient({
                    "composio": {
                        "transport": "streamable_http",
                        "url": session.mcp.url,
                        "headers": session.mcp.headers,
                    }
                })
                
                tools = await mcp_client.get_tools()
                
            except Exception as e:
                logger.error(f"Composio failed: {e}")
                return {
                    "response": f"Failed to initialize {', '.join(analysis.relevant_toolkits)}. Connect your account.",
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False
                }
            
            if not tools:
                return {
                    "response": f"No tools for {', '.join(analysis.relevant_toolkits)}. Connect your account.",
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t.tool_slug for t in rag_tools],
                    "success": False
                }
            
            logger.info(f"Loaded {len(tools)} tools from {', '.join(analysis.relevant_toolkits)}")
            
            final = await self.execution_agent.execute(user_message, tools, user_id, conversation_id)
            
            logger.info(f"Completed in {time.time() - start:.2f}s")
            
            return {
                "response": final,
                "awaiting_user": False,
                "rag_tools_found": len(rag_tools),
                "rag_tool_names": [t.tool_slug for t in rag_tools],
                "toolkits_used": analysis.relevant_toolkits,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            return {
                "response": f"Error: {str(e)}",
                "awaiting_user": False,
                "rag_tools_found": 0,
                "rag_tool_names": [],
                "success": False
            }

_agent_service = None

def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
