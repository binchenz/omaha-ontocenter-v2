import pytest
from app.services.ontology_draft_store import OntologyDraftStore


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


def test_load_when_missing_returns_none():
    assert OntologyDraftStore.load(1, 2) is None


def test_save_and_load_roundtrip():
    OntologyDraftStore.save(
        project_id=1, session_id=2,
        objects=[{"name": "订单"}],
        relationships=[{"from": "订单", "to": "客户"}],
        warnings=["test warning"],
    )
    loaded = OntologyDraftStore.load(1, 2)
    assert loaded is not None
    assert loaded["objects"] == [{"name": "订单"}]
    assert loaded["relationships"] == [{"from": "订单", "to": "客户"}]
    assert loaded["warnings"] == ["test warning"]


def test_save_overwrites_existing():
    OntologyDraftStore.save(1, 2, [{"name": "old"}], [], [])
    OntologyDraftStore.save(1, 2, [{"name": "new"}], [], [])
    assert OntologyDraftStore.load(1, 2)["objects"] == [{"name": "new"}]


def test_clear_removes_draft():
    OntologyDraftStore.save(1, 2, [{"name": "x"}], [], [])
    OntologyDraftStore.clear(1, 2)
    assert OntologyDraftStore.load(1, 2) is None


def test_clear_when_missing_does_not_raise():
    OntologyDraftStore.clear(99, 99)


def test_isolation_between_sessions():
    OntologyDraftStore.save(1, 2, [{"name": "a"}], [], [])
    OntologyDraftStore.save(1, 3, [{"name": "b"}], [], [])
    assert OntologyDraftStore.load(1, 2)["objects"] == [{"name": "a"}]
    assert OntologyDraftStore.load(1, 3)["objects"] == [{"name": "b"}]
