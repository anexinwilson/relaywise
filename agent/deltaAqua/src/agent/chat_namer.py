import boto3
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

class ChatNamer:
    def __init__(self, region: str = settings.AWS_REGION):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
    
    async def generate_chat_name(self, user_message: str) -> str:
        """Generate a chat name using Nova Micro"""
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.nova-micro-v1:0',
                body=json.dumps({
                    "messages": [{"role": "user", "content": [{"text": f'Create a short 3-5 word title for this message: "{user_message}"\n\nRules:\n- Return ONLY the title\n- No prefixes like "Chat Name:" or "Title:"\n- No quotes\n- Just the plain title\n\nExample: "New Slack Messages" not "Chat Name: New Slack Messages"'}]}],
                    "inferenceConfig": {"maxTokens": 20, "temperature": 0.3}
                })
            )
            result = json.loads(response['body'].read())
            title = result['output']['message']['content'][0]['text'].strip()
            
            # Remove common prefixes
            prefixes_to_remove = ['Chat Name:', 'Title:', 'Chat:', 'Name:']
            for prefix in prefixes_to_remove:
                if title.startswith(prefix):
                    title = title[len(prefix):].strip()
            
            # Strip quotes
            title = title.strip('"\'')
            
            logger.info(f"Generated chat name: {title}")
            return title
        except Exception as e:
            logger.error(f"Chat name generation failed: {e}")
            return None
