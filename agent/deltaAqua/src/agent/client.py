import boto3
from concurrent.futures import ThreadPoolExecutor
from pinecone import Pinecone
from composio import Composio
from upstash_redis import Redis
from config import settings

_bedrock_client = None
_pinecone_index = None
_composio_client = None
_memory_client = None
_redis_client = None
_executor = ThreadPoolExecutor(max_workers=4)

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)
    return _bedrock_client

def get_memory_client():
    global _memory_client
    if _memory_client is None:
        _memory_client = boto3.client('bedrock-agentcore', region_name=settings.AWS_REGION)
    return _memory_client

def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index

def get_composio_client():
    global _composio_client
    if _composio_client is None:
        _composio_client = Composio(api_key=settings.COMPOSIO_API_KEY)
    return _composio_client

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
        )
    return _redis_client

def get_executor():
    return _executor
