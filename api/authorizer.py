import os
import jwt
from jwt import PyJWKClient
from functools import lru_cache
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# Get Clerk domain from environment (uses .env locally, Lambda env vars in production)
CLERK_DOMAIN = os.environ.get('CLERK_DOMAIN', 'arriving-stinkbug-51.clerk.accounts.dev')

@lru_cache(maxsize=1)
def get_jwks_client():
    """Get cached JWKS client for Clerk"""
    return PyJWKClient(f"https://{CLERK_DOMAIN}/.well-known/jwks.json")

def lambda_handler(event, context):
    """AppSync Lambda Authorizer - Official AWS Approach"""
    print(f"[Authorizer] Event: {event}")
    
    try:
        # Get token from authorization header
        auth_header = event.get('authorizationToken', '')
        if not auth_header.startswith('Bearer '):
            return {
                "isAuthorized": False,
                "context": {}
            }
        
        token = auth_header.replace('Bearer ', '')
        
        # Get JWKS client
        jwks_client = get_jwks_client()
        
        # Get signing key from JWT
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify and decode JWT
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=f"https://{CLERK_DOMAIN}"
        )
        
        print(f"[Authorizer] Token verified for user: {decoded_token.get('sub')}")
        
        return {
            "isAuthorized": True,
            "resolverContext": {
                "userId": decoded_token.get('sub'),
                "email": decoded_token.get('email', ''),
                "name": decoded_token.get('name', '')
            },
            "ttlOverride": 300
        }
        
    except jwt.ExpiredSignatureError:
        print("[Authorizer] Token has expired")
        return {"isAuthorized": False, "context": {}}
    except jwt.InvalidTokenError as e:
        print(f"[Authorizer] Invalid token: {str(e)}")
        return {"isAuthorized": False, "context": {}}
    except Exception as e:
        print(f"[Authorizer] Error: {str(e)}")
        return {"isAuthorized": False, "context": {}}