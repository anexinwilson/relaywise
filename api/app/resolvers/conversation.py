import boto3
import os
from typing import List, Dict

bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
AGENTCORE_MEMORY_ID = os.getenv('AGENTCORE_MEMORY_ID')

async def get_user_conversations(obj, info, userId: str) -> List[Dict]:
    try:
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
                session_id = session['sessionId']
                created_at = session.get('createdAt')
                
                chat_name = 'New Conversation'
                try:
                    events = bedrock_client.get_events(
                        memoryId=AGENTCORE_MEMORY_ID,
                        actorId=userId,
                        sessionId=session_id,
                        maxResults=10
                    )
                    
                    for event in events.get('events', []):
                        metadata = event.get('metadata', {})
                        if metadata.get('chatName'):
                            chat_name = metadata['chatName']
                            break
                except:
                    pass
                
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
