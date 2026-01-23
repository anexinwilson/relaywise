import json

def lambda_handler(event, context):
    """AppSync Resolver - Simple Handler"""
    print(f"[Handler] Event: {event}")
    
    payload = event.get("payload", event)
    field_name = payload.get("field") or payload.get("info", {}).get("fieldName", "")
    arguments = payload.get("arguments", {})
    
    # Get user context from authorizer
    request_context = payload.get("request", {})
    resolver_context = request_context.get("headers", {})
    
    if field_name == "testMutation":
        return {
            "result": f"Message: {arguments.get('message', 'no message')}",
            "success": True,
            "user": {
                "userId": resolver_context.get("userId"),
                "email": resolver_context.get("email"),
                "name": resolver_context.get("name")
            }
        }
    
    return {
        "result": f"Unknown field: {field_name}",
        "success": False
    }