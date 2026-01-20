
import sys
import os

# Add project root (D:\python\AI-Character-Chatbot)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

print(f"Project Root: {project_root}")
print(f"Sys Path: {sys.path}")

try:
    from backend.api_v2.database.connection import get_db_session
    from backend.api_v2.database.models import AdminUser
    from backend.api_v2.admin.auth import get_password_hash
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
    # Try alternative import if backend is in path?
    try:
        sys.path.append(os.path.join(project_root, 'backend'))
        from api_v2.database.connection import get_db_session
        from api_v2.database.models import AdminUser
        from api_v2.admin.auth import get_password_hash
        print("Alternative imports successful")
    except ImportError as e2:
        print(f"Alternative import failed: {e2}")
        sys.exit(1)

def main():
    db = get_db_session()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if user:
            print("User 'admin' already exists.")
            return

        print("Creating default admin user...")
        hashed_pw = get_password_hash("admin123")
        new_user = AdminUser(username="admin", password_hash=hashed_pw)
        db.add(new_user)
        db.commit()
        print("User 'admin' created successfully.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
