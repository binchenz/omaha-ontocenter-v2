"""Tests for PublicApiKey model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.auth.public_api_key import PublicApiKey
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


def test_create_public_api_key(db_session):
    """Test creating a public API key."""
    user = User(
        email="user@example.com",
        username="testuser",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    api_key = PublicApiKey(
        user_id=user.id,
        key_hash="hash123",
        key_prefix="omaha_pub"
    )
    db_session.add(api_key)
    db_session.commit()

    assert api_key.id is not None
    assert api_key.is_active is True
    assert api_key.user_id == user.id
    assert api_key.key_hash == "hash123"
    assert api_key.key_prefix == "omaha_pub"
    assert api_key.created_at is not None
    assert api_key.last_used_at is None


def test_public_api_key_user_relationship(db_session):
    """Test relationship between PublicApiKey and User."""
    user = User(
        email="user@example.com",
        username="testuser",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    api_key = PublicApiKey(
        user_id=user.id,
        key_hash="hash123",
        key_prefix="omaha_pub"
    )
    db_session.add(api_key)
    db_session.commit()

    assert api_key.user == user
    assert api_key in user.public_api_keys
