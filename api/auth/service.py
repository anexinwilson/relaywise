from clerk_backend_api import Clerk
import os
from typing import Dict, Any

class ClerkAuthService:
    def __init__(self):
        clerk_secret = os.environ.get('CLERK_SECRET_KEY')
        if not clerk_secret:
            raise ValueError("CLERK_SECRET_KEY not set")
        self.clerk = Clerk(bearer_auth=clerk_secret)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Fast JWT verification - only validates token"""
        try:
            session = self.clerk.sessions.verify(token)
            user = session.user
            
            email = user.email_addresses[0].email_address if user.email_addresses else ''
            
            return {
                'userId': user.id,
                'email': email,
                'firstName': user.first_name or '',
                'lastName': user.last_name or ''
            }
        except Exception as e:
            print(f"[Auth] Token verification failed: {str(e)}")
            raise