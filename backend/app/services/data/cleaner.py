from dataclasses import dataclass, field, asdict
from typing import Literal, Optional, List, Dict, Union
import pandas as pd
import re


CleanRule = Literal["duplicate_rows", "strip_whitespace", "standardize_dates"]

_DATE_PATTERNS = [
    re.compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"),
    re.compile(r"\d{1,2}月\d{1,2}[号日]"),
    re.compile(r"^\d{5}$"),  # Excel serial date
]


@dataclass
class QualityIssue:
    table: str
    column: Optional[str]
    issue_type: str  # duplicate_rows, missing_values, inconsistent_format
    count: int
    examples: list[str]
    suggestion: str
    auto_fixable: bool = True

@dataclass
class QualityReport:
    score: int
    issues: list[QualityIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"score": self.score, "issues": [asdict(i) for i in self.issues]}


def _is_string_column(series: pd.Series) -> bool:
    dtype_name = series.dtype.name.lower()
    return series.dtype == object or dtype_name in ("str", "string", "object")


class DataCleaner:
    @staticmethod
    def assess(tables: dict[str, pd.DataFrame]) -> QualityReport:
        issues: list[QualityIssue] = []
        total_cells = 0
        problem_cells = 0

        for table_name, df in tables.items():
            total_cells += df.size

            dup_count = df.duplicated().sum()
            if dup_count > 0:
                problem_cells += dup_count * len(df.columns)
                issues.append(QualityIssue(
                    table=table_name, column=None,
                    issue_type="duplicate_rows", count=int(dup_count),
                    examples=[], suggestion="删除重复行",
                ))

            for col in df.columns:
                series = df[col]
                null_count = int(series.isna().sum())
                if null_count > 0:
                    problem_cells += null_count
                    issues.append(QualityIssue(
                        table=table_name, column=col,
                        issue_type="missing_values", count=null_count,
                        examples=[], suggestion=f"填充或删除 {null_count} 条空值",
                        auto_fixable=False,
                    ))

                if _is_string_column(series):
                    vals = series.dropna().astype(str)
                    matched: set[int] = set()
                    for v in vals:
                        for i, pat in enumerate(_DATE_PATTERNS):
                            if pat.search(v):
                                matched.add(i)
                        if len(matched) == len(_DATE_PATTERNS):
                            break
                    if len(matched) > 1:
                        problem_cells += len(vals)
                        issues.append(QualityIssue(
                            table=table_name, column=col,
                            issue_type="inconsistent_format", count=len(vals),
                            examples=vals.head(3).tolist(),
                            suggestion="统一为 YYYY-MM-DD 格式",
                        ))

        score = 100 if total_cells == 0 else max(0, 100 - int(problem_cells / total_cells * 100))
        return QualityReport(score=score, issues=issues)

    @staticmethod
    def clean(tables: dict[str, pd.DataFrame], auto_rules: list[CleanRule]) -> dict[str, pd.DataFrame]:
        result = {}
        for name, df in tables.items():
            df = df.copy()
            if "duplicate_rows" in auto_rules:
                df = df.drop_duplicates()

            needs_object_cols = (
                "strip_whitespace" in auto_rules or "standardize_dates" in auto_rules
            )
            object_cols = (
                df.select_dtypes(include=["object"]).columns if needs_object_cols else []
            )

            if "strip_whitespace" in auto_rules:
                for col in object_cols:
                    df[col] = df[col].str.strip()
            if "standardize_dates" in auto_rules:
                for col in object_cols:
                    try:
                        parsed = pd.to_datetime(df[col], format="mixed", dayfirst=False)
                        df[col] = parsed.dt.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        try:
                            parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
                            mask = parsed.notna()
                            if mask.any():
                                df.loc[mask, col] = parsed[mask].dt.strftime("%Y-%m-%d")
                        except Exception:
                            pass
            result[name] = df
        return result
