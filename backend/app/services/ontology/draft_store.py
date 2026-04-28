

"""JSON-based ontology draft storage scoped by (project_id, session_id)."""
import json
from pathlib import Path

# Mirror Phase 3a UploadedTableStore convention (data/uploads under cwd at process start).
# UploadedTableStore is also CWD-relative; switching one without the other would split storage.
_BASE = Path("data/uploads")

def _draft_dir(project_id: int, session_id: int) -> Path:
    return (_BASE / str(project_id) / str(session_id) / "_drafts").resolve()

def _draft_path(project_id: int, session_id: int) -> Path:
    return _draft_dir(project_id, session_id) / "draft.json"

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
        _draft_path(project_id, session_id).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def load(project_id: int, session_id: int) -> dict | None:
        p = _draft_path(project_id, session_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def clear(project_id: int, session_id: int) -> None:
        p = _draft_path(project_id, session_id)
        if p.exists():
            p.unlink()
