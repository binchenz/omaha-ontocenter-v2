#!/usr/bin/env python3
"""Generate invite codes."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import secrets
import argparse
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import InviteCode

def generate_codes(db: Session, count: int, expires_days: int):
    """Generate invite codes."""
    expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days > 0 else None

    for _ in range(count):
        code = secrets.token_urlsafe(16)
        invite = InviteCode(code=code, expires_at=expires_at)
        db.add(invite)
        print(code)

    db.commit()
    print(f"\nGenerated {count} invite codes")

def main():
    parser = argparse.ArgumentParser(description='Generate invite codes')
    parser.add_argument('--count', type=int, default=10, help='Number of codes to generate')
    parser.add_argument('--expires', type=int, default=30, help='Expiration in days (0 for no expiration)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        generate_codes(db, args.count, args.expires)
    finally:
        db.close()

if __name__ == '__main__':
    main()
