import json
import httpx
import boto3
import time
from typing import Dict, List, Any, Optional, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from pinecone import Pinecone
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from config import settings

_bedrock_client = None
_pinecone_index = None
_google_credentials = None

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

def get_google_credentials():
    global _google_credentials
    if _google_credentials is None:
        _google_credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        _google_credentials.refresh(Request())
    return _google_credentials

class AgentState(TypedDict):
    messages: List[Any]
    rag_results: Optional[List[Dict]]
    current_action: Optional[Dict]
    user_id: str
    conversation_id: str

class RAGClient:
    def __init__(self):
        self.index = get_pinecone_index()
        self.bedrock = get_bedrock_client()
    
    def search_tools(self, query: str, top_k: int = 3) -> List[Dict]:
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
        except:
            return []
    
    def _get_embedding(self, text: str) -> List[float]:
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.titan-embed-text-v2:0',
                body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
            )
            return json.loads(response['body'].read()).get('embedding', [])
        except:
            return []

class ComposioExecutor:
    def __init__(self):
        self.api_key = settings.COMPOSIO_API_KEY
        self.base_url = "https://backend.composio.dev/api/v3"
    
    async def execute(self, tool_slug: str, user_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/execute/{tool_slug}",
                headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
                json={"user_id": user_id, "arguments": arguments},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

class AgentNodes:
    def __init__(self, llm, rag: RAGClient, executor: ComposioExecutor):
        self.llm = llm
        self.rag = rag
        self.executor = executor
        self.system_prompt = """You are an AI automation controller.
Select the best tool from the RAG context to fulfill the user request.

Return ONLY a JSON object:
{
  "action_type": "chat" | "action",
  "confidence": 0.0-1.0,
  "response": "Brief explanation",
  "tool_slug": "EXACT_SLUG_FROM_METADATA",
  "tool_id": "EXACT_TOOL_ID_FROM_METADATA",
  "arguments": {"param": "value"}
}

CRITICAL: tool_id and tool_slug must be copied exactly from the RAG results. Never generate or modify them."""

    async def rag_and_decide(self, state: AgentState) -> AgentState:
        user_message = state["messages"][-1].content
        
        # #region agent log - RAG timing
        t_rag_start = time.time()
        rag_results = self.rag.search_tools(user_message)
        t_rag_end = time.time()
        print(f"[TIMING] RAG search: {t_rag_end-t_rag_start:.2f}s, found {len(rag_results)} tools")
        # #endregion
        
        state["rag_results"] = rag_results
        
        if not rag_results:
            state["current_action"] = {"action_type": "chat", "response": "No tools found for this request."}
            return state
        
        # Simplified prompt for faster LLM inference
        tools_summary = "\n".join([
            f"- {t['toolkit']}/{t['tool_slug']}: {t['description'][:100]}"
            for t in rag_results[:3]  # Only top 3 tools
        ])
        
        prompt = f"""You are an automation controller. Based on the user request, decide if you should use a tool or just chat.

User: {user_message}

Available tools:
{tools_summary}

Respond with ONLY a JSON object (no markdown):
{{"action_type": "chat" or "action", "confidence": 0.0-1.0, "response": "brief text", "tool_slug": "slug_if_action", "tool_id": "id_if_action", "arguments": {{}}}}"""
        
        # #region agent log - LLM timing
        t_llm_start = time.time()
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        t_llm_end = time.time()
        print(f"[TIMING] LLM inference: {t_llm_end-t_llm_start:.2f}s")
        # #endregion
        
        try:
            content = response.content
            if isinstance(content, list):
                content = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in content])
            
            # Extract JSON more robustly
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                state["current_action"] = json.loads(json_str)
            else:
                state["current_action"] = {"action_type": "chat", "response": content}
        except Exception as e:
            print(f"[ERROR] Failed to parse LLM response: {e}")
            state["current_action"] = {"action_type": "chat", "response": "I couldn't process that request."}
        
        return state

    def route(self, state: AgentState) -> str:
        action = state.get("current_action", {})
        if action.get("action_type") == "action" and action.get("confidence", 0) >= 0.85:
            return "execute"
        return "chat"

    async def chat(self, state: AgentState) -> AgentState:
        response = state["current_action"].get("response", "I'm not sure how to help.")
        state["messages"].append(AIMessage(content=str(response) if isinstance(response, list) else response))
        return state

    async def execute(self, state: AgentState) -> AgentState:
        action = state["current_action"]
        try:
            rag_tools = {tool["tool_id"]: tool for tool in state.get("rag_results", [])}
            selected_tool = rag_tools.get(action.get("tool_id"))
            
            if not selected_tool:
                raise ValueError(f"Hallucinated tool_id: {action.get('tool_id')}")
            
            if selected_tool["tool_slug"] != action.get("tool_slug"):
                raise ValueError(f"tool_slug mismatch")
            
            result = await self.executor.execute(
                tool_slug=action["tool_slug"],
                user_id=state["user_id"],
                arguments=action["arguments"]
            )
            response = f"{action.get('response', 'Done')}\n\n{json.dumps(result, indent=2)}"
            state["messages"].append(AIMessage(content=response))
        except Exception as e:
            state["messages"].append(AIMessage(content=f"Error: {str(e)}"))
        return state

class AgentService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_COMPILER_MODEL,
            credentials=get_google_credentials(),
            project="careful-airfoil-483607-g1",
            temperature=0,
            thinking_level="minimal",
            max_tokens=500  # Limit output tokens for faster inference
        )
        self.rag = RAGClient()
        self.executor = ComposioExecutor()
        self.nodes = AgentNodes(self.llm, self.rag, self.executor)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("rag_and_decide", self.nodes.rag_and_decide)
        workflow.add_node("chat", self.nodes.chat)
        workflow.add_node("execute", self.nodes.execute)
        
        workflow.set_entry_point("rag_and_decide")
        workflow.add_conditional_edges("rag_and_decide", self.nodes.route, {
            "chat": "chat",
            "execute": "execute"
        })
        workflow.add_edge("chat", END)
        workflow.add_edge("execute", END)
        
        return workflow.compile()

    async def execute_task(self, user_id: str, message: str, conversation_id: str) -> Dict[str, Any]:
        start = time.time()
        try:
            state: AgentState = {
                "messages": [HumanMessage(content=message)],
                "rag_results": [],
                "current_action": None,
                "user_id": user_id,
                "conversation_id": conversation_id
            }
            
            # #region agent log - timing instrumentation
            t1 = time.time()
            result = await self.graph.ainvoke(state)
            t2 = time.time()
            print(f"[TIMING] Graph execution: {t2-t1:.2f}s")
            # #endregion
            
            final = result["messages"][-1].content
            
            if isinstance(final, list):
                final = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in final])
            
            total = time.time() - start
            print(f"[TIMING] Total execution: {total:.2f}s")
            print(f"[DEBUG] RAG tools found: {len(result.get('rag_results', []))}")
            
            return {
                "response": final,
                "awaiting_user": False,
                "rag_tools_found": len(result.get("rag_results", [])),
                "function_calls": []
            }
        except Exception as e:
            return {"response": f"System Error: {str(e)}", "function_calls": [], "awaiting_user": False}

_agent_service = None

def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service