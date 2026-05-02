"""
Shared DuckDB → HTTP error mapping.

The OAG query path is invoked from both `/ontology/{id}/query` and the MCP
runtime (`/mcp/runtime/...`). Both callers need the same 4xx behaviour so the
LLM can self-recover instead of retrying a 5xx blindly.
"""
from contextlib import contextmanager

import duckdb
from fastapi import HTTPException


@contextmanager
def map_duckdb_errors():
    """Re-raise DuckDB exceptions as HTTPException with actionable status codes."""
    try:
        yield
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except duckdb.CatalogException as e:
        msg = str(e)
        lowered = msg.lower()
        if "table" in lowered and "does not exist" in lowered:
            raise HTTPException(
                status_code=404,
                detail=f"数据表不存在或尚未导入: {msg}",
            ) from e
        if "column" in lowered or "referenced column" in lowered:
            raise HTTPException(
                status_code=422,
                detail=f"查询字段不存在: {msg}",
            ) from e
        raise HTTPException(
            status_code=404,
            detail=f"目录对象不存在: {msg}",
        ) from e
    except duckdb.BinderException as e:
        raise HTTPException(status_code=422, detail=f"查询绑定错误: {e}") from e
    except (duckdb.ParserException, duckdb.SyntaxException) as e:
        raise HTTPException(status_code=400, detail=f"查询语法错误: {e}") from e
    except duckdb.InvalidInputException as e:
        raise HTTPException(status_code=400, detail=f"查询输入无效: {e}") from e
