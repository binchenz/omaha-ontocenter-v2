"""
Initialize SQLite database with tables.
"""
from app.database import Base, engine
from app.models import User, Project, QueryHistory

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Database initialized successfully!")
print("Database file: omaha.db")
