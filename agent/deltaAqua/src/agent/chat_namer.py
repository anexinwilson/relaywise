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
                    "messages": [{"role": "user", "content": [{"text": f'Given this message: "{user_message}"\n\nGenerate a short 4-6 word chat title. Return only the title, nothing else.'}]}],
                    "inferenceConfig": {"maxTokens": 20, "temperature": 0.3}
                })
            )
            result = json.loads(response['body'].read())
            title = result['output']['message']['content'][0]['text'].strip()
            logger.info(f"Generated chat name: {title}")
            return title
        except Exception as e:
            logger.error(f"Chat name generation failed: {e}")
            return "New Conversation"
