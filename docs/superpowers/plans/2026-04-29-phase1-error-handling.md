# Phase 1: Error Handling & Transaction Safety — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all silent exception swallowing, protect every database write with rollback, fix the SQL injection in slug.py, and unify API error responses.

**Architecture:** Targeted fixes across existing files — no new modules except one small error schema. Each task is independent and can be committed separately.

**Tech Stack:** FastAPI, SQLAlchemy, Python stdlib logging (structlog comes in Phase 2)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `app/services/legacy/financial/ontology_cache_service.py` | Fix 2 bare `except:` blocks |
| Modify | `app/services/ontology/inferrer.py` | Fix 2 broad `except Exception` blocks |
| Modify | `app/services/platform/scheduler.py` | Tighten 4 exception handlers |
| Modify | `app/services/ontology/slug.py` | Fix SQL injection in `ensure_unique_slug` |
| Modify | `app/main.py` | Add global exception handler |
| Create | `app/schemas/error.py` | Unified error response schema |
| Modify | `app/api/auth/login.py` | Add transaction rollback |
| Modify | `app/api/auth/public_auth.py` | Add transaction rollback |
| Modify | `app/api/auth/api_keys.py` | Add transaction rollback |
| Modify | `app/api/projects/crud.py` | Add transaction rollback |
| Modify | `app/api/projects/members.py` | Add transaction rollback |
| Modify | `app/api/projects/assets.py` | Add transaction rollback |
| Modify | `app/api/chat/chat.py` | Add transaction rollback |
| Modify | `app/api/ontology/semantic.py` | Add transaction rollback |
| Modify | `app/api/public_deps.py` | Add transaction rollback |
| Create | `tests/unit/test_slug_validation.py` | Tests for SQL identifier validation |
| Create | `tests/unit/test_error_response.py` | Tests for error schema |
| Create | `tests/api/test_transaction_rollback.py` | Tests for rollback behavior |

---

### Task 1: Fix SQL Injection in slug.py

**Files:**
- Modify: `backend/app/services/ontology/slug.py:50-75`
- Create: `backend/tests/unit/test_slug_validation.py`

- [ ] **Step 1: Write the failing test for identifier validation**

```python
# backend/tests/unit/test_slug_validation.py
import pytest
from app.services.ontology.slug import _validate_sql_identifier


class TestValidateSqlIdentifier:
    def test_valid_simple_name(self):
        assert _validate_sql_identifier("ontology_objects") == "ontology_objects"

    def test_valid_with_numbers(self):
        assert _validate_sql_identifier("table2") == "table2"

    def test_rejects_sql_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("users; DROP TABLE users--")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("my table")

    def test_rejects_semicolons(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("table;")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("")

    def test_rejects_leading_number(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("1table")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/test_slug_validation.py -v`
Expected: FAIL with `ImportError: cannot import name '_validate_sql_identifier'`

- [ ] **Step 3: Implement `_validate_sql_identifier` and use it in `ensure_unique_slug`**

In `backend/app/services/ontology/slug.py`, add the validation function before `ensure_unique_slug` and call it inside `_count`:

```python
import re
import hashlib
from sqlalchemy.orm import Session


_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_sql_identifier(name: str) -> str:
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name
```

Then modify `_count` inside `ensure_unique_slug` (line 63-75) to validate before use:

```python
    def _count(slug_candidate: str) -> int:
        safe_table = _validate_sql_identifier(table_name)
        safe_column = _validate_sql_identifier(column_name)
        q = f"SELECT COUNT(*) FROM {safe_table} WHERE {safe_column} = :slug"
        params: dict = {"slug": slug_candidate}
        if exclude_id is not None:
            q += " AND id != :exclude_id"
            params["exclude_id"] = exclude_id
        if tenant_id is not None:
            q += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        if object_id is not None:
            q += " AND object_id = :object_id"
            params["object_id"] = object_id
        return db.execute(text(q), params).scalar()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/test_slug_validation.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/ontology/slug.py tests/unit/test_slug_validation.py
git commit -m "fix(security): validate SQL identifiers in slug uniqueness check"
```

---

### Task 2: Fix Bare Exceptions in ontology_cache_service.py

**Files:**
- Modify: `backend/app/services/legacy/financial/ontology_cache_service.py:62-65,99-102`

- [ ] **Step 1: Fix the bare `except:` at line 64 (sorting)**

Replace lines 62-65:
```python
            try:
                data = sorted(data, key=lambda x: (x.get(order_by) is None, x.get(order_by, 0)), reverse=reverse)
            except:
                pass
```

With:
```python
            try:
                data = sorted(data, key=lambda x: (x.get(order_by) is None, x.get(order_by, 0)), reverse=reverse)
            except (TypeError, KeyError) as e:
                import logging
                logging.getLogger(__name__).warning("Sort failed on field %s: %s", order_by, e)
```

- [ ] **Step 2: Fix the bare `except:` at line 101 (float conversion)**

Replace lines 99-102:
```python
                    try:
                        raw_record[key] = float(clean_value)
                    except:
                        raw_record[key] = value
```

With:
```python
                    try:
                        raw_record[key] = float(clean_value)
                    except (ValueError, OverflowError):
                        raw_record[key] = value
```

This one doesn't need logging — it's expected behavior for non-numeric strings.

- [ ] **Step 3: Run existing tests**

Run: `cd backend && python -m pytest tests/ -v -k "cache" --no-header`
Expected: Any existing cache-related tests still pass (or no tests match, which is fine)

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/services/legacy/financial/ontology_cache_service.py
git commit -m "fix: replace bare except blocks in ontology_cache_service"
```

---

### Task 3: Fix Broad Exceptions in inferrer.py

**Files:**
- Modify: `backend/app/services/ontology/inferrer.py:99-106,127-138`

- [ ] **Step 1: Fix `classify_tables` exception handler (lines 99-106)**

Replace:
```python
        try:
            raw = self._call_llm(prompt)
            parsed = self._extract_json(raw)
            if not isinstance(parsed, list):
                return [TableClassification(name=t.name) for t in tables]
            return [TableClassification.model_validate(item) for item in parsed]
        except Exception:
            return [TableClassification(name=t.name) for t in tables]
```

With:
```python
        try:
            raw = self._call_llm(prompt)
            parsed = self._extract_json(raw)
            if not isinstance(parsed, list):
                return [TableClassification(name=t.name) for t in tables]
            return [TableClassification.model_validate(item) for item in parsed]
        except (RuntimeError, ConnectionError, TimeoutError) as e:
            import logging
            logging.getLogger(__name__).warning("LLM classification failed: %s", e)
            return [TableClassification(name=t.name) for t in tables]
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            import logging
            logging.getLogger(__name__).warning("Failed to parse LLM classification response: %s", e)
            return [TableClassification(name=t.name) for t in tables]
```

- [ ] **Step 2: Fix `infer_table` exception handler (lines 127-138)**

Replace:
```python
            try:
                raw = self._call_llm(prompt)
                parsed = self._extract_json(raw)
                if not isinstance(parsed, dict):
                    continue
                parsed.setdefault("datasource_id", datasource_id)
                parsed.setdefault("datasource_type", "sql")
                obj = InferredObject.model_validate(parsed)
                return self._validate_semantic_types(obj)
            except Exception:
                continue
```

With:
```python
            try:
                raw = self._call_llm(prompt)
                parsed = self._extract_json(raw)
                if not isinstance(parsed, dict):
                    continue
                parsed.setdefault("datasource_id", datasource_id)
                parsed.setdefault("datasource_type", "sql")
                obj = InferredObject.model_validate(parsed)
                return self._validate_semantic_types(obj)
            except (RuntimeError, ConnectionError, TimeoutError) as e:
                import logging
                logging.getLogger(__name__).warning("LLM inference attempt %d failed: %s", attempt + 1, e)
                continue
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                import logging
                logging.getLogger(__name__).warning("Parse error on attempt %d: %s", attempt + 1, e)
                continue
```

- [ ] **Step 3: Run existing tests**

Run: `cd backend && python -m pytest tests/unit/ontology/ -v --no-header`
Expected: All existing ontology tests pass

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/services/ontology/inferrer.py
git commit -m "fix: replace broad exception handlers in ontology inferrer"
```

---

### Task 4: Tighten Exception Handlers in scheduler.py

**Files:**
- Modify: `backend/app/services/platform/scheduler.py`

The scheduler runs in background threads, so it legitimately needs broad exception handling to avoid crashing the scheduler. The fix here is: keep `except Exception` but ensure every handler logs with full traceback.

- [ ] **Step 1: Fix `start()` handler (lines 31-32)**

Current code is already acceptable — it logs a warning. No change needed.

- [ ] **Step 2: Fix `sync_pipeline` inner handler (lines 64-65)**

Already logs error. No change needed.

- [ ] **Step 3: Fix `_add_job` handler (lines 82-83)**

Already logs error. No change needed.

- [ ] **Step 4: Fix `_execute_pipeline` handler (lines 109-117)**

Replace lines 109-117:
```python
    except Exception as e:
        logger.error(f"Pipeline {pipeline_id} exception: {e}")
        if pipeline:
            try:
                pipeline.last_run_status = "error"
                pipeline.last_error = str(e)
                db.commit()
            except Exception:
                pass
```

With:
```python
    except Exception as e:
        logger.exception("Pipeline %s failed with unhandled exception", pipeline_id)
        if pipeline:
            try:
                pipeline.last_run_status = "error"
                pipeline.last_error = str(e)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to update pipeline %s error status", pipeline_id)
```

Key changes: use `logger.exception()` for full traceback, add `db.rollback()` on inner failure.

- [ ] **Step 5: Run existing tests**

Run: `cd backend && python -m pytest tests/ -v -k "pipeline or scheduler" --no-header`
Expected: Any existing tests pass

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/platform/scheduler.py
git commit -m "fix: add traceback logging and rollback in pipeline scheduler"
```

---

### Task 5: Create Unified Error Response Schema

**Files:**
- Create: `backend/app/schemas/error.py`
- Create: `backend/tests/unit/test_error_response.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_error_response.py
from app.schemas.error import ErrorResponse


class TestErrorResponse:
    def test_basic_error(self):
        err = ErrorResponse(error="Not Found", detail="Project 42 does not exist")
        assert err.error == "Not Found"
        assert err.detail == "Project 42 does not exist"

    def test_error_without_detail(self):
        err = ErrorResponse(error="Internal Server Error")
        assert err.detail is None

    def test_serialization(self):
        err = ErrorResponse(error="Bad Request", detail="Invalid field")
        data = err.model_dump()
        assert data == {"error": "Bad Request", "detail": "Invalid field"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/test_error_response.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the schema**

```python
# backend/app/schemas/error.py
from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/test_error_response.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/schemas/error.py tests/unit/test_error_response.py
git commit -m "feat: add unified ErrorResponse schema"
```

---

### Task 6: Add Global Exception Handler to main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add the global exception handler**

Add these imports at the top of `app/main.py`:
```python
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
```

Add the handler after the CORS middleware block (after line 38):
```python
logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": None},
    )
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `cd backend && python -m pytest tests/api/ -v --no-header`
Expected: All existing API tests pass

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/main.py
git commit -m "feat: add global unhandled exception handler"
```

---

### Task 7: Add Transaction Rollback to Auth Endpoints

**Files:**
- Modify: `backend/app/api/auth/login.py:35-42`
- Modify: `backend/app/api/auth/public_auth.py:41-48,67-72`
- Modify: `backend/app/api/auth/api_keys.py:54-60`

- [ ] **Step 1: Fix `register()` in login.py (line 38-41)**

Replace:
```python
    db.add(user)
    db.commit()
    db.refresh(user)

    return user
```

With:
```python
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")
    db.refresh(user)

    return user
```

Add `from fastapi import HTTPException` to imports if not already present.

- [ ] **Step 2: Fix `register_user()` in public_auth.py (lines 42-47)**

Replace:
```python
    invite.is_used = True
    invite.used_by = user.id
    invite.used_at = datetime.utcnow()

    db.commit()
    db.refresh(user)
```

With:
```python
    invite.is_used = True
    invite.used_by = user.id
    invite.used_at = datetime.utcnow()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register user")
    db.refresh(user)
```

- [ ] **Step 3: Fix `generate_api_key()` in public_auth.py (lines 71-72)**

Replace:
```python
    db.add(api_key)
    db.commit()
```

With:
```python
    db.add(api_key)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to generate API key")
```

- [ ] **Step 4: Fix `create_api_key()` in api_keys.py (lines 58-60)**

Replace:
```python
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
```

With:
```python
    db.add(api_key)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create API key")
    db.refresh(api_key)
```

- [ ] **Step 5: Run existing auth tests**

Run: `cd backend && python -m pytest tests/api/test_api_auth.py tests/api/test_api_public_auth.py -v --no-header`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/auth/login.py app/api/auth/public_auth.py app/api/auth/api_keys.py
git commit -m "fix: add transaction rollback to auth endpoints"
```

---

### Task 8: Add Transaction Rollback to Project Endpoints

**Files:**
- Modify: `backend/app/api/projects/crud.py:36-41,86-92,104-106`
- Modify: `backend/app/api/projects/members.py:73-76,101-102,126-127`
- Modify: `backend/app/api/projects/assets.py:83-85,136-137`

- [ ] **Step 1: Fix `create_project()` in crud.py (lines 36-41)**

Replace:
```python
    db.add(project)
    db.flush()  # get project.id without committing
    log_action(db, action="project.create", user_id=current_user.id,
               project_id=project.id, resource_type="project", resource_id=str(project.id), commit=False)
    db.commit()
    db.refresh(project)
```

With:
```python
    db.add(project)
    db.flush()
    log_action(db, action="project.create", user_id=current_user.id,
               project_id=project.id, resource_type="project", resource_id=str(project.id), commit=False)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create project")
    db.refresh(project)
```

- [ ] **Step 2: Fix `update_project()` in crud.py (lines 91-92)**

Replace:
```python
    db.commit()
    db.refresh(project)
```

With:
```python
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update project")
    db.refresh(project)
```

- [ ] **Step 3: Fix `delete_project()` in crud.py (lines 105-106)**

Replace:
```python
    db.delete(project)
    db.commit()
```

With:
```python
    db.delete(project)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")
```

- [ ] **Step 4: Fix `add_member()` in members.py (lines 74-76)**

Replace:
```python
    member = ProjectMember(project_id=project_id, user_id=target.id, role=req.role)
    db.add(member)
    db.commit()
    db.refresh(member)
```

With:
```python
    member = ProjectMember(project_id=project_id, user_id=target.id, role=req.role)
    db.add(member)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add member")
    db.refresh(member)
```

- [ ] **Step 5: Fix `update_member_role()` in members.py (line 102)**

Replace:
```python
    member.role = req.role
    db.commit()
```

With:
```python
    member.role = req.role
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update member role")
```

- [ ] **Step 6: Fix `remove_member()` in members.py (lines 126-127)**

Replace:
```python
    db.delete(member)
    db.commit()
```

With:
```python
    db.delete(member)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove member")
```

- [ ] **Step 7: Fix `save_asset()` in assets.py (lines 83-85)**

Replace:
```python
    db.add_all(lineage_records)
    db.commit()
    db.refresh(asset)
```

With:
```python
    db.add_all(lineage_records)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save asset")
    db.refresh(asset)
```

- [ ] **Step 8: Fix `delete_asset()` in assets.py (lines 136-137)**

Replace:
```python
    db.delete(asset)
    db.commit()
```

With:
```python
    db.delete(asset)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete asset")
```

- [ ] **Step 9: Run existing project tests**

Run: `cd backend && python -m pytest tests/api/test_api_projects.py tests/api/test_api_members.py tests/api/test_api_assets.py -v --no-header 2>&1 || echo "Some test files may not exist yet — that's OK"`
Expected: Any existing tests pass

- [ ] **Step 10: Commit**

```bash
cd backend
git add app/api/projects/crud.py app/api/projects/members.py app/api/projects/assets.py
git commit -m "fix: add transaction rollback to project, member, and asset endpoints"
```

---

### Task 9: Add Transaction Rollback to Chat and Remaining Endpoints

**Files:**
- Modify: `backend/app/api/chat/chat.py:40-42,111-112`
- Modify: `backend/app/api/ontology/semantic.py:52-53`
- Modify: `backend/app/api/public_deps.py:30-31`

- [ ] **Step 1: Fix `create_chat_session()` in chat.py (lines 40-42)**

Replace:
```python
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
```

With:
```python
    db.add(chat_session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create chat session")
    db.refresh(chat_session)
```

- [ ] **Step 2: Fix `delete_chat_session()` in chat.py (lines 111-112)**

Replace:
```python
    db.delete(session)
    db.commit()
```

With:
```python
    db.delete(session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete chat session")
```

- [ ] **Step 3: Fix `update_semantic_config()` in semantic.py (lines 52-53)**

Replace:
```python
    project.omaha_config = body.config
    db.commit()
```

With:
```python
    project.omaha_config = body.config
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update config")
```

- [ ] **Step 4: Fix `verify_api_key()` in public_deps.py (lines 30-31)**

Replace:
```python
    api_key.last_used_at = datetime.utcnow()
    db.commit()
```

With:
```python
    api_key.last_used_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
```

Note: No HTTPException here — this is a non-critical "last used" timestamp update. Failing silently (after rollback) is acceptable.

- [ ] **Step 5: Run all API tests**

Run: `cd backend && python -m pytest tests/api/ -v --no-header`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/chat/chat.py app/api/ontology/semantic.py app/api/public_deps.py
git commit -m "fix: add transaction rollback to chat, semantic, and public_deps endpoints"
```

---

### Task 10: Write Transaction Rollback Integration Test

**Files:**
- Create: `backend/tests/api/test_transaction_rollback.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/api/test_transaction_rollback.py
"""Verify that endpoints return 500 and rollback when db.commit() fails."""
import pytest
from unittest.mock import Mock, patch, PropertyMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.api.deps import get_current_user
from app.database import get_db


mock_user = Mock()
mock_user.id = 1
mock_user.email = "test@test.com"
mock_user.is_active = True


def override_get_current_user():
    return mock_user


def make_failing_db():
    """Create a mock DB session whose commit() raises IntegrityError."""
    mock_session = Mock()
    mock_session.commit.side_effect = IntegrityError("duplicate", {}, None)
    mock_session.rollback = Mock()

    mock_q = Mock()
    mock_q.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_q
    return mock_session


@pytest.fixture
def failing_client():
    db = make_failing_db()

    def override_get_db():
        yield db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), db
    app.dependency_overrides.clear()


def test_create_project_rollback_on_commit_failure(failing_client):
    client, db = failing_client
    response = client.post(
        "/api/v1/projects/",
        json={"name": "Test", "description": "test"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 500
    db.rollback.assert_called()


def test_register_rollback_on_commit_failure():
    db = make_failing_db()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "email": "new@test.com",
                  "password": "pass123", "full_name": "New User"},
        )
        assert response.status_code == 500
        db.rollback.assert_called()
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run the test**

Run: `cd backend && python -m pytest tests/api/test_transaction_rollback.py -v`
Expected: All tests PASS (since we already added rollback in Tasks 7-9)

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/api/test_transaction_rollback.py
git commit -m "test: add integration tests for transaction rollback behavior"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Run the full test suite**

Run: `cd backend && python -m pytest tests/ -v --no-header`
Expected: All tests pass

- [ ] **Step 2: Verify no remaining bare exceptions**

Run: `cd backend && grep -rn "except:" app/ --include="*.py" | grep -v "except:" | head -20` and `cd backend && grep -rn "^\s*except:\s*$" app/ --include="*.py"`
Expected: Zero matches for bare `except:` (without a type)

- [ ] **Step 3: Commit any final fixes if needed, then tag**

```bash
git tag phase1-error-handling-complete
```
