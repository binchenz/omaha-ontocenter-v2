import pytest
import pandas as pd
from app.services.data.cleaner import DataCleaner, QualityReport, QualityIssue

def test_assess_detects_duplicate_rows():
    df = pd.DataFrame({"name": ["张三", "张三", "李四"], "amount": [100, 100, 200]})
    report = DataCleaner.assess({"customers": df})
    issues = [i for i in report.issues if i.issue_type == "duplicate_rows"]
    assert len(issues) == 1
    assert issues[0].table == "customers"
    assert issues[0].count == 1

def test_assess_detects_missing_values():
    df = pd.DataFrame({"name": ["张三", None, "李四"], "amount": [100, 200, None]})
    report = DataCleaner.assess({"orders": df})
    issues = [i for i in report.issues if i.issue_type == "missing_values"]
    assert len(issues) == 2  # one per column with nulls

def test_assess_detects_inconsistent_dates():
    df = pd.DataFrame({"date": ["2024/3/5", "3月5号", "2024-03-06", "45356"]})
    report = DataCleaner.assess({"orders": df})
    issues = [i for i in report.issues if i.issue_type == "inconsistent_format"]
    assert len(issues) >= 1

def test_assess_quality_score():
    df = pd.DataFrame({"name": ["张三", "李四"], "amount": [100, 200]})
    report = DataCleaner.assess({"clean_table": df})
    assert report.score >= 90

def test_clean_removes_duplicate_rows():
    df = pd.DataFrame({"name": ["张三", "张三", "李四"], "amount": [100, 100, 200]})
    result = DataCleaner.clean({"t": df}, auto_rules=["duplicate_rows"])
    assert len(result["t"]) == 2

def test_clean_standardizes_dates():
    df = pd.DataFrame({"date": ["2024/3/5", "2024-03-06"]})
    result = DataCleaner.clean({"t": df}, auto_rules=["standardize_dates"])
    assert result["t"]["date"].iloc[0] == "2024-03-05"
    assert result["t"]["date"].iloc[1] == "2024-03-06"

def test_clean_strips_whitespace():
    df = pd.DataFrame({"name": [" 张三 ", "李四  "]})
    result = DataCleaner.clean({"t": df}, auto_rules=["strip_whitespace"])
    assert result["t"]["name"].iloc[0] == "张三"
    assert result["t"]["name"].iloc[1] == "李四"

def test_quality_report_to_dict():
    report = QualityReport(
        score=67,
        issues=[QualityIssue(table="t", column="name", issue_type="duplicate_rows", count=5, examples=["张三"], suggestion="去重")]
    )
    d = report.to_dict()
    assert d["score"] == 67
    assert len(d["issues"]) == 1
