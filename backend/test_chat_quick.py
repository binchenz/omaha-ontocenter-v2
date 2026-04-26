#!/usr/bin/env python3
"""Quick test script to check database and chat functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models.project.project import Project
from app.models.auth.user import User
from app.services.ontology.store import OntologyStore
from app.models.ontology.ontology import OntologyObject

# Database setup
DATABASE_URL = "sqlite:///./omaha.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_database():
    print("=" * 60)
    print("Checking Database...")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Check users
        users = db.query(User).all()
        print(f"\nTotal users: {len(users)}")
        for user in users:
            print(f"  - ID: {user.id}, Username: {user.username}, Email: {user.email}")
        
        # Check projects
        projects = db.query(Project).all()
        print(f"\nTotal projects: {len(projects)}")
        for project in projects:
            tenant_id = project.tenant_id or project.owner_id
            print(f"  - ID: {project.id}, Name: {project.name}")
            print(f"    Owner ID: {project.owner_id}, Tenant ID: {project.tenant_id} (using: {tenant_id})")
            
            # Check ontology for this project
            store = OntologyStore(db)
            ontology = store.get_full_ontology(tenant_id)
            print(f"    Ontology objects: {len(ontology.get('objects', []))}")
            for obj in ontology.get('objects', []):
                print(f"      - {obj['name']}: {len(obj.get('properties', []))} properties")
        
        print("\n" + "=" * 60)
        print("Database check complete!")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    check_database()
