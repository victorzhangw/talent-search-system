
import os
import sys

# Ensure the parent directory is in python path to resolve module imports if needed, 
# although standalone execution might be simpler if we just import the function.
# Or we can just inline the logic if imports are tricky for a standalone script without app context.
# But let's try to import the adjacent module.

try:
    from token_generator import generate_upstream_token
except ImportError:
    # If run directly inside the folder, import might fail without package structure.
    # We add the parent dir to path to allow importing if needed, or just copy logic for a pure test script.
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from token_generator import generate_upstream_token

def main():
    print("--- JWT Token Generator for Testing ---")
    email = input("Enter User Email (default: test@example.com): ").strip()
    if not email:
        email = "test@example.com"
    
    # Optional: Allow manually setting secret for test if not in env
    current_secret = os.getenv('PARTY_A_PLUGIN_SECRET')
    if not current_secret:
        print("\nNOTE: 'PARTY_A_PLUGIN_SECRET' not found in environment variables.")
        print("Using default secret: 'traitty_ai_api'")
        # Ensure the environment variable is set for the generator to pick it up if it reads os.getenv directly
        os.environ['PARTY_A_PLUGIN_SECRET'] = "traitty_ai_api"
    else:
        print(f"\nUsing detected secret starting with: {current_secret[:3]}***")

    try:
        token = generate_upstream_token(email)
        print("\n✅ Token Generated Successfully:")
        print("-" * 60)
        print(token)
        print("-" * 60)
        print(f"User: {email}")
        print("Validity: 15 minutes")
    except Exception as e:
        print(f"\n❌ Error generating token: {e}")

if __name__ == "__main__":
    main()
    input("\n請按 Enter 鍵離開...")
