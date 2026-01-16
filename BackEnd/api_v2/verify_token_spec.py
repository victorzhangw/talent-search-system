import jwt
import os

# 1. Spec provided by user
spec_secret = "traitty_ai_api"
spec_payload = {
  "email": "eva@wepredict.io",
  "user_id": 1,
  "token_type": "access",
  "jti": "fdaa44c9-3873-4be9-bf1f-d09963e7362e",
  "iat": 1767966098,
  "exp": 1767966998,
  "aud": "traitty",
  "scope": "traitty_plugin"
}
spec_expected_signature_part = "aZD9C6FxMTRxqM0y5kpyrAdl23eTZWFsCAGB6Adhk_4"
# Full token example from user
spec_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImV2YUB3ZXByZWRpY3QuaW8iLCJ1c2VyX2lkIjoxLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwianRpIjoiZmRhYTQ0YzktMzg3My00YmU5LWJmMWYtZDA5OTYzZTczNjJlIiwiaWF0IjoxNzY3OTY2MDk4LCJleHAiOjE3Njc5NjY5OTgsImF1ZCI6InRyYWl0dHkiLCJzY29wZSI6InRyYWl0dHlfcGx1Z2luIn0.aZD9C6FxMTRxqM0y5kpyrAdl23eTZWFsCAGB6Adhk_4"

print("=== User Spec Verification ===")

# 2. Generate Trace
generated_token = jwt.encode(
    spec_payload, 
    spec_secret, 
    algorithm="HS256", 
    headers={"alg": "HS256", "typ": "JWT"}
)

print(f"Spec Token:      {spec_token}")
print(f"Generated Token: {generated_token}")

if generated_token == spec_token:
    print("✅ SUCCESS: Generated token EXACTLY matches the user spec.")
else:
    print("❌ FAILURE: Generated token does NOT match user spec.")
    
    # Debug parts
    print("\nHeader Comparison:")
    # We can't easily decode header order without raw decode, but let's check payload correctness
    decoded = jwt.decode(generated_token, spec_secret, algorithms=["HS256"], audience="traitty")
    print(f"Decoded Payload: {decoded}")
    
# 3. Verify Env Var Logic (Simulated)
print("\n=== Env Var Logic Check ===")
os.environ['PARTY_A_PLUGIN_SECRET'] = "test_secret_123"
from utils.token_generator import generate_upstream_token
test_token = generate_upstream_token("test@example.com")
# Try to decode with test secret
try:
    jwt.decode(test_token, "test_secret_123", algorithms=["HS256"], audience="traitty", options={"verify_exp": False})
    print("✅ SUCCESS: generate_upstream_token picked up PARTY_A_PLUGIN_SECRET.")
except Exception as e:
    print(f"❌ FAILURE: generate_upstream_token failed to use env secret: {e}")
