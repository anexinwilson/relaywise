import json
import re
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
    required_params: List[str] = []
    score: float

class RAGClient:
    def __init__(self):
        self.index = get_pinecone_index()
        self.bedrock = get_bedrock_client()
    
    async def search_tools(self, query: str, top_k: int = 10, filter: dict = None) -> List[RAGTool]:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, self._search_tools_sync, query, top_k, filter)
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    def _search_tools_sync(self, query: str, top_k: int = 10, filter: dict = None) -> List[RAGTool]:
        embedding = self._get_embedding(query)
        if not embedding:
            return []
        
        results = self.index.query(vector=embedding, top_k=top_k, filter=filter, include_metadata=True)
        
        tools = []
        for match in results.matches:
            meta = match.metadata
            if isinstance(meta, str):
                meta = json.loads(meta)
            
            tool_slug = meta.get("slug", "")
            toolkit = meta.get("toolkit", "")
            version = meta.get("version", "")
            
            # full prose chunk — contains slug_description, human_description, required
            chunk_text = meta.get("text", "")
            
            # parse required params from chunk text
            required_params = []
            if chunk_text:
                req_match = re.search(r'required:\s*(.+?)(?:\n|$)', chunk_text, re.IGNORECASE)
                if req_match:
                    val = req_match.group(1).strip()
                    if val.lower() != "none":
                        required_params = [v.strip() for v in val.split(",")]
            
            if tool_slug:
                tools.append(RAGTool(
                    tool_slug=tool_slug,
                    tool_id=tool_slug,
                    toolkit=toolkit,
                    version=version,
                    description=chunk_text,
                    required_params=required_params,
                    score=match.score
                ))
        return tools
    
    def _get_embedding(self, text: str) -> List[float]:
        response = self.bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
        )
        return json.loads(response['body'].read()).get('embedding', [])