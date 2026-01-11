
import jwt
import time
import json

# Reference Data from Spec
REFERENCE_PAYLOAD = {
  "email": "eva@wepredict.io",
  "user_id": 1,
  "token_type": "access",
  "jti": "fdaa44c9-3873-4be9-bf1f-d09963e7362e",
  "iat": 1767966098,
  "exp": 1767966998,
  "aud": "traitty",
  "scope": "traitty_plugin"
}

SECRET_KEY = "traitty_ai_api"
EXPECTED_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImV2YUB3ZXByZWRpY3QuaW8iLCJ1c2VyX2lkIjoxLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwianRpIjoiZmRhYTQ0YzktMzg3My00YmU5LWJmMWYtZDA5OTYzZTczNjJlIiwiaWF0IjoxNzY3OTY2MDk4LCJleHAiOjE3Njc5NjY5OTgsImF1ZCI6InRyYWl0dHkiLCJzY29wZSI6InRyYWl0dHlfcGx1Z2luIn0.aZD9C6FxMTRxqM0y5kpyrAdl23eTZWFsCAGB6Adhk_4"

def generate_jwt(payload):
    # NOTE: PyJWT encodes strings by default in newer versions, 
    # but exact sorting might be tricky if we want to match the exact string.
    # However, standard HS256 verification should ideally check the signature validity, 
    # not just string equality (though header order matters for that).
    # Since the user provided an EXACT payload string, let's try to match it.
    
    # We pass headers explicitly to match { "alg": "HS256", "typ": "JWT" }
    token = jwt.encode(
        payload, 
        SECRET_KEY, 
        algorithm="HS256", 
        headers={"alg": "HS256", "typ": "JWT"}
    )
    return token

def verify_token_match():
    print(f"--- Verifying JWT Generation ---")
    generated = generate_jwt(REFERENCE_PAYLOAD)
    
    print(f"Reference: {EXPECTED_TOKEN}")
    print(f"Generated: {generated}")
    
    if generated == EXPECTED_TOKEN:
        print("\n[SUCCESS] Generated token matches exact reference string.")
        return True
    else:
        print("\n[FAIL] Generated token does NOT match reference string.")
        
        # Diagnostics
        header_segment, payload_segment, crypto_segment = generated.split('.')
        ref_header, ref_payload, ref_crypto = EXPECTED_TOKEN.split('.')
        
        if header_segment != ref_header:
            print("Header mismatch!")
        if payload_segment != ref_payload:
            print("Payload mismatch! (Likely JSON key sorting differences)")
        if crypto_segment != ref_crypto:
            print("Signature mismatch!")
            
        return False

if __name__ == "__main__":
    verify_token_match()
