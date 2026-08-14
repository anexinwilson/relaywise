"""Test configuration.

`app.core.config` builds its Settings at import time, so the environment has to
be populated before any `app.*` module is imported.
"""

import os

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("UPSTASH_REDIS_REST_URL", "https://redis.invalid")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "test-token")
os.environ.setdefault("CLERK_DOMAIN", "clerk.example.com")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/000/test.fifo")
