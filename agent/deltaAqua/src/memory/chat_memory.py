from datetime import datetime, timezone
from config import settings
import logging
import boto3

logger = logging.getLogger(__name__)

class ChatMemory:
    def __init__(self, memory_id: str = settings.AGENTCORE_MEMORY_ID, region: str = settings.AWS_REGION):
        self.memory_id = memory_id
        self.bedrock_client = boto3.client('bedrock-agentcore', region_name=region)
    
    def get_chat_name(self, actor_id: str, session_id: str) -> str | None:
        """Get chat name from first message (Message 0)"""
        try:
            events_response = self.bedrock_client.list_events(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                maxResults=1,  # Only need first message
                includePayloads=True
            )
            
            events = events_response.get('events', [])
            if events:
                event = events[0]
                payload = event.get('payload', [])
                if payload and isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict) and 'conversational' in item:
                            content = item['conversational'].get('content', {})
                            if isinstance(content, dict):
                                chat_name = content.get('text', '')
                                if chat_name:
                                    logger.info(f"Retrieved chat name (first message) for session {session_id}: {chat_name}")
                                    return chat_name
            
            logger.info(f"No messages found for session {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat name for session {session_id}: {e}")
            return None
    
    def store_message(self, actor_id: str, session_id: str, message: str, role: str):
        """Store a message event (no chat_name in metadata)"""
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc)
        
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
        logger.info(f"Stored {role} message for session {session_id}")
    
    def is_first_message(self, actor_id: str, session_id: str) -> bool:
        """Check if this is the first message in the session"""
        try:
            events_response = self.bedrock_client.list_events(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                maxResults=1,
                includePayloads=False
            )
            
            has_events = len(events_response.get('events', [])) > 0
            
            if has_events:
                logger.info(f"Session {session_id} has events - not first message")
                return False
            
            logger.info(f"Session {session_id} has no events - first message")
            return True
            
        except Exception as e:
            logger.error(f"Error checking first message: {e}")
            return False
    
    def get_chat_names(self, actor_id: str, max_results: int = 50):
        try:
            response = self.bedrock_client.list_sessions(
                memoryId=self.memory_id,
                actorId=actor_id,
                maxResults=max_results
            )
            
            titles = []
            for session in response.get('sessionSummaries', []):
                session_id = session.get('sessionId')
                title = self.get_chat_name(actor_id, session_id)
                
                titles.append({
                    'session_id': session_id,
                    'title': title or 'Untitled',
                    'created_at': session.get('createdAt')
                })
            
            return sorted(titles, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting chat names: {e}")
            return []
