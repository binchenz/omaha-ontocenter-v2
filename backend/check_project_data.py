#!/usr/bin/env python3
"""Check project data in database"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.project.project import Project

# Database setup
DATABASE_URL = "sqlite:///./omaha.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_projects():
    db = SessionLocal()
    try:
        projects = db.query(Project).all()
        
        print("=== Project Data ===")
        for project in projects:
            print(f"\nProject ID: {project.id}")
            print(f"Name: {project.name}")
            print(f"Owner ID: {project.owner_id}")
            print(f"Tenant ID: {project.tenant_id}")
            print(f"Omaha Config Length: {len(project.omaha_config) if project.omaha_config else 0}")
            if project.omaha_config:
                preview = project.omaha_config[:500] + "..." if len(project.omaha_config) > 500 else project.omaha_config
                print(f"Omaha Config Preview:\n{preview}")
                
    finally:
        db.close()


if __name__ == "__main__":
    check_projects()
