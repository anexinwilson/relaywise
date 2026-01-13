import httpx
from google import genai
from google.genai import types
from composio import Composio
from composio_gemini import GeminiProvider
from app.config.settings import settings

class IntegrationService:
    def __init__(self, genai_client: genai.Client):
        self.genai_client = genai_client
        self.composio_client = Composio(
            api_key=settings.COMPOSIO_API_KEY,
            provider=GeminiProvider(),
            toolkit_versions="latest"
        )
    
    async def list_available_apps(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://backend.composio.dev/api/v1/apps",
                headers={"x-api-key": settings.COMPOSIO_API_KEY},
                timeout=10.0
            )
            data = response.json()
            return {"success": True, "apps": data.get("items", []) if isinstance(data, dict) else data}
    
    async def execute_with_gemini(self, clerk_user_id: str, message: str):
        toolkit_detection = self.genai_client.models.generate_content(
            model=settings.GEMINI_COMPILER_MODEL,
            contents=f"What app/service is needed for: '{message}'? Reply with ONE word only (slack/github/gmail/notion/trello/asana/drive)"
        )
        
        toolkit = toolkit_detection.text.strip().lower()
        
        tools = self.composio_client.tools.get(
            user_id=clerk_user_id,
            toolkits=[toolkit],
            limit=200
        )
        
        config = types.GenerateContentConfig(
            tools=tools,
            temperature=0.3,
            system_instruction="Use the FEWEST tools possible. Answer directly."
        )
        
        chat = self.genai_client.chats.create(model=settings.GEMINI_COMPILER_MODEL, config=config)
        response = chat.send_message(message)
        all_function_calls = []
        
        for _ in range(3):
            if not (hasattr(response, 'function_calls') and response.function_calls):
                break
            
            function_response_parts = []
            
            for fc in response.function_calls:
                tool_result = self.composio_client.tools.execute(
                    slug=fc.name,
                    arguments=dict(fc.args) if fc.args else {},
                    user_id=clerk_user_id,
                    dangerously_skip_version_check=True
                )
                
                all_function_calls.append({
                    "name": fc.name,
                    "args": dict(fc.args) if fc.args else {},
                    "result": str(tool_result)
                })
                
                function_response_parts.append(
                    types.Part.from_function_response(name=fc.name, response={"result": str(tool_result)})
                )
            
            response = chat.send_message(function_response_parts)
        
        return {
            "response": response.text if hasattr(response, 'text') else None,
            "function_calls": all_function_calls
        }

_integration_service = None

def get_integration_service(genai_client: genai.Client) -> IntegrationService:
    global _integration_service
    if _integration_service is None:
        _integration_service = IntegrationService(genai_client)
    return _integration_service