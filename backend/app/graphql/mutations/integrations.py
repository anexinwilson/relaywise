import strawberry
import uuid
from typing import Optional
from app.auth.middleware import verify_clerk_token
from app.integrations.service import get_integration_service
from app.services.agent_service import get_agent_service
from app.graphql.types import TaskExecutionResult, FunctionCall
from app.graphql.context import GraphQLContext


@strawberry.type
class IntegrationMutations:
    @strawberry.mutation
    async def execute_composio_task(
        self,
        message: str,
        info: strawberry.Info[GraphQLContext, None]
    ) -> TaskExecutionResult:
        try:
            user_info = verify_clerk_token(info.context.request)
            clerk_user_id = user_info["clerk_user_id"]
            
            genai_client = info.context.request.app.state.genai_client
            service = get_integration_service(genai_client)
            
            result = await service.execute_with_gemini(
                clerk_user_id=clerk_user_id,
                message=message
            )
            
            function_calls = [
                FunctionCall(
                    name=fc["name"],
                    args=fc.get("args"),
                    result=fc.get("result")
                )
                for fc in result["function_calls"]
            ]
            
            conversation_id = str(uuid.uuid4())
            
            return TaskExecutionResult(
                success=True,
                response=result["response"],
                conversation_id=conversation_id,
                function_calls=function_calls,
                error=None
            )
        except Exception as e:
            return TaskExecutionResult(
                success=False,
                response="",
                conversation_id="",
                function_calls=[],
                error=str(e)
            )
    
    @strawberry.mutation
    async def execute_mcp_task(
        self,
        message: str,
        info: strawberry.Info[GraphQLContext, None],
        conversation_id: Optional[str] = None
    ) -> TaskExecutionResult:
        """
        Execute ANY task with auto-discovered tools from all connected apps.
        Uses Composio Tool Router to automatically discover available tools.
        """
        try:
            user_info = verify_clerk_token(info.context.request)
            clerk_user_id = user_info["clerk_user_id"]
            
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
            
            agent_service = get_agent_service()
            
            result = await agent_service.execute_task(
                user_id=clerk_user_id,
                message=message,
                conversation_id=conversation_id
            )
            
            function_calls = [
                FunctionCall(
                    name=fc["name"],
                    args=fc.get("args"),
                    result=fc.get("result")
                )
                for fc in result["function_calls"]
            ]
            
            return TaskExecutionResult(
                success=True,
                response=result["response"] or "Task completed",
                conversation_id=conversation_id,
                function_calls=function_calls,
                error=None
            )
        except Exception as e:
            import traceback
            print(f"[GraphQL MCP Error] {traceback.format_exc()}")
            return TaskExecutionResult(
                success=False,
                response="",
                conversation_id=conversation_id or "",
                function_calls=[],
                error=str(e)
            )