import json
import jwt
import boto3
from jwt import PyJWKClient
from functools import lru_cache

def get_secret():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='cognive/lambda/secrets')
    return json.loads(response['SecretString'])

@lru_cache(maxsize=1)
def get_clerk_domain():
    secret = get_secret()
    return secret['CLERK_DOMAIN']

@lru_cache(maxsize=1)
def get_jwks_client():
    domain = get_clerk_domain()
    return PyJWKClient(f"https://{domain}/.well-known/jwks.json")

def lambda_handler(event, context):
    try:
        auth_header = event.get('authorizationToken', '')
        if not auth_header.startswith('Bearer '):
            return {"isAuthorized": False, "context": {}}
        
        token = auth_header.replace('Bearer ', '')
        domain = get_clerk_domain()
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=f"https://{domain}"
        )
        
        return {
            "isAuthorized": True,
            "resolverContext": {
                "userId": decoded_token.get('sub')
            },
            "ttlOverride": 300
        }
        
    except jwt.ExpiredSignatureError:
        return {"isAuthorized": False, "context": {}}
    except jwt.InvalidTokenError:
        return {"isAuthorized": False, "context": {}}
    except Exception:
        return {"isAuthorized": False, "context": {}}