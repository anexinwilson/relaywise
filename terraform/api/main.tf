terraform {
  required_version = "~> 1.15"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Applied to every taggable resource in this stack. Makes Cost Explorer
  # groupable by project and marks these resources as Terraform-owned so nobody
  # edits them by hand in the console.
  default_tags {
    tags = {
      Project   = "relaywise"
      Stack     = "api"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
