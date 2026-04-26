#!/usr/bin/env python3
"""Test script to query "牧原最近怎么样？"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.project import Project
from app.models.chat_session import ChatSession
from app.services.chat import ChatService
from app.services.ontology_store import OntologyStore
from app.services.omaha import OmahaService
from app.services.agent_tools import AgentToolkit
from app.services.agent import AgentService

# Database setup
DATABASE_URL = "sqlite:///./omaha.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_chat_query():
    print("=" * 70)
    print("Testing Chat Query: '牧原最近怎么样？'")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Get project 4 (金融股票分析)
        project = db.query(Project).filter(Project.id == 4).first()
        if not project:
            print("Project 4 not found!")
            return
        
        print(f"\nUsing project: {project.name} (ID: {project.id})")
        tenant_id = project.tenant_id or project.owner_id
        print(f"Tenant ID: {tenant_id}")
        
        # Check ontology
        store = OntologyStore(db)
        ontology = store.get_full_ontology(tenant_id)
        print(f"\nOntology has {len(ontology.get('objects', []))} objects available")
        
        # Create chat service
        chat_service = ChatService(project_id=project.id, db=db)
        
        # Create a test chat session
        session = ChatSession(
            project_id=project.id,
            user_id=1,
            title="测试会话 - 牧原"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        print(f"\nCreated test chat session: ID={session.id}")
        
        # Test the query
        print("\n" + "=" * 70)
        print("Sending query: '牧原最近怎么样？'")
        print("=" * 70)
        
        try:
            result = chat_service.send_message(
                session_id=session.id,
                user_message="牧原最近怎么样？",
                config_yaml=project.omaha_config,
                llm_provider="deepseek"
            )
            
            print("\n" + "=" * 70)
            print("Query Result:")
            print("=" * 70)
            print(f"Response: {result.get('message', 'No response')}")
            
            if result.get('data_table'):
                print(f"\nData Table: {len(result['data_table'])} rows")
                for i, row in enumerate(result['data_table'][:5]):
                    print(f"  Row {i+1}: {row}")
            
            if result.get('sql'):
                print(f"\nSQL: {result['sql']}")
                
        except Exception as e:
            print(f"\nError sending message: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 70)
        print("Also testing direct agent service directly")
        print("=" * 70)
        
        # Test Omaha service directly first
        omaha_service = OmahaService(project.omaha_config or "")
        
        # Test query for 牧原 (002714.SZ)
        print("\nTesting query for 牧原 stock data:")
        try:
            stock_result = omaha_service.query_objects(
                "Stock",
                selected_columns=["Stock.ts_code", "Stock.name", "Stock.industry"],
                filters=[{"field": "ts_code", "operator": "=", "value": "002714.SZ"}],
                limit=1
            )
            print(f"Stock query result: {stock_result}")
            
            # Test daily quote
            daily_result = omaha_service.query_objects(
                "DailyQuote",
                selected_columns=["DailyQuote.trade_date", "DailyQuote.close", "DailyQuote.pct_chg"],
                filters=[{"field": "ts_code", "operator": "=", "value": "002714.SZ"}],
                limit=10
            )
            print(f"\nDaily quote query result (first 5 rows:")
            if daily_result.get("success") and daily_result.get("data"):
                for row in daily_result["data"][:5]:
                    print(f"  {row}")
            
        except Exception as e:
            print(f"Error querying data: {e}")
            import traceback
            traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    test_chat_query()
