import httpx
from google import genai
from app.config.settings import settings

class IntegrationService:
    def __init__(self, genai_client: genai.Client):
        self.genai_client = genai_client
    
    async def list_available_apps(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://backend.composio.dev/api/v1/apps",
                    headers={"x-api-key": settings.COMPOSIO_API_KEY},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return {"success": False, "apps": [], "error": f"API error: {response.status_code}"}
                
                data = response.json()
                apps_list = data.get("items", []) if isinstance(data, dict) else data
                
                return {"success": True, "apps": apps_list, "error": None}
        except Exception as e:
            return {"success": False, "apps": [], "error": str(e)}

_integration_service = None

def get_integration_service(genai_client: genai.Client) -> IntegrationService:
    global _integration_service
    if _integration_service is None:
        _integration_service = IntegrationService(genai_client)
    return _integration_service