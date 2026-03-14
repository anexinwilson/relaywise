import boto3
import os
from typing import List, Dict, Optional
from datetime import datetime

try:
    from app.config.settings import settings
    from app.config.redis import redis_client
    AGENTCORE_MEMORY_ID = os.getenv('AGENTCORE_MEMORY_ID') or getattr(settings, 'AGENTCORE_MEMORY_ID', None)
except ImportError:
    AGENTCORE_MEMORY_ID = os.getenv('AGENTCORE_MEMORY_ID')
    redis_client = None

bedrock_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

def get_user_conversations(obj, info, userId: str) -> List[Dict]:
    try:
        print(f"=== API USING MEMORY ID: {AGENTCORE_MEMORY_ID} ===")
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

                metadata = _get_session_metadata(userId, session_id)
                last_modified = metadata['lastModifiedAt'] or created_at

                all_sessions.append({
                    'sessionId': session_id,
                    'chatName': metadata['chatName'],
                    'lastModifiedAt': last_modified
                })

            next_token = response.get('nextToken')
            if not next_token:
                break

        return all_sessions
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return []

def _get_session_metadata(userId: str, sessionId: str) -> Dict:
    """Get chat name (oldest event) and lastModifiedAt (newest event timestamp)."""
    try:
        events_response = bedrock_client.list_events(
            memoryId=AGENTCORE_MEMORY_ID,
            actorId=userId,
            sessionId=sessionId,
            maxResults=100,
            includePayloads=True
        )

        events = events_response.get('events', [])
        if not events:
            return {'chatName': None, 'lastModifiedAt': None}

        # Events are newest-first: events[0] is latest, events[-1] is oldest
        newest_event = events[0]
        oldest_event = events[-1]

        # Get lastModifiedAt from newest event timestamp
        last_modified = newest_event.get('eventTimestamp')
        if hasattr(last_modified, 'isoformat'):
            last_modified = last_modified.isoformat()
        elif last_modified is not None:
            last_modified = str(last_modified)

        # Get chat name from oldest event content
        chat_name = None
        payload = oldest_event.get('payload', [])
        if payload and isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and 'conversational' in item:
                    content = item['conversational'].get('content', {})
                    if isinstance(content, dict):
                        chat_name = content.get('text', '')
                        break

        return {'chatName': chat_name, 'lastModifiedAt': last_modified}

    except Exception as e:
        print(f"Error getting session metadata for {sessionId}: {e}")
        return {'chatName': None, 'lastModifiedAt': None}

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
                    for item in payload:
                        if isinstance(item, dict) and 'conversational' in item:
                            conv = item['conversational']
                            role = conv.get('role', '').upper()
                            
                            content_data = conv.get('content', {})
                            content = content_data.get('text', '') if isinstance(content_data, dict) else str(content_data)
                            sender = 'user' if role == 'USER' else 'assistant'
                            
                            if content:
                                unique_id = event_id if event_id else created_at
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


def delete_conversation(obj, info, userId: str, sessionId: str) -> Dict:
    """Delete all events in a conversation session from AgentCore Memory."""
    try:
        if not AGENTCORE_MEMORY_ID:
            return {'success': False, 'error': 'Memory ID not configured'}

        # List all events for this session (paginate to get all)
        all_event_ids = []
        next_token = None

        while True:
            params = {
                'memoryId': AGENTCORE_MEMORY_ID,
                'actorId': userId,
                'sessionId': sessionId,
                'maxResults': 100,
            }
            if next_token:
                params['nextToken'] = next_token

            response = bedrock_client.list_events(**params)

            for event in response.get('events', []):
                event_id = event.get('eventId')
                if event_id:
                    all_event_ids.append(event_id)

            next_token = response.get('nextToken')
            if not next_token:
                break

        deleted_count = 0
        failed_events = []
        
        for event_id in all_event_ids:
            try:
                bedrock_client.delete_event(
                    memoryId=AGENTCORE_MEMORY_ID,
                    sessionId=sessionId,
                    eventId=event_id,
                    actorId=userId,
                )
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting event {event_id}: {e}")
                failed_events.append(event_id)

        if failed_events:
            return {
                'success': False, 
                'error': f'Failed to delete {len(failed_events)} events',
                'deletedCount': deleted_count
            }

        print(f"Deleted {deleted_count}/{len(all_event_ids)} events for session {sessionId}")

        return {'success': True, 'deletedCount': deleted_count}

    except Exception as e:
        print(f"Error deleting conversation {sessionId}: {e}")
        return {'success': False, 'error': str(e)}