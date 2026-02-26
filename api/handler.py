import json
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def lambda_handler(event, context):
    """AppSync Resolver - Lambda Handler for conversation queries"""
    print(f"[Handler] Event: {json.dumps(event, default=str)}")
    
    payload = event.get("payload", event)
    field_name = payload.get("info", {}).get("fieldName", "")
    arguments = payload.get("arguments", {})
    
    print(f"[Handler] field_name: {field_name}")
    print(f"[Handler] arguments: {json.dumps(arguments)}")
    
    # Get user context from authorizer
    request_context = payload.get("request", {})
    resolver_context = request_context.get("headers", {})
    user_id = resolver_context.get("userId")
    
    print(f"[Handler] user_id: {user_id}")
    
    try:
        if field_name == "getUserConversations":
            if not user_id:
                print("[Handler] No user_id, returning []")
                return []
            from app.resolvers.conversation import get_user_conversations
            result = get_user_conversations(None, None, user_id)
            print(f"[Handler] getUserConversations returned {len(result)} conversations")
            return result
        
        elif field_name == "getConversationMessages":
            if not user_id:
                print("[Handler] No user_id, returning []")
                return []
            session_id = arguments.get("sessionId")
            print(f"[Handler] sessionId: {session_id}")
            if not session_id:
                print("[Handler] No sessionId, returning []")
                return []
            from app.resolvers.conversation import get_conversation_messages
            result = get_conversation_messages(None, None, user_id, session_id)
            print(f"[Handler] getConversationMessages returned {len(result)} messages")
            return result
        
        elif field_name == "getOrCreateUser":
            from app.resolvers.user import get_or_create_user
            # This needs database access - simplified for Lambda
            return {
                "userId": user_id,
                "email": resolver_context.get("email"),
                "name": resolver_context.get("name"),
                "tier": "free",
                "apiCallCount": 0
            }
        
        elif field_name == "testMutation":
            return {
                "result": f"Message: {arguments.get('message', 'no message')}",
                "success": True,
                "user": {
                    "userId": user_id,
                    "email": resolver_context.get("email"),
                    "name": resolver_context.get("name")
                }
            }
        
        else:
            print(f"[Handler] Unknown field: {field_name}")
            return {
                "result": f"Unknown field: {field_name}",
                "success": False
            }
    
    except Exception as e:
        print(f"[Handler] Error in {field_name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "success": False
        }