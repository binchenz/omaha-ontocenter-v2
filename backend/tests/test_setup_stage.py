import pytest
from app.models.project.project import Project

def test_project_has_setup_stage_default():
    p = Project(name="test", owner_id=1)
    assert p.setup_stage == "idle"

def test_project_setup_stage_values():
    valid = ["idle", "connecting", "cleaning", "modeling", "ready"]
    for stage in valid:
        p = Project(name="test", owner_id=1, setup_stage=stage)
        assert p.setup_stage == stage
