from bedrock_agentcore.memory import MemoryClient
from datetime import datetime
from config import settings
import logging
import boto3

logger = logging.getLogger(__name__)

class ChatMemory:
    def __init__(self, memory_id: str = settings.AGENTCORE_MEMORY_ID, region: str = settings.AWS_REGION):
        self.memory_id = memory_id
        self.client = MemoryClient(region_name=region)
        self.bedrock_client = boto3.client('bedrock-agentcore', region_name=region)
    
    def _sanitize_metadata_value(self, value: str) -> str:
        import re
        return re.sub(r'[^a-zA-Z0-9\s._:/=+@-]', '', value)
    
    def store_chat_title(self, actor_id: str, session_id: str, title: str):
        timestamp = datetime.utcnow()
        sanitized_title = self._sanitize_metadata_value(title)
        self.bedrock_client.create_event(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=timestamp,
            payload=[{
                'conversational': {
                    'role': 'OTHER',
                    'content': {'text': title}
                }
            }],
            metadata={
                'chat_title': {'stringValue': sanitized_title},
                'event_type': {'stringValue': 'chat_title'},
                'created_at': {'stringValue': timestamp.isoformat()}
            }
        )
        logger.info(f"Stored chat name: {title}")
    
    def store_message(self, actor_id: str, session_id: str, message: str, role: str):
        timestamp = datetime.utcnow()
        self.bedrock_client.create_event(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=timestamp,
            payload=[{
                'conversational': {
                    'role': role,
                    'content': {'text': message}
                }
            }],
            metadata={
                'event_type': {'stringValue': f'{role.lower()}_message'},
                'source': {'stringValue': 'agent'}
            }
        )
        logger.info(f"Stored {role} message")
    
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
        try:
            response = self.bedrock_client.list_sessions(
                memoryId=self.memory_id,
                actorId=actor_id,
                maxResults=max_results
            )
            
            titles = []
            for session in response.get('sessionSummaries', []):
                session_id = session.get('sessionId')
                
                events_response = self.bedrock_client.list_events(
                    memoryId=self.memory_id,
                    actorId=actor_id,
                    sessionId=session_id,
                    maxResults=5,
                    includePayloads=False
                )
                
                title = 'Untitled'
                for event in events_response.get('events', []):
                    metadata = event.get('metadata', {})
                    if metadata.get('event_type', {}).get('stringValue') == 'chat_title':
                        title = metadata.get('chat_title', {}).get('stringValue', 'Untitled')
                        break
                
                titles.append({
                    'session_id': session_id,
                    'title': title,
                    'created_at': session.get('createdAt')
                })
            
            return sorted(titles, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting chat titles: {e}")
            return []
