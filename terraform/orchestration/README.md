# AppSync Orchestration Infrastructure

This Terraform module sets up AWS AppSync GraphQL API for orchestrating requests between the API and Agent services.

## Architecture

```
Next.js (Vercel) 
    ↓
AppSync GraphQL API
    ↓
Lambda Resolver (Auth + Bedrock AgentCore)
    ↓
Bedrock AgentCore (LangGraph Agent)
    ↓
Composio + Pinecone + Gemini
```

## Components

- **AppSync GraphQL API**: Managed GraphQL endpoint
- **Lambda Data Source**: Resolver that handles auth and invokes Bedrock AgentCore
- **IAM Roles**: Permissions for AppSync → Lambda → Bedrock

## Usage

1. **Set variables** in `terraform.tfvars`:
```hcl
aws_region = "us-east-1"
lambda_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:appsync-resolver"
appsync_api_name = "cognive-graphql-api"
environment = "dev"
```

2. **Initialize and apply**:
```bash
cd terraform/orchestration
terraform init
terraform plan
terraform apply
```

3. **Get outputs**:
```bash
terraform output appsync_api_url
terraform output appsync_api_key  # For API_KEY auth
```

## Lambda Function Requirements

Your Lambda function should:
- Accept AppSync event format
- Verify Clerk token from headers
- Invoke Bedrock AgentCore synchronously
- Return GraphQL-compatible response

Example Lambda handler structure:
```python
def handler(event, context):
    field = event['field']
    headers = event.get('request', {}).get('headers', {})
    
    # Verify Clerk token
    clerk_token = headers.get('authorization', '').replace('Bearer ', '')
    user_info = verify_clerk_token(clerk_token)
    
    if field == 'executeMcpTask':
        # Invoke Bedrock AgentCore
        result = invoke_bedrock_agentcore(
            message=event['arguments']['message'],
            user_id=user_info['clerk_user_id'],
            conversation_id=event['arguments'].get('conversationId')
        )
        return result
    
    return {"error": "Unknown field"}
```

## Authentication

Currently configured for `API_KEY` authentication at the AppSync level. **Clerk authentication is handled in the Lambda resolver** by verifying the `Authorization` header token.

The flow:
1. Client sends request to AppSync with `x-api-key` header (AppSync auth)
2. Client also includes `Authorization: Bearer <clerk_token>` header
3. Lambda resolver extracts Clerk token and verifies it
4. Lambda proceeds with authenticated user context

To switch AppSync auth to AWS_IAM:
1. Update `authentication_type` in `appsync.tf` to `AWS_IAM`
2. Update client to use AWS credentials instead of API key
3. Clerk verification in Lambda remains the same

## Next Steps

- Add EventBridge configuration for async workflows
- Add subscriptions for real-time updates
- Add caching configuration
- Add custom domain
