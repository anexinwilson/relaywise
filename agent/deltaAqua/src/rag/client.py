import json
import boto3
from typing import List, Dict, Optional
from pinecone import Pinecone
from config import settings
from utils import get_logger

logger = get_logger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    def generate(self, text: str) -> Optional[List[float]]:
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.titan-embed-text-v2:0',
                body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
            )
            return json.loads(response['body'].read()).get('embedding')
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

class MetadataParser:
    @staticmethod
    def parse(raw_metadata: any) -> Dict:
        try:
            if isinstance(raw_metadata, str):
                meta = json.loads(raw_metadata)
            else:
                meta = raw_metadata
            
            no_auth_str = meta.get("no_auth", "False")
            no_auth = no_auth_str == "True" if isinstance(no_auth_str, str) else bool(no_auth_str)
            
            return {
                "tool_slug": meta.get("slug", ""),
                "tool_id": meta.get("tool_id", ""),
                "toolkit": meta.get("toolkit", ""),
                "description": meta.get("text", ""),
                "no_auth": no_auth,
                "required_params": [p.strip() for p in meta.get("required_params", "").split(",") if p.strip()],
                "optional_params": [p.strip() for p in meta.get("optional_params", "").split(",") if p.strip()],
                "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
            }
        except Exception as e:
            logger.error(f"Metadata parse failed: {e}")
            return {}

class RAGClient:
    def __init__(self):
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = pc.Index(settings.PINECONE_INDEX_NAME)
        self.embeddings = EmbeddingGenerator()
        self.parser = MetadataParser()
    
    def find_tools(self, query: str, intent: str = "action", top_k: Optional[int] = None) -> List[Dict]:
        if top_k is None:
            top_k = {"list_all": 862, "list_filtered": 50, "specific_app": 100}.get(intent, 10)
        
        embedding = self.embeddings.generate(query)
        if not embedding:
            return []
        
        try:
            results = self.index.query(vector=embedding, top_k=top_k, include_metadata=True)
            tools = []
            for match in results.matches:
                parsed = self.parser.parse(match.metadata)
                if parsed.get("tool_slug"):
                    parsed["score"] = match.score
                    tools.append(parsed)
            logger.info(f"Found {len(tools)} tools for intent: {intent}")
            return tools
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return []