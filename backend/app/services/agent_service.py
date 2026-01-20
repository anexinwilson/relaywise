from typing import Dict, List, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from composio import Composio
from app.config.settings import settings
from google.oauth2 import service_account

_composio_client: Optional[Composio] = None
BLACKLIST_TOOLKITS = {"MICROSOFTGRAPH", "MICROSOFTONEDRIVE", "MICROSOFTOUTLOOK", "MICROSOFTTEAMS"}
_conversation_sessions: Dict[str, Any] = {}


def get_composio_client() -> Composio:
    global _composio_client
    if _composio_client is None:
        _composio_client = Composio(api_key=settings.COMPOSIO_API_KEY)
    return _composio_client


async def get_or_create_session(
    user_id: str,
    conversation_id: str,
    connected_apps: Optional[List[str]] = None
) -> Any:
    session_key = f"{user_id}:{conversation_id}"
    if session_key in _conversation_sessions:
        return _conversation_sessions[session_key]
    
    composio = get_composio_client()
    kwargs = {"user_id": user_id, "manage_connections": True}
    
    if connected_apps:
        kwargs["toolkits"] = [
            app.upper() for app in connected_apps 
            if app.upper() not in BLACKLIST_TOOLKITS
        ]
    
    session = composio.create(**kwargs)
    _conversation_sessions[session_key] = session
    return session


class AgentService:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            credentials=credentials,
            project="careful-airfoil-483607-g1",
            temperature=0,
            thinking_level="minimal"
        )
    
    async def execute_task(
        self,
        user_id: str,
        message: str,
        conversation_id: str,
        connected_apps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        mcp_client = None
        try:
            session = await get_or_create_session(user_id, conversation_id, connected_apps)
            
            mcp_client = MultiServerMCPClient({
                "composio": {
                    "url": session.mcp.url,
                    "transport": "streamable_http",
                    "headers": session.mcp.headers
                }
            })
            
            tools = await mcp_client.get_tools()
            if not tools:
                return {"response": "Tool Router setup failed. Please try again.", "function_calls": []}
            
            agent = create_react_agent(self.llm, tools, checkpointer=None)
            result = await agent.ainvoke({"messages": [{"role": "user", "content": message}]})
            
            function_calls = []
            response_text = None
            
            for msg in result.get("messages", []):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    function_calls.extend({
                        "name": tc.get("name", "unknown"),
                        "args": tc.get("args", {}),
                        "result": None
                    } for tc in msg.tool_calls)
                
                if hasattr(msg, "content") and msg.content:
                    content = msg.content
                    if isinstance(content, list):
                        response_text = ' '.join(
                            item.get('text', '') 
                            for item in content 
                            if isinstance(item, dict) and 'text' in item
                        ).strip() or response_text
                    elif isinstance(content, str):
                        response_text = content.strip()
            
            return {
                "response": response_text or "Task completed successfully.",
                "function_calls": function_calls
            }
        except Exception as e:
            return {"response": f"I encountered an error: {str(e)}. Please try again.", "function_calls": []}
        finally:
            if mcp_client:
                try:
                    await mcp_client.close()
                except:
                    pass


_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service