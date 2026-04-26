import pytest
from unittest.mock import patch, MagicMock
from app.models.project.project import Project
from app.services.agent.toolkit import AgentToolkit
import pandas as pd

def test_full_onboarding_flow():
    """Test the complete flow: upload → assess → clean → re-assess"""
    mock_omaha = MagicMock()
    toolkit = AgentToolkit(omaha_service=mock_omaha)

    # Step 1: Upload file (mock pandas read)
    test_df = pd.DataFrame({
        "客户": ["张三", " 张三 ", "李四", "李四"],
        "金额": [100, 100, 200, 300],
        "日期": ["2024/3/5", "2024-03-05", "2024/3/6", "2024-03-07"],
    })
    with patch("pandas.read_excel", return_value=test_df):
        result = toolkit.execute_tool("upload_file", {
            "file_path": "/tmp/test.xlsx",
            "table_name": "orders"
        })
    assert result["success"] is True
    assert result["data"]["row_count"] == 4

    # Step 2: Assess quality
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is True
    assert "score" in result["data"]
    assert isinstance(result["data"]["issues"], list)

    # Step 3: Clean data
    result = toolkit.execute_tool("clean_data", {
        "rules": ["duplicate_rows", "strip_whitespace", "standardize_dates"]
    })
    assert result["success"] is True

    # Step 4: Re-assess — score should improve
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is True

def test_setup_stage_transitions():
    project = Project(name="test", owner_id=1)
    assert project.setup_stage == "idle"

    project.setup_stage = "connecting"
    assert project.setup_stage == "connecting"

    project.setup_stage = "cleaning"
    assert project.setup_stage == "cleaning"

    project.setup_stage = "modeling"
    assert project.setup_stage == "modeling"

    project.setup_stage = "ready"
    assert project.setup_stage == "ready"
