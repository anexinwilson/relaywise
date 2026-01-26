import json
import urllib3
import os

http = urllib3.PoolManager()

def lambda_handler(event, context):
    user_id = event.get('userId')
    message = event.get('message')
    session_id = event.get('sessionId')

    if not user_id or not message:
        return {'success': False, 'error': 'Missing userId or message'}

    agentcore_endpoint = os.environ.get('AGENTCORE_ENDPOINT')
    if not agentcore_endpoint:
        return {'success': False, 'error': 'AgentCore endpoint not configured'}

    try:
        response = http.request(
            'POST',
            agentcore_endpoint,
            body=json.dumps({'userId': user_id, 'message': message, 'sessionId': session_id}),
            headers={'Content-Type': 'application/json'},
            timeout=urllib3.Timeout(connect=5.0, read=900.0)
        )

        if response.status == 200:
            return json.loads(response.data.decode('utf-8'))
        else:
            return {'success': False, 'error': f'Status {response.status}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}