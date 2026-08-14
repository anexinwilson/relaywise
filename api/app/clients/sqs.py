"""SQS client."""

from __future__ import annotations

from functools import lru_cache

import boto3

from app.core.config import settings


@lru_cache(maxsize=1)
def get_sqs():
    return boto3.client("sqs", region_name=settings.AWS_REGION)
