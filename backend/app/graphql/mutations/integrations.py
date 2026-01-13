import strawberry
from app.auth.middleware import verify_clerk_token
from app.integrations.service import get_integration_service
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
            
            return TaskExecutionResult(
                success=True,
                response=result["response"],
                function_calls=function_calls,
                error=None
            )
        except Exception as e:
            return TaskExecutionResult(
                success=False,
                response="",
                function_calls=[],
                error=str(e)
            )