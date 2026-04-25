"""Pickle-based ontology draft storage scoped by (project_id, session_id)."""
import pickle
from pathlib import Path


_BASE = Path("data/uploads")


def _draft_dir(project_id: int, session_id: int) -> Path:
    return (_BASE / str(project_id) / str(session_id) / "_drafts").resolve()


def _draft_path(project_id: int, session_id: int) -> Path:
    return _draft_dir(project_id, session_id) / "draft.pkl"


class OntologyDraftStore:
    @staticmethod
    def save(
        project_id: int,
        session_id: int,
        objects: list,
        relationships: list,
        warnings: list,
    ) -> None:
        d = _draft_dir(project_id, session_id)
        d.mkdir(parents=True, exist_ok=True)
        payload = {
            "objects": objects,
            "relationships": relationships,
            "warnings": warnings,
        }
        with _draft_path(project_id, session_id).open("wb") as f:
            pickle.dump(payload, f)

    @staticmethod
    def load(project_id: int, session_id: int) -> dict | None:
        p = _draft_path(project_id, session_id)
        if not p.exists():
            return None
        with p.open("rb") as f:
            return pickle.load(f)

    @staticmethod
    def clear(project_id: int, session_id: int) -> None:
        p = _draft_path(project_id, session_id)
        if p.exists():
            p.unlink()
