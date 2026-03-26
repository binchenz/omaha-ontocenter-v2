"""
User model tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.database import Base


# In-memory SQLite test database
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_with_inviter(db_session):
    """Test user with inviter relationship."""
    inviter = User(
        email="inviter@example.com",
        username="inviter",
        hashed_password="hashed"
    )
    db_session.add(inviter)
    db_session.commit()

    invited = User(
        email="invited@example.com",
        username="invited",
        hashed_password="hashed",
        invited_by=inviter.id
    )
    db_session.add(invited)
    db_session.commit()

    assert invited.invited_by == inviter.id
