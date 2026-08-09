import json
import os
import sys
import uuid
import boto3
from app.config.settings import settings
from app.observability import logger, metrics

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sqs = boto3.client("sqs", region_name=settings.AWS_REGION)


def _bounded_title(message: str) -> str:
    title = " ".join(message.strip().split()).strip(" .,!?:;")
    return (" ".join(title.split()[:8]) or "New conversation")[:80]

@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event, context):
    """AppSync Resolver - Lambda Handler for conversation queries"""
    print(f"[Handler] Event: {json.dumps(event, default=str)}")
    
    payload = event.get("payload", event)
    field_name = payload.get("info", {}).get("fieldName", "")
    arguments = payload.get("arguments", {})
    
    print(f"[Handler] field_name: {field_name}")
    print(f"[Handler] arguments: {json.dumps(arguments)}")
    
    # Get user context from authorizer
    identity = payload.get("identity", {}) or {}
    resolver_context = identity.get("resolverContext", {}) or {}
    if not resolver_context:
        resolver_context = payload.get("request", {}).get("headers", {}) or {}
    user_id = resolver_context.get("userId")
    
    print(f"[Handler] user_id: {user_id}")
    
    try:
        if field_name == "askAgent":
            if not user_id:
                return {"success": False, "error": "Unauthorized"}
            message = arguments.get("message")
            if not isinstance(message, str) or not message.strip():
                return {"success": False, "error": "message is required"}
            session_id = arguments.get("sessionId") or str(uuid.uuid4())
            queue_url = settings.SQS_QUEUE_URL
            task_id = str(uuid.uuid4())
            chat_name = _bounded_title(message)
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({
                    "taskId": task_id,
                    "userId": user_id,
                    "sessionId": session_id,
                    "message": message,
                    "chatName": chat_name,
                }),
                MessageGroupId=session_id,
                MessageDeduplicationId=task_id,
            )
            metrics.add_metric(name="TaskAccepted", unit="Count", value=1)
            logger.info("Task accepted", extra={"task_id": task_id, "session_id": session_id})
            return {
                "success": True,
                "taskId": task_id,
                "sessionId": session_id,
                "response": "Processing your request...",
                "chatName": chat_name,
            }

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
        metrics.add_metric(name="ResolverError", unit="Count", value=1)
        logger.exception("Resolver failed", extra={"error_type": type(e).__name__})
        print(f"[Handler] Error in {field_name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "success": False
        }
