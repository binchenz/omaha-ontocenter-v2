# 金融分析系统云端部署实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Omaha OntoCenter 部署到火山引擎云服务器，提供公开 REST API 和 Claude Code Skill

**Architecture:** 单体架构，FastAPI + PostgreSQL + Nginx，邀请码注册系统，定时缓存 Tushare 数据，REST API 对外服务

**Tech Stack:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, Nginx, Tushare Pro API, systemd, cron

---

## Chunk 1: 数据库模型和迁移

### Task 1: 更新 User 模型添加 invited_by 字段

**Files:**
- Modify: `backend/app/models/user.py`

- [ ] **Step 1: 编写测试验证 invited_by 字段**

Add to `backend/tests/test_models_user.py`:

```python
def test_user_with_inviter(db_session):
    """Test user with inviter relationship."""
    inviter = User(
        email="inviter@example.com",
        username="inviter",
        hashed_password="hashed"
    )
    db_session.add(inviter)
    db_session.commit()

    invited = User(
        email="invited@example.com",
        username="invited",
        hashed_password="hashed",
        invited_by=inviter.id
    )
    db_session.add(invited)
    db_session.commit()

    assert invited.invited_by == inviter.id
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_models_user.py::test_user_with_inviter -v`
Expected: FAIL with "User has no attribute 'invited_by'"

- [ ] **Step 3: 更新 User 模型**

Edit `backend/app/models/user.py` to add:

```python
invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_models_user.py::test_user_with_inviter -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/user.py backend/tests/test_models_user.py
git commit -m "feat: add invited_by field to User model"
```

---

### Task 2: 创建邀请码模型

**Files:**
- Create: `backend/app/models/invite_code.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 编写邀请码模型测试**

创建测试文件 `backend/tests/test_models_invite_code.py`:

```python
"""Tests for InviteCode model."""
import pytest
from datetime import datetime, timedelta
from app.models.invite_code import InviteCode
from app.models.user import User


def test_create_invite_code(db_session):
    """Test creating an invite code."""
    user = User(
        email="creator@example.com",
        username="creator",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    code = InviteCode(
        code="TEST123",
        created_by=user.id
    )
    db_session.add(code)
    db_session.commit()

    assert code.id is not None
    assert code.code == "TEST123"
    assert code.is_used is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_models_invite_code.py -v`
Expected: FAIL with "No module named 'app.models.invite_code'"

- [ ] **Step 3: 创建邀请码模型**

Create `backend/app/models/invite_code.py`:

```python
"""InviteCode model for user registration."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", foreign_keys=[created_by], backref="created_invite_codes")
    user = relationship("User", foreign_keys=[used_by], backref="used_invite_code")
```

- [ ] **Step 4: 更新 models __init__.py**

Edit `backend/app/models/__init__.py` to add:

```python
from app.models.invite_code import InviteCode
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_models_invite_code.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/invite_code.py backend/app/models/__init__.py backend/tests/test_models_invite_code.py
git commit -m "feat: add InviteCode model for user registration"
```

---

### Task 2: 创建公开 API Key 模型

**Files:**
- Create: `backend/app/models/public_api_key.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 编写公开 API Key 模型测试**

Create `backend/tests/test_models_public_api_key.py`:

```python
"""Tests for PublicApiKey model."""
import pytest
from app.models.public_api_key import PublicApiKey
from app.models.user import User


def test_create_public_api_key(db_session):
    """Test creating a public API key."""
    user = User(
        email="user@example.com",
        username="testuser",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    api_key = PublicApiKey(
        user_id=user.id,
        key_hash="hash123",
        key_prefix="omaha_pub"
    )
    db_session.add(api_key)
    db_session.commit()

    assert api_key.id is not None
    assert api_key.is_active is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_models_public_api_key.py -v`
Expected: FAIL

- [ ] **Step 3: 创建公开 API Key 模型**

Create `backend/app/models/public_api_key.py`:

```python
"""PublicApiKey model for public REST API authentication."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class PublicApiKey(Base):
    __tablename__ = "public_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(16), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="public_api_keys")
```

- [ ] **Step 4: 更新 models __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from app.models.public_api_key import PublicApiKey
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_models_public_api_key.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/public_api_key.py backend/app/models/__init__.py backend/tests/test_models_public_api_key.py
git commit -m "feat: add PublicApiKey model for REST API authentication"
```

---

### Task 3: 创建缓存数据模型

**Files:**
- Create: `backend/app/models/cached_stock.py`
- Create: `backend/app/models/cached_financial.py`
- Create: `backend/app/models/public_query_log.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建缓存股票模型**

Create `backend/app/models/cached_stock.py`:

```python
"""CachedStock model for storing Tushare stock data."""
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class CachedStock(Base):
    __tablename__ = "cached_stocks"

    ts_code = Column(String(20), primary_key=True)
    name = Column(String(50))
    industry = Column(String(50), index=True)
    area = Column(String(50), index=True)
    market = Column(String(20))
    list_date = Column(String(8))
    list_status = Column(String(1))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_industry', 'industry'),
        Index('idx_area', 'area'),
    )
```

- [ ] **Step 2: 创建缓存财务指标模型**

Create `backend/app/models/cached_financial.py`:

```python
"""CachedFinancialIndicator model for storing financial metrics."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class CachedFinancialIndicator(Base):
    __tablename__ = "cached_financial_indicators"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    end_date = Column(String(8), nullable=False, index=True)
    roe = Column(Numeric(10, 2))
    roa = Column(Numeric(10, 2))
    grossprofit_margin = Column(Numeric(10, 2))
    netprofit_margin = Column(Numeric(10, 2))
    debt_to_assets = Column(Numeric(10, 2))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_end_date', 'end_date'),
    )
```

- [ ] **Step 3: 创建公开查询日志模型**

Create `backend/app/models/public_query_log.py`:

```python
"""PublicQueryLog model for tracking public API queries."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class PublicQueryLog(Base):
    __tablename__ = "public_query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query_type = Column(String(50))
    object_type = Column(String(50))
    filters = Column(JSON)  # Works with both PostgreSQL and SQLite
    result_count = Column(Integer)
    execution_time_ms = Column(Integer)
    is_public = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", backref="public_query_logs")
```

- [ ] **Step 4: 更新 models __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from app.models.cached_stock import CachedStock
from app.models.cached_financial import CachedFinancialIndicator
from app.models.public_query_log import PublicQueryLog
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/cached_stock.py backend/app/models/cached_financial.py backend/app/models/public_query_log.py backend/app/models/__init__.py
git commit -m "feat: add cache and query log models for public API"
```

---

### Task 4: 创建数据库迁移

**Files:**
- Create: Alembic migration file (auto-generated)

- [ ] **Step 1: 生成迁移文件**

Run: `cd backend && alembic revision --autogenerate -m "add public API models"`

- [ ] **Step 2: 检查生成的迁移文件**

Run: `ls -la backend/alembic/versions/`
Review the latest migration file to ensure it includes all new tables.

- [ ] **Step 3: 运行迁移**

Run: `cd backend && alembic upgrade head`
Expected: All tables created successfully

- [ ] **Step 4: 验证表创建**

Run: `cd backend && python -c "from app.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"`
Expected: See invite_codes, public_api_keys, cached_stocks, cached_financial_indicators, public_query_logs

- [ ] **Step 5: 提交迁移文件**

```bash
git add backend/alembic/versions/*.py
git commit -m "chore: add database migration for public API models"
```

---

## Chunk 2: 公开 API 端点实现

### Task 5: 创建邀请码注册端点

**Files:**
- Create: `backend/app/api/public_auth.py`
- Create: `backend/app/schemas/public_auth.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 编写注册端点测试**

Create `backend/tests/test_api_public_auth.py`:

```python
"""Tests for public auth API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.models.invite_code import InviteCode
from app.models.user import User


def test_register_with_valid_invite_code(client: TestClient, db_session):
    """Test user registration with valid invite code."""
    # Create invite code
    invite = InviteCode(code="VALID123")
    db_session.add(invite)
    db_session.commit()

    response = client.post(
        "/api/public/auth/register",
        json={
            "invite_code": "VALID123",
            "username": "newuser",
            "email": "new@example.com"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "user_id" in data


def test_register_with_invalid_invite_code(client: TestClient):
    """Test registration fails with invalid code."""
    response = client.post(
        "/api/public/auth/register",
        json={
            "invite_code": "INVALID",
            "username": "newuser",
            "email": "new@example.com"
        }
    )
    assert response.status_code == 400
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_api_public_auth.py::test_register_with_valid_invite_code -v`
Expected: FAIL

- [ ] **Step 3: 创建 Pydantic schemas**

Create `backend/app/schemas/public_auth.py`:

```python
"""Schemas for public authentication."""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    invite_code: str
    username: str
    email: EmailStr


class RegisterResponse(BaseModel):
    success: bool
    user_id: int
    message: str


class ApiKeyRequest(BaseModel):
    username: str
    email: EmailStr


class ApiKeyResponse(BaseModel):
    success: bool
    api_key: str
    message: str
```

- [ ] **Step 4: 创建公开认证端点**

Create `backend/app/api/public_auth.py`:

```python
"""Public authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import secrets
import hashlib
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.invite_code import InviteCode
from app.models.public_api_key import PublicApiKey
from app.schemas.public_auth import (
    RegisterRequest, RegisterResponse,
    ApiKeyRequest, ApiKeyResponse
)

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_with_invite_code(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user with invite code."""
    # Validate invite code
    invite = db.query(InviteCode).filter(
        InviteCode.code == request.invite_code,
        InviteCode.is_used == False
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used invite code"
        )

    # Check if expired
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code has expired"
        )

    # Check if user exists
    existing = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )

    # Create user (no password for public API users)
    user = User(
        email=request.email,
        username=request.username,
        hashed_password="",  # No password needed
        invited_by=invite.created_by
    )
    db.add(user)

    # Mark invite code as used
    invite.is_used = True
    invite.used_by = user.id
    invite.used_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return RegisterResponse(
        success=True,
        user_id=user.id,
        message="注册成功，请使用 /api/public/auth/api-key 获取 API Key"
    )


@router.post("/api-key", response_model=ApiKeyResponse)
def get_api_key(
    request: ApiKeyRequest,
    db: Session = Depends(get_db)
):
    """Get API key for registered user."""
    user = db.query(User).filter(
        User.email == request.email,
        User.username == request.username
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user already has an active API key
    existing_key = db.query(PublicApiKey).filter(
        PublicApiKey.user_id == user.id,
        PublicApiKey.is_active == True
    ).first()

    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active API key"
        )

    # Generate new API key
    raw_key = f"omaha_pub_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = PublicApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=raw_key[:16]
    )
    db.add(api_key)
    db.commit()

    return ApiKeyResponse(
        success=True,
        api_key=raw_key,
        message="请妥善保管此 API Key，不会再次显示"
    )
```

- [ ] **Step 5: 注册路由到主应用**

Edit `backend/app/main.py` to add:

```python
from app.api import public_auth

app.include_router(
    public_auth.router,
    prefix="/api/public/auth",
    tags=["public-auth"]
)
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && pytest tests/test_api_public_auth.py -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add backend/app/api/public_auth.py backend/app/schemas/public_auth.py backend/app/main.py backend/tests/test_api_public_auth.py
git commit -m "feat: add public auth endpoints with invite code system"
```

---

### Task 6: 创建 API Key 认证依赖

**Files:**
- Create: `backend/app/api/public_deps.py`

- [ ] **Step 1: 编写认证依赖测试**

Create `backend/tests/test_api_public_deps.py`:

```python
"""Tests for public API dependencies."""
import pytest
from fastapi import HTTPException
from app.api.public_deps import verify_api_key
from app.models.public_api_key import PublicApiKey
from app.models.user import User
import hashlib


def test_verify_valid_api_key(db_session):
    """Test API key verification with valid key."""
    user = User(email="test@example.com", username="test", hashed_password="")
    db_session.add(user)
    db_session.commit()

    raw_key = "omaha_pub_test123"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = PublicApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix="omaha_pub_test"
    )
    db_session.add(api_key)
    db_session.commit()

    # Test with proper Authorization header format
    result = verify_api_key(f"Bearer {raw_key}", db_session)
    assert result.id == user.id


def test_verify_invalid_api_key(db_session):
    """Test API key verification fails with invalid key."""
    with pytest.raises(HTTPException) as exc:
        verify_api_key("Bearer invalid_key", db_session)
    assert exc.value.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_api_public_deps.py -v`
Expected: FAIL

- [ ] **Step 3: 创建认证依赖**

Create `backend/app/api/public_deps.py`:

```python
"""Dependencies for public API endpoints."""
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import hashlib
from datetime import datetime

from app.database import get_db
from app.models.public_api_key import PublicApiKey
from app.models.user import User


def verify_api_key(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """Verify API key from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )

    raw_key = authorization[7:]  # Remove "Bearer " prefix
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = db.query(PublicApiKey).filter(
        PublicApiKey.key_hash == key_hash,
        PublicApiKey.is_active == True
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )

    # Update last used timestamp
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    # Return user
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_api_public_deps.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/public_deps.py backend/tests/test_api_public_deps.py
git commit -m "feat: add API key authentication dependency for public API"
```

---

### Task 7: 创建公开查询 API 端点

**Files:**
- Create: `backend/app/api/public_query.py`
- Create: `backend/app/schemas/public_query.py`
- Create: `backend/app/services/cache_service.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建缓存服务**

Create `backend/app/services/cache_service.py`:

```python
"""Cache service for querying cached data."""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.models.cached_stock import CachedStock
from app.models.cached_financial import CachedFinancialIndicator


class CacheService:
    """Service for querying cached Tushare data."""

    def __init__(self, db: Session):
        self.db = db

    def query_stocks(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query cached stocks with filters."""
        query = self.db.query(CachedStock)

        if filters:
            for f in filters:
                field = f.get("field")
                operator = f.get("operator")
                value = f.get("value")

                if operator == "=":
                    query = query.filter(getattr(CachedStock, field) == value)
                elif operator == "like":
                    query = query.filter(getattr(CachedStock, field).like(f"%{value}%"))

        results = query.limit(limit).all()
        return [
            {
                "ts_code": r.ts_code,
                "name": r.name,
                "industry": r.industry,
                "area": r.area,
                "market": r.market,
                "list_date": r.list_date
            }
            for r in results
        ]

    def query_financial_indicators(
        self,
        ts_codes: List[str],
        limit: int = 100
    ) -> Dict[str, Dict[str, Any]]:
        """Query cached financial indicators for given stocks."""
        results = self.db.query(CachedFinancialIndicator).filter(
            CachedFinancialIndicator.ts_code.in_(ts_codes)
        ).limit(limit).all()

        data = {}
        for r in results:
            if r.ts_code not in data:
                data[r.ts_code] = {
                    "roe": float(r.roe) if r.roe else None,
                    "roa": float(r.roa) if r.roa else None,
                    "grossprofit_margin": float(r.grossprofit_margin) if r.grossprofit_margin else None,
                    "netprofit_margin": float(r.netprofit_margin) if r.netprofit_margin else None,
                    "debt_to_assets": float(r.debt_to_assets) if r.debt_to_assets else None,
                }
        return data
```

- [ ] **Step 2: 创建查询 schemas**

Create `backend/app/schemas/public_query.py`:

```python
"""Schemas for public query API."""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class FilterItem(BaseModel):
    field: str
    operator: str
    value: Any


class QueryRequest(BaseModel):
    object_type: str
    selected_columns: Optional[List[str]] = None
    filters: Optional[List[FilterItem]] = None
    limit: int = 100


class QueryResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    count: int
    cached: bool
    execution_time_ms: int


class ObjectListResponse(BaseModel):
    success: bool
    objects: List[Dict[str, str]]


class SchemaResponse(BaseModel):
    success: bool
    object_type: str
    fields: List[Dict[str, str]]
```

- [ ] **Step 3: 创建公开查询端点**

Create `backend/app/api/public_query.py`:

```python
"""Public query API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import time

from app.database import get_db
from app.api.public_deps import verify_api_key
from app.models.user import User
from app.models.public_query_log import PublicQueryLog
from app.schemas.public_query import (
    QueryRequest, QueryResponse,
    ObjectListResponse, SchemaResponse
)
from app.services.cache_service import CacheService

router = APIRouter()


@router.get("/objects", response_model=ObjectListResponse)
def list_objects(
    current_user: User = Depends(verify_api_key)
):
    """List available business objects."""
    return ObjectListResponse(
        success=True,
        objects=[
            {"name": "Stock", "description": "A股上市公司基本信息"},
            {"name": "FinancialIndicator", "description": "财务指标数据"}
        ]
    )


@router.get("/schema/{object_type}", response_model=SchemaResponse)
def get_schema(
    object_type: str,
    current_user: User = Depends(verify_api_key)
):
    """Get schema for a business object."""
    schemas = {
        "Stock": [
            {"name": "ts_code", "type": "string", "description": "股票代码"},
            {"name": "name", "type": "string", "description": "股票名称"},
            {"name": "industry", "type": "string", "description": "所属行业"},
            {"name": "area", "type": "string", "description": "地区"},
            {"name": "market", "type": "string", "description": "市场类型"},
            {"name": "list_date", "type": "string", "description": "上市日期"}
        ],
        "FinancialIndicator": [
            {"name": "ts_code", "type": "string", "description": "股票代码"},
            {"name": "roe", "type": "number", "description": "净资产收益率"},
            {"name": "roa", "type": "number", "description": "总资产收益率"},
            {"name": "grossprofit_margin", "type": "number", "description": "销售毛利率"},
            {"name": "netprofit_margin", "type": "number", "description": "销售净利率"},
            {"name": "debt_to_assets", "type": "number", "description": "资产负债率"}
        ]
    }

    if object_type not in schemas:
        raise HTTPException(status_code=404, detail="Object type not found")

    return SchemaResponse(
        success=True,
        object_type=object_type,
        fields=schemas[object_type]
    )


@router.post("/query", response_model=QueryResponse)
def query_data(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_api_key)
):
    """Query business object data with rate limiting."""
    # Check rate limit: 100 queries per hour per user
    from datetime import datetime, timedelta
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_queries = db.query(PublicQueryLog).filter(
        PublicQueryLog.user_id == current_user.id,
        PublicQueryLog.created_at >= one_hour_ago
    ).count()

    if recent_queries >= 100:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: 100 queries per hour"
        )

    start_time = time.time()

    cache_service = CacheService(db)

    if request.object_type == "Stock":
        filters = [f.dict() for f in request.filters] if request.filters else None
        data = cache_service.query_stocks(filters=filters, limit=request.limit)
    else:
        raise HTTPException(status_code=400, detail="Unsupported object type")

    execution_time = int((time.time() - start_time) * 1000)

    # Log query
    log = PublicQueryLog(
        user_id=current_user.id,
        query_type="query",
        object_type=request.object_type,
        filters={"filters": filters} if filters else {},
        result_count=len(data),
        execution_time_ms=execution_time
    )
    db.add(log)
    db.commit()

    return QueryResponse(
        success=True,
        data=data,
        count=len(data),
        cached=True,
        execution_time_ms=execution_time
    )
```

- [ ] **Step 4: 注册路由**

Edit `backend/app/main.py` to add:

```python
from app.api import public_query

app.include_router(
    public_query.router,
    prefix="/api/public/v1",
    tags=["public-query"]
)
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/public_query.py backend/app/schemas/public_query.py backend/app/services/cache_service.py backend/app/main.py
git commit -m "feat: add public query API endpoints with caching"
```

---

## Chunk 3: 数据同步脚本

### Task 8: 创建数据同步脚本

**Files:**
- Create: `backend/scripts/sync_tushare_data.py`
- Create: `backend/scripts/generate_invite_codes.py`

- [ ] **Step 1: 创建 Tushare 数据同步脚本**

Create `backend/scripts/sync_tushare_data.py`:

```python
"""Sync Tushare data to cache tables."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tushare as ts
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import SessionLocal
from app.models.cached_stock import CachedStock
from app.models.cached_financial import CachedFinancialIndicator
from app.config import settings


def sync_stocks(db: Session):
    """Sync stock basic info."""
    print("Syncing stock basic info...")
    pro = ts.pro_api(settings.TUSHARE_TOKEN)

    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name,area,industry,market,list_date,list_status')

    count = 0
    for _, row in df.iterrows():
        stock = db.query(CachedStock).filter(CachedStock.ts_code == row['ts_code']).first()

        if stock:
            stock.name = row['name']
            stock.industry = row['industry']
            stock.area = row['area']
            stock.market = row['market']
            stock.list_date = row['list_date']
            stock.list_status = row['list_status']
            stock.cached_at = datetime.utcnow()
        else:
            stock = CachedStock(
                ts_code=row['ts_code'],
                name=row['name'],
                industry=row['industry'],
                area=row['area'],
                market=row['market'],
                list_date=row['list_date'],
                list_status=row['list_status']
            )
            db.add(stock)

        count += 1
        if count % 100 == 0:
            db.commit()
            print(f"Synced {count} stocks...")

    db.commit()
    print(f"Total synced: {count} stocks")


def sync_financial_indicators(db: Session):
    """Sync financial indicators for all stocks."""
    print("Syncing financial indicators...")
    pro = ts.pro_api(settings.TUSHARE_TOKEN)

    stocks = db.query(CachedStock).all()
    count = 0

    for stock in stocks:
        try:
            df = pro.fina_indicator(ts_code=stock.ts_code, fields='ts_code,end_date,roe,roa,grossprofit_margin,netprofit_margin,debt_to_assets')

            if df.empty:
                continue

            latest = df.iloc[0]

            existing = db.query(CachedFinancialIndicator).filter(
                CachedFinancialIndicator.ts_code == stock.ts_code,
                CachedFinancialIndicator.end_date == latest['end_date']
            ).first()

            if existing:
                existing.roe = latest['roe']
                existing.roa = latest['roa']
                existing.grossprofit_margin = latest['grossprofit_margin']
                existing.netprofit_margin = latest['netprofit_margin']
                existing.debt_to_assets = latest['debt_to_assets']
                existing.cached_at = datetime.utcnow()
            else:
                indicator = CachedFinancialIndicator(
                    ts_code=stock.ts_code,
                    end_date=latest['end_date'],
                    roe=latest['roe'],
                    roa=latest['roa'],
                    grossprofit_margin=latest['grossprofit_margin'],
                    netprofit_margin=latest['netprofit_margin'],
                    debt_to_assets=latest['debt_to_assets']
                )
                db.add(indicator)

            count += 1
            if count % 50 == 0:
                db.commit()
                print(f"Synced {count} financial indicators...")

        except Exception as e:
            print(f"Error syncing {stock.ts_code}: {e}")
            continue

    db.commit()
    print(f"Total synced: {count} financial indicators")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        sync_stocks(db)
        sync_financial_indicators(db)
    finally:
        db.close()
```

- [ ] **Step 2: 创建邀请码生成脚本**

Create `backend/scripts/generate_invite_codes.py`:

```python
"""Generate invite codes for user registration."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import secrets
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.invite_code import InviteCode


def generate_codes(count: int = 10, expires_days: int = 30):
    """Generate invite codes."""
    db = SessionLocal()
    try:
        codes = []
        for _ in range(count):
            code = secrets.token_urlsafe(16)
            invite = InviteCode(
                code=code,
                expires_at=datetime.utcnow() + timedelta(days=expires_days)
            )
            db.add(invite)
            codes.append(code)

        db.commit()

        print(f"Generated {count} invite codes:")
        for code in codes:
            print(f"  {code}")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10, help="Number of codes to generate")
    parser.add_argument("--expires", type=int, default=30, help="Expiration days")
    args = parser.parse_args()

    generate_codes(args.count, args.expires)
```

- [ ] **Step 3: 测试数据同步脚本**

Run: `cd backend && python scripts/sync_tushare_data.py`
Expected: Stocks and financial data synced successfully

- [ ] **Step 4: 测试邀请码生成**

Run: `cd backend && python scripts/generate_invite_codes.py --count 5`
Expected: 5 invite codes generated and printed

- [ ] **Step 5: 提交**

```bash
git add backend/scripts/sync_tushare_data.py backend/scripts/generate_invite_codes.py
git commit -m "feat: add data sync and invite code generation scripts"
```

---

### Task 9: 创建 Cron 配置

**Files:**
- Create: `deployment/crontab.txt`
- Create: `deployment/sync_wrapper.sh`

- [ ] **Step 1: 创建同步包装脚本**

Create `deployment/sync_wrapper.sh`:

```bash
#!/bin/bash
# Wrapper script for cron job
# NOTE: This script is for production deployment at /opt/omaha-cloud/

cd /opt/omaha-cloud/backend
source /opt/omaha-cloud/venv/bin/activate

python scripts/sync_tushare_data.py >> /opt/omaha-cloud/logs/sync.log 2>&1

echo "Sync completed at $(date)" >> /opt/omaha-cloud/logs/sync.log
```

- [ ] **Step 2: 创建备份脚本**

Create `deployment/backup.sh`:

```bash
#!/bin/bash
# Database backup script
# NOTE: This script is for production deployment at /opt/omaha-cloud/

BACKUP_DIR="/opt/omaha-cloud/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="omaha_cloud"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL database
pg_dump $DB_NAME > $BACKUP_DIR/omaha_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "omaha_*.sql" -mtime +7 -delete

echo "Backup completed at $(date)" >> /opt/omaha-cloud/logs/backup.log
```

- [ ] **Step 3: 创建 crontab 配置**

Create `deployment/crontab.txt`:

```
# Sync Tushare data daily at 2:00 AM
0 2 * * * /opt/omaha-cloud/deployment/sync_wrapper.sh

# Backup database daily at 3:00 AM
0 3 * * * /opt/omaha-cloud/deployment/backup.sh
```

- [ ] **Step 4: 提交**

```bash
git add deployment/crontab.txt deployment/sync_wrapper.sh deployment/backup.sh
git commit -m "chore: add cron configuration and backup script"
```

---

## Chunk 4: Claude Code Skill 实现

### Task 10: 创建 financial-ontology-cloud Skill

**Files:**
- Create: `.claude/skills/financial-ontology-cloud/SKILL.md`
- Create: `.claude/skills/financial-ontology-cloud/examples.md`
- Create: `.claude/skills/financial-ontology-cloud/setup.md`

- [ ] **Step 1: 创建 Skill 主文档**

Create `.claude/skills/financial-ontology-cloud/SKILL.md`:

```markdown
# Financial Ontology Cloud Skill

## Overview

Query A-share financial data through Omaha OntoCenter cloud API.

## Prerequisites

1. Get invite code from administrator
2. Register at the API endpoint
3. Obtain API key
4. Set environment variable: `export OMAHA_CLOUD_API_KEY="your_key_here"`

## Base URL

**NOTE**: Replace `your-domain.com` with your actual domain name.

```
https://your-domain.com/api/public/v1
```

## Available Objects

- **Stock**: A股上市公司基本信息
- **FinancialIndicator**: 财务指标数据

## Common Queries

### Query bank stocks

```bash
curl -X POST https://your-domain.com/api/public/v1/query \
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": [{"field": "industry", "operator": "=", "value": "银行"}],
    "limit": 20
  }'
```

### Get object schema

```bash
curl https://your-domain.com/api/public/v1/schema/Stock \
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY"
```

## Error Handling

- 401: Invalid or missing API key
- 400: Invalid request format
- 404: Object type not found
- 429: Rate limit exceeded

See examples.md for more query patterns.
```

- [ ] **Step 2: 创建示例文档**

Create `.claude/skills/financial-ontology-cloud/examples.md`:

```markdown
# Query Examples

## Example 1: Find all bank stocks

**User**: "查找所有银行股"

**Query**:
\`\`\`bash
curl -X POST $BASE_URL/query \\
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY" \\
  -d '{"object_type": "Stock", "filters": [{"field": "industry", "operator": "=", "value": "银行"}]}'
\`\`\`

## Example 2: Search by stock name

**User**: "查找平安银行"

**Query**:
\`\`\`bash
curl -X POST $BASE_URL/query \\
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY" \\
  -d '{"object_type": "Stock", "filters": [{"field": "name", "operator": "like", "value": "平安"}]}'
\`\`\`

## Example 3: List available objects

**User**: "有哪些可查询的对象？"

**Query**:
\`\`\`bash
curl $BASE_URL/objects \\
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY"
\`\`\`
```

- [ ] **Step 3: 创建设置指南**

Create `.claude/skills/financial-ontology-cloud/setup.md`:

```markdown
# Setup Guide

## Step 1: Get Invite Code

Contact the administrator to get an invite code.

## Step 2: Register

\`\`\`bash
curl -X POST https://your-domain.com/api/public/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "invite_code": "YOUR_INVITE_CODE",
    "username": "your_username",
    "email": "your@email.com"
  }'
\`\`\`

## Step 3: Get API Key

\`\`\`bash
curl -X POST https://your-domain.com/api/public/auth/api-key \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "your_username",
    "email": "your@email.com"
  }'
\`\`\`

## Step 4: Set Environment Variable

\`\`\`bash
export OMAHA_CLOUD_API_KEY="omaha_pub_xxxxx"
\`\`\`

Add to your `~/.zshrc` or `~/.bashrc` to persist.

## Step 5: Test

\`\`\`bash
curl https://your-domain.com/api/public/v1/objects \\
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY"
\`\`\`
```

- [ ] **Step 4: 提交**

```bash
git add .claude/skills/financial-ontology-cloud/
git commit -m "feat: add financial-ontology-cloud skill for Claude Code"
```

---

## Chunk 5: 部署配置

### Task 11: 创建部署配置文件

**Files:**
- Create: `deployment/nginx.conf`
- Create: `deployment/omaha-cloud.service`
- Create: `deployment/deploy.sh`

- [ ] **Step 1: 创建 Nginx 配置**

Create `deployment/nginx.conf`:

**NOTE**: Replace all instances of `your-domain.com` with your actual domain name before deployment.

```nginx
server {
    listen 80;
    server_name your-domain.com;  # REPLACE WITH YOUR DOMAIN
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # REPLACE WITH YOUR DOMAIN

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;  # REPLACE
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;  # REPLACE

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /api/public/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        return 404;
    }
}
```

- [ ] **Step 2: 创建 systemd 服务配置**

Create `deployment/omaha-cloud.service`:

```ini
[Unit]
Description=Omaha Cloud API Service
After=network.target postgresql.service

[Service]
Type=simple
User=omaha
WorkingDirectory=/opt/omaha-cloud/backend
Environment="PATH=/opt/omaha-cloud/venv/bin"
EnvironmentFile=/opt/omaha-cloud/.env
ExecStart=/opt/omaha-cloud/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: 创建部署脚本**

Create `deployment/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "Deploying Omaha Cloud..."

# Pull latest code
cd /opt/omaha-cloud
git pull origin main

# Install dependencies
source venv/bin/activate
cd backend
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart service
sudo systemctl restart omaha-cloud

echo "Deployment complete!"
```

- [ ] **Step 4: 提交**

```bash
git add deployment/nginx.conf deployment/omaha-cloud.service deployment/deploy.sh
git commit -m "chore: add deployment configuration files"
```

---

## 实施总结

本计划包含 11 个主要任务，分为 5 个 chunk：

1. **Chunk 1**: 数据库模型和迁移（Task 1-4）
2. **Chunk 2**: 公开 API 端点实现（Task 5-7）
3. **Chunk 3**: 数据同步脚本（Task 8-9）
4. **Chunk 4**: Claude Code Skill 实现（Task 10）
5. **Chunk 5**: 部署配置（Task 11）

每个任务遵循 TDD 流程：测试 → 实现 → 验证 → 提交。

预计实施时间：1-2 周
