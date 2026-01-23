import os
import json

def authorize(event, context):
    return event

def lambda_handler(event, context):
    print(f"[Lambda] Event: {event}")
    
    # Validate API Key from request headers
    headers = event.get("request", {}).get("headers", {})
    api_key = headers.get("x-api-key", "")
    
    expected_api_key = os.environ.get("APPSYNC_API_KEY", "")
    
    if not api_key or api_key != expected_api_key:
        print("[Lambda] Invalid or missing API key")
        return {
            "result": "Unauthorized",
            "success": False
        }
    
    payload = event.get("payload", event)
    field_name = payload.get("field") or payload.get("info", {}).get("fieldName", "")
    arguments = payload.get("arguments", {})
    
    if field_name == "testMutation":
        return {
            "result": f"Lambda works! Message: {arguments.get('message', 'no message')}",
            "success": True
        }
    
    return {
        "result": f"Unknown field: {field_name}",
        "success": False
    }