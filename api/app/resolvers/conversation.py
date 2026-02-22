import boto3
import os
from typing import List, Dict, Optional
from datetime import datetime

try:
    from app.config.settings import settings
    AGENTCORE_MEMORY_ID = os.getenv('AGENTCORE_MEMORY_ID') or getattr(settings, 'AGENTCORE_MEMORY_ID', None)
except ImportError:
    AGENTCORE_MEMORY_ID = os.getenv('AGENTCORE_MEMORY_ID')

bedrock_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

def get_user_conversations(obj, info, userId: str) -> List[Dict]:
    try:
        if not AGENTCORE_MEMORY_ID:
            return []
        
        all_sessions = []
        next_token = None

        while True:
            params = {
                'memoryId': AGENTCORE_MEMORY_ID,
                'actorId': userId,
                'maxResults': 100
            }
            if next_token:
                params['nextToken'] = next_token

            response = bedrock_client.list_sessions(**params)

            for session in response.get('sessionSummaries', []):
                if not isinstance(session, dict):
                    continue
                session_id = session.get('sessionId')
                if session_id is None:
                    continue
                created_at = session.get('createdAt')
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                elif created_at is not None:
                    created_at = str(created_at)
                
                chat_name = _get_chat_name_from_metadata(userId, session_id)
                
                all_sessions.append({
                    'sessionId': session_id,
                    'chatName': chat_name,
                    'createdAt': created_at
                })

            next_token = response.get('nextToken')
            if not next_token:
                break

        return all_sessions
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return []

def _get_chat_name_from_summaries(userId: str, sessionId: str) -> str:
    try:
        return _get_chat_name_from_metadata(userId, sessionId)
    except Exception as e:
        print(f"Error getting chat name for session {sessionId}: {e}")
        return 'New Conversation'

def _get_chat_name_from_metadata(userId: str, sessionId: str) -> str:
    try:
        params = {
            'memoryId': AGENTCORE_MEMORY_ID,
            'actorId': userId,
            'sessionId': sessionId,
            'maxResults': 10,
            'includePayloads': False
        }
        
        response = bedrock_client.list_events(**params)
        events = response.get('events', [])
        
        for event in events:
            if not isinstance(event, dict):
                continue
            
            metadata = event.get('metadata', {})
            event_type = metadata.get('event_type', {})
            if isinstance(event_type, dict):
                event_type_value = event_type.get('stringValue', '')
            else:
                event_type_value = str(event_type)
            
            if event_type_value == 'chat_title':
                chat_title = metadata.get('chat_title', {})
                if isinstance(chat_title, dict):
                    title = chat_title.get('stringValue', '')
                else:
                    title = str(chat_title)
                if title:
                    return title
        
        if events:
            params['includePayloads'] = True
            params['maxResults'] = 50
            response = bedrock_client.list_events(**params)
            
            for event in reversed(response.get('events', [])):
                payload = event.get('payload', [])
                if payload and isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict) and 'conversational' in item:
                            conv = item['conversational']
                            role = conv.get('role', '').upper()
                            if role == 'USER':
                                content = conv.get('content', {})
                                text = content.get('text', '') if isinstance(content, dict) else str(content)
                                if text and len(text) > 0:
                                    return text[:50] + ('...' if len(text) > 50 else '')
        
        return 'New Conversation'
    except Exception as e:
        print(f"Error in metadata chat name for session {sessionId}: {e}")
        return 'New Conversation'

def get_conversation_messages(obj, info, userId: str, sessionId: str) -> List[Dict]:
    try:
        if not AGENTCORE_MEMORY_ID:
            return []
        
        messages = []
        next_token = None
        
        while True:
            params = {
                'memoryId': AGENTCORE_MEMORY_ID,
                'actorId': userId,
                'sessionId': sessionId,
                'maxResults': 100,
                'includePayloads': True
            }
            if next_token:
                params['nextToken'] = next_token
            
            response = bedrock_client.list_events(**params)
            
            for event in response.get('events', []):
                if not isinstance(event, dict):
                    continue
                
                metadata = event.get('metadata', {})
                event_type = metadata.get('event_type', {})
                if isinstance(event_type, dict):
                    event_type_value = event_type.get('stringValue', '')
                else:
                    event_type_value = str(event_type)
                
                if event_type_value == 'chat_title':
                    continue
                
                event_id = event.get('eventId')
                event_timestamp = event.get('eventTimestamp')
                payload = event.get('payload', [])
                
                if hasattr(event_timestamp, 'isoformat'):
                    created_at = event_timestamp.isoformat()
                elif event_timestamp is not None:
                    created_at = str(event_timestamp)
                else:
                    created_at = ''
                
                if payload and isinstance(payload, list):
                    for idx, item in enumerate(payload):
                        if isinstance(item, dict) and 'conversational' in item:
                            conv = item['conversational']
                            role = conv.get('role', '').upper()
                            content_data = conv.get('content', {})
                            content = content_data.get('text', '') if isinstance(content_data, dict) else str(content_data)
                            sender = 'user' if role == 'USER' else 'assistant'
                            
                            if content:
                                # Create unique ID by combining event_id with index and role
                                unique_id = f"{event_id}_{idx}_{role.lower()}" if event_id else f"{created_at}_{idx}_{role.lower()}"
                                messages.append({
                                    'id': unique_id,
                                    'sender': sender,
                                    'content': content,
                                    'timestamp': created_at,
                                    'type': sender.upper()
                                })
            
            next_token = response.get('nextToken')
            if not next_token:
                break
        
        messages.sort(key=lambda x: x.get('timestamp', ''))
        
        return messages
    except Exception as e:
        print(f"Error fetching conversation messages for session {sessionId}: {e}")
        return []