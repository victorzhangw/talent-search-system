import jwt
import time
import uuid
from flask import current_app

def generate_upstream_token(user_email: str) -> str:
    """
    Generates a fresh short-lived JWT token for calling Traitty API.
    Standardizes the logic previously scattered in auth.py.
    """
    secret = "traitty_ai_api"  # TODO: Move to Config if strict, matching auth.py for now
    
    payload = {
      "email": user_email,
      "user_id": 1, # Placeholder if upstream doesn't check user_id strictness
      "token_type": "access",
      "jti": str(uuid.uuid4()),
      "iat": int(time.time()),
      "exp": int(time.time()) + 900, # 15 mins validity
      "aud": "traitty",
      "scope": "traitty_plugin"
    }

    token = jwt.encode(
        payload, 
        secret, 
        algorithm="HS256", 
        headers={"alg": "HS256", "typ": "JWT"}
    )
    
    return token
