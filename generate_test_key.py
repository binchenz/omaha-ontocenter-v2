#!/usr/bin/env python
"""Generate API key for MCP testing."""
import os
import sys
import secrets
import hashlib
from datetime import datetime, timedelta

# Set required env vars
os.environ.setdefault('DATABASE_URL', 'sqlite:///./backend/omaha.db')
os.environ.setdefault('SECRET_KEY', 'your-secret-key-here-change-in-production-min-32-chars')
os.environ.setdefault('DATAHUB_GMS_URL', 'http://localhost:8080')

sys.path.insert(0, 'backend')

from app.database import SessionLocal
from app.models.api_key import ProjectApiKey

def generate_key():
    """Generate a new API key."""
    prefix = secrets.token_hex(4)
    secret = secrets.token_hex(16)
    full_key = f"omaha_1_{prefix}_{secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_hash, prefix

def main():
    project_id = 7

    db = SessionLocal()
    try:
        # Generate key
        full_key, key_hash, prefix = generate_key()

        # Get first user as creator
        from app.models.user import User
        user = db.query(User).first()
        if not user:
            print("Error: No users found. Create a user first.")
            return

        # Create API key record
        api_key = ProjectApiKey(
            project_id=project_id,
            key_hash=key_hash,
            key_prefix=prefix,
            name="MCP Test Key",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=365),
            created_by=user.id
        )

        db.add(api_key)
        db.commit()

        print("=" * 60)
        print("API Key Generated Successfully!")
        print("=" * 60)
        print(f"\nProject ID: {project_id}")
        print(f"Key ID: {api_key.id}")
        print(f"\n⚠️  SAVE THIS KEY - IT WON'T BE SHOWN AGAIN:")
        print(f"\n{full_key}\n")
        print("=" * 60)
        print("\nAdd this to your MCP config:")
        print(f'  "OMAHA_API_KEY": "{full_key}"')
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
