"""Tests for session_store — process-local ObjectSet memory."""
import pytest
from app.services.agent.runtime import session_store


def test_set_and_get_last_objectset():
    """Test basic set/get for last ObjectSet."""
    session_id = 123
    objectset = {
        "object_type": "产品",
        "obj_slug": "product",
        "filters": [{"field": "价格", "operator": ">=", "value": 100}],
        "selected": ["name", "price"],
        "limit": 10,
        "last_rids": [1, 2, 3],
    }
    session_store.set_last_objectset(session_id, objectset)
    retrieved = session_store.get_last_objectset(session_id)
    assert retrieved == objectset


def test_get_nonexistent_session_returns_none():
    """Test get for nonexistent session returns None."""
    result = session_store.get_last_objectset(999999)
    assert result is None


def test_clear_session():
    """Test clear_session removes entry."""
    session_id = 456
    session_store.set_last_objectset(session_id, {"foo": "bar"})
    session_store.clear_session(session_id)
    assert session_store.get_last_objectset(session_id) is None


def test_overwrite_last_objectset():
    """Test that set_last_objectset overwrites previous entry."""
    session_id = 789
    session_store.set_last_objectset(session_id, {"first": True})
    session_store.set_last_objectset(session_id, {"second": True})
    retrieved = session_store.get_last_objectset(session_id)
    assert retrieved == {"second": True}
