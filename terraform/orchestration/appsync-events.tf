resource "aws_cloudformation_stack" "appsync_events" {
  name = "cognive-agent-events-stack"
  template_body = jsonencode({
    AWSTemplateFormatVersion = "2010-09-09"
    Description              = "AppSync Events API for AI agent real-time updates"
    Resources = {
      AgentEventsAPI = {
        Type = "AWS::AppSync::Api"
        Properties = {
          Name = "cognive-agent-events"
          EventConfig = {
            AuthProviders = [
              {
                AuthType = "AWS_IAM"
              },
              {
                AuthType = "API_KEY"
              }
            ]
            ConnectionAuthModes = [
              {
                AuthType = "AWS_IAM"
              },
              {
                AuthType = "API_KEY"
              }
            ]
            DefaultPublishAuthModes = [
              {
                AuthType = "AWS_IAM"
              },
              {
                AuthType = "API_KEY"
              }
            ]
            DefaultSubscribeAuthModes = [
              {
                AuthType = "AWS_IAM"
              },
              {
                AuthType = "API_KEY"
              }
            ]
          }
        }
      }
      EventAPIKey = {
        Type = "AWS::AppSync::ApiKey"
        Properties = {
          ApiId       = { "Fn::GetAtt" = ["AgentEventsAPI", "ApiId"] }
          Description = "API key for agent events"
        }
      }
      AgentChannelNamespace = {
        Type = "AWS::AppSync::ChannelNamespace"
        Properties = {
          ApiId = { "Fn::GetAtt" = ["AgentEventsAPI", "ApiId"] }
          Name  = "agent-updates"
          PublishAuthModes = [
            {
              AuthType = "AWS_IAM"
            },
            {
              AuthType = "API_KEY"
            }
          ]
          SubscribeAuthModes = [
            {
              AuthType = "AWS_IAM"
            },
            {
              AuthType = "API_KEY"
            }
          ]
        }
      }
    }
    Outputs = {
      EventAPIId = {
        Value = { "Fn::GetAtt" = ["AgentEventsAPI", "ApiId"] }
      }
      ApiKey = {
        Value = { "Fn::GetAtt" = ["EventAPIKey", "ApiKey"] }
      }
      WebSocketEndpoint = {
        Value = { "Fn::Sub" = "wss://$${AgentEventsAPI.Dns.Realtime}/event" }
      }
      HttpEndpoint = {
        Value = { "Fn::Sub" = "https://$${AgentEventsAPI.Dns.Http}" }
      }
    }
  })
  tags = {
    Environment = "production"
    Service     = "ai-agents"
  }
}