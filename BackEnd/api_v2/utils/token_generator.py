import os
import jwt
import time
import uuid
import logging
from flask import current_app
from .logger import get_daily_logger

def get_token_logger():
    return get_daily_logger("TokenGenerator", "token_generator.log", level=logging.INFO)

token_logger = get_token_logger()

def generate_upstream_token(user_email: str) -> str:
    """
    Generates a fresh short-lived JWT token for calling Traitty API.
    Standardizes the logic previously scattered in auth.py.
    """
    secret = os.getenv('PARTY_A_PLUGIN_SECRET', "traitty_ai_api")
    if secret == "traitty_ai_api":
        token_logger.warning("Using default insecure secret 'traitty_ai_api'. Set PARTY_A_PLUGIN_SECRET in .env")
    
    payload = {
      "email": user_email,
      "user_id": 1, # Placeholder if upstream doesn't check user_id strictness
      "token_type": "access",
      "jti": str(uuid.uuid4()),
      "iat": int(time.time()) - 60, # Backdate 60s for clock skew
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
