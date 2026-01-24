import uvicorn
from app.app import graphql_resolver
import traceback
import asyncio

def handler(event, context):
    try:
        print(f"[Handler] Starting with event: {event}")
        result = asyncio.run(graphql_resolver(event))
        print(f"[Handler] Result: {result}")
        return result
    except Exception as e:
        print(f"[Handler] ERROR: {str(e)}")
        print(f"[Handler] Traceback: {traceback.format_exc()}")
        return {"error": str(e), "success": False}

if __name__ == "__main__":
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000, reload=True)