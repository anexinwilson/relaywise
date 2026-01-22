import json
import os
import boto3
from functools import lru_cache

secrets_client = boto3.client('secretsmanager')

@lru_cache(maxsize=1)
def get_secrets():
    secret_name = os.environ.get('SECRETS_MANAGER_SECRET_NAME')
    if not secret_name:
        return {}
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"[Error] Failed to get secrets: {e}")
        return {}

def lambda_handler(event, context):
    print(f"[Lambda] Event: {event}")
    
    secrets = get_secrets()
    
    payload = event.get("payload", event)
    field_name = payload.get("field") or payload.get("info", {}).get("fieldName", "")
    arguments = payload.get("arguments", {})
    
    if field_name == "testMutation":
        return {
            "result": f"Lambda works! Message: {arguments.get('message', 'no message')}",
            "success": True
        }
    
    return {
        "result": f"Unknown field: {field_name}",
        "success": False
    }