import boto3
from concurrent.futures import ThreadPoolExecutor
from pinecone import Pinecone
from composio import Composio
from bedrock_agentcore.memory import MemoryClient
from config import settings

_bedrock_client = None
_pinecone_index = None
_composio_client = None
_memory_client = None
_executor = ThreadPoolExecutor(max_workers=4)

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)
    return _bedrock_client

def get_memory_client():
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryClient(region_name=settings.AWS_REGION)
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

def get_executor():
    return _executor
