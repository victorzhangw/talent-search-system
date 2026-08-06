import os
import sys

# 將 api_v2 的根目錄加入 sys.path，以便正確解析套件內的相對與絕對路徑
API_V2_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if API_V2_DIR not in sys.path:
    sys.path.insert(0, API_V2_DIR)

from utils.token_generator import generate_upstream_token

def main():
    print("--- JWT Token Generator for Testing ---")
    email = input("Enter User Email (default: eva.wepredict@gmail.com): ").strip()
    if not email:
        email = "eva.wepredict@gmail.com"
    
    current_secret = os.getenv('PARTY_A_PLUGIN_SECRET')
    if not current_secret:
        print("\nNOTE: 'PARTY_A_PLUGIN_SECRET' not found in environment variables.")
        print("Using default secret: 'traitty_ai_api'")
        os.environ['PARTY_A_PLUGIN_SECRET'] = "traitty_ai_api"
    else:
        print(f"\nUsing detected secret starting with: {current_secret[:3]}***")

    try:
        token = generate_upstream_token(email)
        print("\n[OK] Token Generated Successfully:")
        print("-" * 60)
        print(token)
        print("-" * 60)
        print(f"User: {email}")
        print("Validity: 15 minutes")
    except Exception as e:
        print(f"\nERROR: Error generating token: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: 未預期的錯誤: {e}")
    finally:
        input("\n請按 Enter 鍵離開...")