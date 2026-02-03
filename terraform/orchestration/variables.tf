variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "agentcore_endpoint" {
  type        = string
  description = "AgentCore endpoint (ngrok URL or deployed URL)"
}
