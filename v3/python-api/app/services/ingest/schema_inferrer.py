import pandas as pd


SEMANTIC_HINTS = {
    "金额": "currency", "价格": "currency", "收入": "currency", "成本": "currency",
    "收入": "currency", "利润": "currency", "amount": "currency", "price": "currency",
    "revenue": "currency", "cost": "currency", "毛利率": "percentage", "rate": "percentage",
    "日期": "date", "时间": "datetime", "date": "date", "time": "datetime",
    "created_at": "datetime", "updated_at": "datetime",
    "名称": "text", "描述": "text", "name": "text", "description": "text",
    "状态": "enum", "类型": "enum", "status": "enum", "type": "enum",
    "编号": "id", "编码": "id", "id": "id", "code": "id",
}


def infer_semantic_type(col_name: str, dtype: str, sample_values: list) -> str:
    """Infer semantic type from column name, pandas dtype, and sample values."""
    col_lower = col_name.lower()
    for hint, sem_type in SEMANTIC_HINTS.items():
        if hint in col_lower:
            return sem_type

    dtype_str = str(dtype).lower()
    if "int" in dtype_str or "float" in dtype_str:
        return "number"
    if "datetime" in dtype_str:
        return "date"
    if "bool" in dtype_str:
        return "enum"

    if sample_values:
        unique_ratio = len(set(str(v) for v in sample_values[:500])) / min(len(sample_values), 500)
        if unique_ratio < 0.1:
            return "enum"

    return "text"


def infer_columns(df: pd.DataFrame) -> list[dict]:
    """Infer column metadata from a DataFrame."""
    columns = []
    for col in df.columns:
        sample = df[col].dropna().head(100).tolist()
        columns.append({
            "name": col,
            "dtype": str(df[col].dtype),
            "semantic_type": infer_semantic_type(col, str(df[col].dtype), sample),
            "sample_values": sample[:5],
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
        })
    return columns
