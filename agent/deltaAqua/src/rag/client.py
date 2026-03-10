import json
import asyncio
from typing import List
from pydantic import BaseModel
from agent.client import get_bedrock_client, get_pinecone_index, get_executor
from utils import get_logger

logger = get_logger(__name__)
_executor = get_executor()

class RAGTool(BaseModel):
    tool_slug: str
    tool_id: str
    toolkit: str
    version: str
    description: str
    summary: str = ""
    feature: str = ""
    required_params: List[str] = []
    optional_params: List[str] = []
    score: float

class RAGClient:
    def __init__(self):
        self.index = get_pinecone_index()
        self.bedrock = get_bedrock_client()
    
    async def search_tools(self, query: str, top_k: int = 10) -> List[RAGTool]:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, self._search_tools_sync, query, top_k)
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    def _search_tools_sync(self, query: str, top_k: int = 10) -> List[RAGTool]:
        embedding = self._get_embedding(query)
        if not embedding:
            return []
        
        results = self.index.query(vector=embedding, top_k=top_k, include_metadata=True)
        
        tools = []
        for match in results.matches:
            meta = match.metadata
            if isinstance(meta, str):
                meta = json.loads(meta)
            
            req_params = meta.get("required_params", "")
            opt_params = meta.get("optional_params", "")
            
            tools.append(RAGTool(
                tool_slug=meta.get("slug", ""),
                tool_id=meta.get("tool_id", ""),
                toolkit=meta.get("toolkit", ""),
                version=meta.get("version", ""),
                description=meta.get("text", ""),
                summary=meta.get("summary", ""),
                feature=meta.get("feature", ""),
                required_params=req_params.split(",") if req_params else [],
                optional_params=opt_params.split(",") if opt_params else [],
                score=match.score
            ))
        return tools
    
    def _get_embedding(self, text: str) -> List[float]:
        response = self.bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
        )
        return json.loads(response['body'].read()).get('embedding', [])