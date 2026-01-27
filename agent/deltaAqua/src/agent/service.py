import json
import boto3
import time
from typing import Dict, List, Any, Optional, TypedDict, Literal

from composio import Composio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from pinecone import Pinecone

from config import settings
from utils import get_logger

logger = get_logger(__name__)

_bedrock_client = None
_pinecone_index = None
_composio_client = None

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
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

class RAGClient:
    def __init__(self):
        self.index = get_pinecone_index()
        self.bedrock = get_bedrock_client()
    
    def search_tools(self, query: str, top_k: int = 10) -> List[Dict]:
        try:
            embedding = self._get_embedding(query)
            if not embedding:
                return []
            
            results = self.index.query(vector=embedding, top_k=top_k, include_metadata=True)
            
            tools = []
            for match in results.matches:
                meta = match.metadata
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except:
                        continue
                
                req_params = meta.get("required_params", "")
                opt_params = meta.get("optional_params", "")
                
                tools.append({
                    "tool_slug": meta.get("slug"),
                    "tool_id": meta.get("tool_id"),
                    "toolkit": meta.get("toolkit"),
                    "description": meta.get("text", ""),
                    "required_params": req_params.split(",") if req_params else [],
                    "optional_params": opt_params.split(",") if opt_params else [],
                    "score": match.score
                })
            
            return tools
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    def _get_embedding(self, text: str) -> List[float]:
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.titan-embed-text-v2:0',
                body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
            )
            return json.loads(response['body'].read()).get('embedding', [])
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

class MCPSessionManager:
    def __init__(self):
        self.composio = get_composio_client()
        self._sessions = {}
    
    async def get_tools_for_toolkit(self, user_id: str, toolkit: str) -> List[Any]:
        if not toolkit:
            return []
        
        try:
            session = self.composio.create(
                user_id=user_id,
                toolkits=[toolkit],
                manage_connections={
                    "callback_url": settings.CALLBACK_URL
                }
            )
            
            mcp_client = MultiServerMCPClient({
                "composio": {
                    "transport": "streamable_http",
                    "url": session.mcp.url,
                    "headers": session.mcp.headers,
                }
            })
            
            tools = await mcp_client.get_tools()
            return tools
        except Exception as e:
            logger.error(f"MCP session failed for {toolkit}: {e}")
            return []

class AgentService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0
        )
        logger.info("Initialized with gpt-5-mini")
        
        self.rag = RAGClient()
        self.mcp = MCPSessionManager()

    async def execute_task(self, user_message: str, user_id: str, conversation_id: str) -> Dict[str, Any]:
        start = time.time()
        try:
            rag_tools = self.rag.search_tools(user_message, top_k=10)
            
            if not rag_tools:
                return {
                    "response": "No tools found for your request.",
                    "awaiting_user": False,
                    "rag_tools_found": 0,
                    "rag_tool_names": [],
                    "success": True
                }
            
            toolkit = rag_tools[0]["toolkit"]
            
            tools = await self.mcp.get_tools_for_toolkit(user_id, toolkit)
            
            if not tools:
                return {
                    "response": f"Failed to initialize {toolkit} tools. You may need to connect your account.",
                    "awaiting_user": True,
                    "rag_tools_found": len(rag_tools),
                    "rag_tool_names": [t["tool_slug"] for t in rag_tools],
                    "success": False
                }
            
            model_with_tools = self.llm.bind_tools(tools)
            tool_node = ToolNode(tools)
            
            def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
                last_message = state["messages"][-1]
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    return "tools"
                return "__end__"
            
            async def call_model(state: MessagesState):
                response = await model_with_tools.ainvoke(state["messages"])
                return {"messages": [response]}
            
            workflow = StateGraph(MessagesState)
            workflow.add_node("agent", call_model)
            workflow.add_node("tools", tool_node)
            workflow.add_edge("__start__", "agent")
            workflow.add_conditional_edges("agent", should_continue)
            workflow.add_edge("tools", "agent")
            
            agent = workflow.compile()
            
            result = await agent.ainvoke({
                "messages": [{"role": "user", "content": user_message}]
            })
            
            final = result["messages"][-1].content
            
            if isinstance(final, list):
                final = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in final])
            
            elapsed = time.time() - start
            logger.info(f"Task completed in {elapsed:.2f}s")
            
            return {
                "response": final,
                "awaiting_user": False,
                "rag_tools_found": len(rag_tools),
                "rag_tool_names": [t["tool_slug"] for t in rag_tools],
                "success": True
            }
        except Exception as e:
            logger.error(f"Task error: {e}")
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