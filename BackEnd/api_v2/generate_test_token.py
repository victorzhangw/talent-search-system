# Simple script to generate a JWT for Postman testing
import sys
import os

# Add current directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.token_generator import generate_upstream_token

def main():
    email = "eva@wepredict.io"
    if len(sys.argv) > 1:
        email = sys.argv[1]
    
    print(f"Generating Token for: {email}")
    token = generate_upstream_token(email)
    print("\n" + "="*50)
    print("Bearer Token (Valid for 15 mins):")
    print("="*50)
    print(token)
    print("="*50 + "\n")

    print("Postman Usage:")
    print("1. Method: POST / GET")
    print("2. URL: https://uat.traitty.com/v1/candidates/ (or local /api/v2/...)")
    print(f"3. Header: Authorization: Bearer {token[:10]}...")

if __name__ == "__main__":
    main()
