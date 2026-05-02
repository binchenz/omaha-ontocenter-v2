"""SQL identifier and aggregate expression validation to prevent injection."""
import re

IDENT_RE = re.compile(r"^[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*$")
ALLOWED_AGG_FUNCS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "STDDEV", "MEDIAN"}

# Pattern: FUNC(column) or FUNC(column) AS alias or FUNC(*)
AGG_RE = re.compile(
    r"^\s*(?P<fn>[A-Za-z_]+)\s*\(\s*(?P<col>\*|[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*)\s*\)"
    r"(?:\s+AS\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*))?\s*$",
    re.IGNORECASE,
)


def validate_identifier(name: str) -> str:
    """Ensure a column/identifier is safe. Raises ValueError otherwise."""
    if not name or not IDENT_RE.match(name):
        raise ValueError(f"无效的字段名: {name}")
    return name


def escape_sql_value(v: any) -> str:
    """Escape a value for safe SQL string interpolation."""
    return str(v).replace("'", "''")


def validate_measure(expr: str) -> str:
    """Validate an aggregate expression like 'SUM(amount)' or 'COUNT(*) AS count'.

    Whitelists aggregate function names; rejects anything with multiple statements
    or non-identifier column references.
    """
    if not expr or ";" in expr or "--" in expr:
        raise ValueError(f"无效的聚合表达式: {expr}")
    m = AGG_RE.match(expr)
    if not m:
        raise ValueError(f"聚合表达式格式错误: {expr}")
    fn = m.group("fn").upper()
    if fn not in ALLOWED_AGG_FUNCS:
        raise ValueError(f"不支持的聚合函数 {fn}，允许: {', '.join(sorted(ALLOWED_AGG_FUNCS))}")
    col = m.group("col")
    if col != "*":
        validate_identifier(col)
    alias = m.group("alias")
    if alias and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", alias):
        raise ValueError(f"无效的别名: {alias}")
    return expr.strip()
