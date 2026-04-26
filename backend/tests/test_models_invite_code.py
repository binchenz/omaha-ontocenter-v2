"""Tests for InviteCode model."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.auth.invite_code import InviteCode
from app.models.auth.user import User
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


def test_create_invite_code(db_session):
    """Test creating an invite code."""
    user = User(
        email="creator@example.com",
        username="creator",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    code = InviteCode(
        code="TEST123",
        created_by=user.id
    )
    db_session.add(code)
    db_session.commit()

    assert code.id is not None
    assert code.code == "TEST123"
    assert code.is_used is False


def test_invite_code_usage(db_session):
    """Test marking an invite code as used."""
    creator = User(
        email="creator@example.com",
        username="creator",
        hashed_password="hashed"
    )
    db_session.add(creator)
    db_session.commit()

    code = InviteCode(
        code="USED123",
        created_by=creator.id
    )
    db_session.add(code)
    db_session.commit()

    # Mark as used
    user = User(
        email="user@example.com",
        username="user",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    code.is_used = True
    code.used_by = user.id
    code.used_at = datetime.utcnow()
    db_session.commit()

    assert code.is_used is True
    assert code.used_by == user.id
    assert code.used_at is not None
