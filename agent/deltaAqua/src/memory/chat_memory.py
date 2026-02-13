from bedrock_agentcore.memory import MemoryClient
from datetime import datetime
from config import settings
import logging

logger = logging.getLogger(__name__)

class ChatMemory:
    def __init__(self, memory_id: str = settings.AGENTCORE_MEMORY_ID, region: str = settings.AWS_REGION):
        self.memory_id = memory_id
        self.client = MemoryClient(region_name=region)
    
    def store_chat_title(self, actor_id: str, session_id: str, title: str):
        """Store chat title on first message"""
        timestamp = datetime.utcnow().isoformat()
        self.client.create_event(
            memory_id=self.memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[(f"CHAT_TITLE: {title} | SESSION_ID: {session_id} | STARTED: {timestamp}", "USER")]
        )
        logger.info(f"Stored chat title: {title}")
    
    def is_first_message(self, actor_id: str, session_id: str) -> bool:
        """Check if this is the first message in a session"""
        try:
            sessions = self.client.list_sessions(
                memory_id=self.memory_id,
                actor_id=actor_id,
                max_results=1
            )
            
            if not sessions.get('sessionSummaries'):
                return True
            
            for session in sessions.get('sessionSummaries', []):
                if session.get('sessionId') == session_id:
                    return False
            
            return True
        except:
            return True
    
    def get_chat_titles(self, actor_id: str, max_results: int = 50):
        """Retrieve all chat titles for a user"""
        memories = self.client.retrieve_memories(
            memory_id=self.memory_id,
            actor_id=actor_id,
            query="CHAT_TITLE session started",
            max_results=max_results
        )
        
        titles = []
        for mem in memories.get('memories', []):
            content = mem.get('content', '')
            if 'CHAT_TITLE:' in content:
                start = content.find('CHAT_TITLE:') + 12
                end = content.find('|', start)
                title = content[start:end].strip() if end != -1 else content[start:].strip()
                titles.append({
                    'session_id': mem.get('sessionId'),
                    'title': title,
                    'created_at': mem.get('createdAt')
                })
        
        return sorted(titles, key=lambda x: x.get('created_at', ''), reverse=True)
