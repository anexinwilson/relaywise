"""Test configuration.

`config.py` builds its Settings at import time, so the environment must be
populated before any module that imports it.
"""

import os

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("COMPOSIO_API_KEY", "test-composio-key")
os.environ.setdefault("CALLBACK_URL", "http://localhost:3000/integrations")
os.environ.setdefault("BEDROCK_MANTLE_BASE_URL", "https://mantle.invalid/v1")
os.environ.setdefault("BEDROCK_MANTLE_API_KEY", "test-mantle-key")
os.environ.setdefault("BEDROCK_MODEL_ID", "test-model")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("APPSYNC_EVENTS_ENDPOINT", "https://appsync.invalid/graphql")
os.environ.setdefault("APPSYNC_API_KEY", "test-appsync-key")
os.environ.setdefault("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/000/test.fifo")
os.environ.setdefault("UPSTASH_REDIS_REST_URL", "https://redis.invalid")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "test-token")
