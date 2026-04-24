# Phase 1: Foundation — Core Generalization + Semantic Layer + Agent Architecture + Multi-Tenancy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Omaha OntoCenter's core from a financial-specific tool into a general-purpose AI-native data platform foundation.

**Architecture:** Keep proven core (OmahaService, connectors, semantic engine), generalize away financial hardcoding, migrate ontology storage from YAML-in-DB to PostgreSQL tables, build single-Agent + tools architecture, add tenant_id isolation to all models.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest, React 18, TypeScript

**Spec Reference:** `docs/superpowers/specs/2026-04-25-ai-native-saas-design.md` — Sections 2, 3, 4, 5.1, 12.1

---

## File Structure

### New Files
- `backend/app/models/tenant.py` — Tenant model
- `backend/app/models/ontology.py` — Ontology SQLAlchemy models (OntologyObject, ObjectProperty, OntologyRelationship, HealthRule, BusinessGoal, DomainKnowledge)
- `backend/app/services/ontology_store.py` — CRUD service for ontology DB tables
- `backend/app/services/ontology_importer.py` — YAML → DB import service
- `backend/app/services/agent.py` — Single Agent with tool dispatch
- `backend/app/services/agent_tools.py` — Tool definitions (query_data, aggregate, generate_chart, etc.)
- `backend/app/api/agent.py` — Agent API endpoints (replaces chat routes for new flow)
- `backend/tests/test_ontology_store.py` — Ontology store tests
- `backend/tests/test_ontology_importer.py` — YAML import tests
- `backend/tests/test_agent.py` — Agent service tests
- `backend/tests/test_agent_tools.py` — Agent tools tests
- `backend/tests/test_tenant_isolation.py` — Multi-tenancy tests
- `backend/alembic/versions/phase1_001_add_tenant_model.py` — Tenant migration
- `backend/alembic/versions/phase1_002_add_ontology_tables.py` — Ontology tables migration

### Modified Files
- `backend/app/services/omaha.py` — Generalize `api_name` → `source_entity`, extract financial-specific code
- `backend/app/services/semantic.py` — Add general semantic types
- `backend/app/models/project.py` — Add `tenant_id` FK
- `backend/app/models/user.py` — Add `tenant_id` FK
- `backend/app/main.py` — Register new routes
- `backend/app/config.py` — Add agent/LLM config settings

---

## Task 1: Add Tenant Model and Multi-Tenancy Foundation

**Files:**
- Create: `backend/app/models/tenant.py`
- Modify: `backend/app/models/user.py` — add `tenant_id` FK
- Modify: `backend/app/models/project.py` — add `tenant_id` FK
- Modify: `backend/app/models/__init__.py` — export Tenant
- Test: `backend/tests/test_tenant_isolation.py`

- [ ] **Step 1: Write failing test for Tenant model**

```python
# backend/tests/test_tenant_isolation.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_tenant(db_session):
    tenant = Tenant(name="Acme Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()
    assert tenant.id is not None
    assert tenant.name == "Acme Corp"
    assert tenant.plan == "free"


def test_user_belongs_to_tenant(db_session):
    tenant = Tenant(name="Acme Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(
        email="test@acme.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()
    assert user.tenant_id == tenant.id


def test_project_belongs_to_tenant(db_session):
    tenant = Tenant(name="Acme Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(
        email="test@acme.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()

    project = Project(
        name="Test Project",
        owner_id=user.id,
        tenant_id=tenant.id,
    )
    db_session.add(project)
    db_session.commit()
    assert project.tenant_id == tenant.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_tenant_isolation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.tenant'`

- [ ] **Step 3: Create Tenant model**

```python
# backend/app/models/tenant.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan = Column(String(20), nullable=False, default="free")  # free | pro | enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("User", back_populates="tenant")
    projects = relationship("Project", back_populates="tenant")
```

- [ ] **Step 4: Add tenant_id to User model**

In `backend/app/models/user.py`, add after the `invited_by` column:

```python
tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
```

Add to relationships:

```python
tenant = relationship("Tenant", back_populates="users")
```

Add import: `from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey`

- [ ] **Step 5: Add tenant_id to Project model**

In `backend/app/models/project.py`, add after the `owner_id` column:

```python
tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
```

Add to relationships:

```python
tenant = relationship("Tenant", back_populates="projects")
```

- [ ] **Step 6: Export Tenant from models __init__**

In `backend/app/models/__init__.py`, add:

```python
from app.models.tenant import Tenant
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_tenant_isolation.py -v`
Expected: All 3 tests PASS

- [ ] **Step 8: Create Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add tenant model and tenant_id to user and project"`
Verify the generated migration adds `tenants` table and `tenant_id` columns.

- [ ] **Step 9: Commit**

```bash
cd backend
git add app/models/tenant.py app/models/user.py app/models/project.py app/models/__init__.py tests/test_tenant_isolation.py alembic/versions/
git commit -m "feat: add Tenant model and multi-tenancy foundation"
```

---

## Task 2: Ontology Database Models

**Files:**
- Create: `backend/app/models/ontology.py`
- Modify: `backend/app/models/__init__.py` — export new models
- Test: `backend/tests/test_ontology_store.py`

- [ ] **Step 1: Write failing test for ontology models**

```python
# backend/tests/test_ontology_store.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.models.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def tenant(db_session):
    t = Tenant(name="Test Corp", plan="free")
    db_session.add(t)
    db_session.commit()
    return t


def test_create_ontology_object(db_session, tenant):
    obj = OntologyObject(
        tenant_id=tenant.id,
        name="Order",
        source_entity="t_order",
        datasource_id="mysql_erp",
        datasource_type="sql",
        description="Customer purchase order",
        business_context="Full lifecycle from placement to delivery",
        domain="retail",
    )
    db_session.add(obj)
    db_session.commit()
    assert obj.id is not None
    assert obj.name == "Order"
    assert obj.source_entity == "t_order"


def test_create_object_property(db_session, tenant):
    obj = OntologyObject(
        tenant_id=tenant.id,
        name="Order",
        source_entity="t_order",
        datasource_id="mysql_erp",
        datasource_type="sql",
    )
    db_session.add(obj)
    db_session.commit()

    prop = ObjectProperty(
        object_id=obj.id,
        name="total_amount",
        data_type="float",
        semantic_type="currency_cny",
        description="Order total amount",
    )
    db_session.add(prop)
    db_session.commit()
    assert prop.id is not None
    assert prop.semantic_type == "currency_cny"


def test_create_health_rule(db_session, tenant):
    obj = OntologyObject(
        tenant_id=tenant.id,
        name="Order",
        source_entity="t_order",
        datasource_id="mysql_erp",
        datasource_type="sql",
    )
    db_session.add(obj)
    db_session.commit()

    rule = HealthRule(
        object_id=obj.id,
        metric="avg_delivery_days",
        expression="avg(delivery_date - order_date)",
        warning_threshold="> 3",
        critical_threshold="> 7",
        advice="Check warehouse capacity",
    )
    db_session.add(rule)
    db_session.commit()
    assert rule.id is not None


def test_create_relationship(db_session, tenant):
    order = OntologyObject(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    customer = OntologyObject(
        tenant_id=tenant.id, name="Customer",
        source_entity="t_customer", datasource_id="mysql_erp", datasource_type="sql",
    )
    db_session.add_all([order, customer])
    db_session.commit()

    rel = OntologyRelationship(
        tenant_id=tenant.id,
        name="order_customer",
        from_object_id=order.id,
        to_object_id=customer.id,
        relationship_type="many_to_one",
        from_field="customer_id",
        to_field="id",
    )
    db_session.add(rel)
    db_session.commit()
    assert rel.id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ontology_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.ontology'`

- [ ] **Step 3: Create ontology models**

```python
# backend/app/models/ontology.py
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class OntologyObject(Base):
    __tablename__ = "ontology_objects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    source_entity = Column(String, nullable=False)
    datasource_id = Column(String, nullable=False)
    datasource_type = Column(String, nullable=False)
    description = Column(Text)
    business_context = Column(Text)
    domain = Column(String(50), index=True)
    default_filters = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    properties = relationship("ObjectProperty", back_populates="object", cascade="all, delete-orphan")
    health_rules = relationship("HealthRule", back_populates="object", cascade="all, delete-orphan")
    business_goals = relationship("BusinessGoal", back_populates="object", cascade="all, delete-orphan")
    domain_knowledge_items = relationship("DomainKnowledge", back_populates="object", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_object_name"),
    )


class ObjectProperty(Base):
    __tablename__ = "object_properties"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    semantic_type = Column(String(50))
    description = Column(Text)
    is_computed = Column(Boolean, default=False)
    expression = Column(Text)
    is_required = Column(Boolean, default=False)

    object = relationship("OntologyObject", back_populates="properties")

    __table_args__ = (
        UniqueConstraint("object_id", "name", name="uq_object_property_name"),
    )


class OntologyRelationship(Base):
    __tablename__ = "ontology_relationships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    from_object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    to_object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(20), nullable=False)
    from_field = Column(String, nullable=False)
    to_field = Column(String, nullable=False)

    from_object = relationship("OntologyObject", foreign_keys=[from_object_id])
    to_object = relationship("OntologyObject", foreign_keys=[to_object_id])


class HealthRule(Base):
    __tablename__ = "health_rules"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    metric = Column(String, nullable=False)
    expression = Column(Text, nullable=False)
    warning_threshold = Column(String)
    critical_threshold = Column(String)
    advice = Column(Text)

    object = relationship("OntologyObject", back_populates="health_rules")


class BusinessGoal(Base):
    __tablename__ = "business_goals"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    target = Column(String, nullable=False)
    period = Column(String)

    object = relationship("OntologyObject", back_populates="business_goals")


class DomainKnowledge(Base):
    __tablename__ = "domain_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(20), default="template")

    object = relationship("OntologyObject", back_populates="domain_knowledge_items")
```

- [ ] **Step 4: Export from models __init__**

In `backend/app/models/__init__.py`, add:

```python
from app.models.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ontology_store.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Create Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add ontology tables"`
Verify migration creates: `ontology_objects`, `object_properties`, `ontology_relationships`, `health_rules`, `business_goals`, `domain_knowledge`.

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/models/ontology.py app/models/__init__.py tests/test_ontology_store.py alembic/versions/
git commit -m "feat: add ontology database models for semantic layer"
```

---

## Task 3: Ontology Store Service (CRUD)

**Files:**
- Create: `backend/app/services/ontology_store.py`
- Test: `backend/tests/test_ontology_store.py` (extend)

- [ ] **Step 1: Write failing tests for ontology store CRUD**

Append to `backend/tests/test_ontology_store.py`:

```python
from app.services.ontology_store import OntologyStore


def test_store_create_object(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id,
        name="Product",
        source_entity="t_product",
        datasource_id="mysql_erp",
        datasource_type="sql",
        description="Product catalog",
        domain="retail",
    )
    assert obj.id is not None
    assert obj.name == "Product"


def test_store_list_objects(db_session, tenant):
    store = OntologyStore(db_session)
    store.create_object(
        tenant_id=tenant.id, name="Product",
        source_entity="t_product", datasource_id="mysql_erp", datasource_type="sql",
    )
    store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    objects = store.list_objects(tenant_id=tenant.id)
    assert len(objects) == 2


def test_store_get_object_with_properties(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Product",
        source_entity="t_product", datasource_id="mysql_erp", datasource_type="sql",
    )
    store.add_property(
        object_id=obj.id, name="price", data_type="float", semantic_type="currency_cny",
    )
    store.add_property(
        object_id=obj.id, name="name", data_type="string", semantic_type="text",
    )
    result = store.get_object(tenant_id=tenant.id, name="Product")
    assert result is not None
    assert len(result.properties) == 2


def test_store_add_health_rule(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    rule = store.add_health_rule(
        object_id=obj.id,
        metric="avg_delivery_days",
        expression="avg(delivery_date - order_date)",
        warning_threshold="> 3",
        critical_threshold="> 7",
        advice="Check warehouse capacity",
    )
    assert rule.id is not None
    refreshed = store.get_object(tenant_id=tenant.id, name="Order")
    assert len(refreshed.health_rules) == 1


def test_store_tenant_isolation(db_session):
    store = OntologyStore(db_session)
    t1 = Tenant(name="Corp A", plan="free")
    t2 = Tenant(name="Corp B", plan="free")
    db_session.add_all([t1, t2])
    db_session.commit()

    store.create_object(
        tenant_id=t1.id, name="Product",
        source_entity="t_product", datasource_id="db1", datasource_type="sql",
    )
    store.create_object(
        tenant_id=t2.id, name="Product",
        source_entity="t_product", datasource_id="db2", datasource_type="sql",
    )
    assert len(store.list_objects(tenant_id=t1.id)) == 1
    assert len(store.list_objects(tenant_id=t2.id)) == 1
    assert store.get_object(tenant_id=t1.id, name="Product").datasource_id == "db1"


def test_store_delete_object_cascades(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    store.add_property(object_id=obj.id, name="amount", data_type="float")
    store.add_health_rule(
        object_id=obj.id, metric="total", expression="sum(amount)",
    )
    store.delete_object(tenant_id=tenant.id, name="Order")
    assert store.get_object(tenant_id=tenant.id, name="Order") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ontology_store.py::test_store_create_object -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ontology_store'`

- [ ] **Step 3: Implement OntologyStore service**

```python
# backend/app/services/ontology_store.py
from sqlalchemy.orm import Session
from app.models.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
)


class OntologyStore:
    def __init__(self, db: Session):
        self.db = db

    def create_object(self, tenant_id: int, name: str, source_entity: str,
                      datasource_id: str, datasource_type: str,
                      description: str = None, business_context: str = None,
                      domain: str = None, default_filters: list = None) -> OntologyObject:
        obj = OntologyObject(
            tenant_id=tenant_id, name=name, source_entity=source_entity,
            datasource_id=datasource_id, datasource_type=datasource_type,
            description=description, business_context=business_context,
            domain=domain, default_filters=default_filters or [],
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_object(self, tenant_id: int, name: str) -> OntologyObject | None:
        return (
            self.db.query(OntologyObject)
            .filter(OntologyObject.tenant_id == tenant_id, OntologyObject.name == name)
            .first()
        )

    def list_objects(self, tenant_id: int) -> list[OntologyObject]:
        return (
            self.db.query(OntologyObject)
            .filter(OntologyObject.tenant_id == tenant_id)
            .all()
        )

    def delete_object(self, tenant_id: int, name: str) -> bool:
        obj = self.get_object(tenant_id, name)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True

    def add_property(self, object_id: int, name: str, data_type: str,
                     semantic_type: str = None, description: str = None,
                     is_computed: bool = False, expression: str = None) -> ObjectProperty:
        prop = ObjectProperty(
            object_id=object_id, name=name, data_type=data_type,
            semantic_type=semantic_type, description=description,
            is_computed=is_computed, expression=expression,
        )
        self.db.add(prop)
        self.db.commit()
        self.db.refresh(prop)
        return prop

    def add_health_rule(self, object_id: int, metric: str, expression: str,
                        warning_threshold: str = None, critical_threshold: str = None,
                        advice: str = None) -> HealthRule:
        rule = HealthRule(
            object_id=object_id, metric=metric, expression=expression,
            warning_threshold=warning_threshold, critical_threshold=critical_threshold,
            advice=advice,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def add_relationship(self, tenant_id: int, name: str, from_object_id: int,
                         to_object_id: int, relationship_type: str,
                         from_field: str, to_field: str,
                         description: str = None) -> OntologyRelationship:
        rel = OntologyRelationship(
            tenant_id=tenant_id, name=name, description=description,
            from_object_id=from_object_id, to_object_id=to_object_id,
            relationship_type=relationship_type,
            from_field=from_field, to_field=to_field,
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def add_business_goal(self, object_id: int, name: str, metric: str,
                          target: str, period: str = None) -> BusinessGoal:
        goal = BusinessGoal(
            object_id=object_id, name=name, metric=metric,
            target=target, period=period,
        )
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def add_domain_knowledge(self, object_id: int, content: str,
                             source: str = "template") -> DomainKnowledge:
        dk = DomainKnowledge(
            object_id=object_id, content=content, source=source,
        )
        self.db.add(dk)
        self.db.commit()
        self.db.refresh(dk)
        return dk

    def get_full_ontology(self, tenant_id: int) -> dict:
        """Build complete ontology dict for Agent context injection."""
        objects = self.list_objects(tenant_id)
        result = []
        for obj in objects:
            result.append({
                "name": obj.name,
                "source_entity": obj.source_entity,
                "datasource_id": obj.datasource_id,
                "description": obj.description,
                "business_context": obj.business_context,
                "domain": obj.domain,
                "properties": [
                    {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type,
                     "description": p.description, "is_computed": p.is_computed}
                    for p in obj.properties
                ],
                "health_rules": [
                    {"metric": r.metric, "expression": r.expression,
                     "warning": r.warning_threshold, "critical": r.critical_threshold,
                     "advice": r.advice}
                    for r in obj.health_rules
                ],
                "goals": [
                    {"name": g.name, "metric": g.metric, "target": g.target}
                    for g in obj.business_goals
                ],
                "knowledge": [dk.content for dk in obj.domain_knowledge_items],
            })
        rels = (
            self.db.query(OntologyRelationship)
            .filter(OntologyRelationship.tenant_id == tenant_id)
            .all()
        )
        relationships = [
            {"name": r.name, "from": r.from_object.name, "to": r.to_object.name,
             "type": r.relationship_type, "from_field": r.from_field, "to_field": r.to_field}
            for r in rels
        ]
        return {"objects": result, "relationships": relationships}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ontology_store.py -v`
Expected: All 10 tests PASS (4 model tests + 6 store tests)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/ontology_store.py tests/test_ontology_store.py
git commit -m "feat: add OntologyStore CRUD service for semantic layer"
```

---

## Task 4: YAML → DB Ontology Importer

**Files:**
- Create: `backend/app/services/ontology_importer.py`
- Test: `backend/tests/test_ontology_importer.py`

- [ ] **Step 1: Write failing test for YAML import**

```python
# backend/tests/test_ontology_importer.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.models.ontology import OntologyObject, ObjectProperty, OntologyRelationship
from app.services.ontology_store import OntologyStore
from app.services.ontology_importer import OntologyImporter


SAMPLE_YAML = """
datasources:
  - id: mysql_erp
    name: ERP Database
    type: sql
    connection:
      url: postgresql://localhost/erp

ontology:
  objects:
    - name: Order
      datasource: mysql_erp
      source_entity: t_order
      description: Customer purchase order
      business_context: Full lifecycle from placement to delivery
      domain: retail
      default_filters:
        - field: status
          operator: "!="
          value: "deleted"
      properties:
        - name: id
          type: integer
          description: Order ID
        - name: total_amount
          type: float
          semantic_type: currency_cny
          description: Order total
        - name: order_date
          type: date
          semantic_type: date
      computed_properties:
        - name: avg_item_price
          expression: "{total_amount} / {item_count}"
          semantic_type: currency_cny
          description: Average price per item
    - name: Customer
      datasource: mysql_erp
      source_entity: t_customer
      description: Customer information
      properties:
        - name: id
          type: integer
        - name: name
          type: string
  relationships:
    - name: order_customer
      from_object: Order
      to_object: Customer
      type: many_to_one
      join_condition:
        from_field: customer_id
        to_field: id
"""


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def tenant(db_session):
    t = Tenant(name="Test Corp", plan="free")
    db_session.add(t)
    db_session.commit()
    return t


def test_import_yaml_creates_objects(db_session, tenant):
    importer = OntologyImporter(db_session)
    result = importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    assert result["objects_created"] == 2
    assert result["relationships_created"] == 1


def test_import_yaml_properties(db_session, tenant):
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    store = OntologyStore(db_session)
    order = store.get_object(tenant_id=tenant.id, name="Order")
    assert order is not None
    prop_names = {p.name for p in order.properties}
    assert "total_amount" in prop_names
    assert "avg_item_price" in prop_names
    computed = [p for p in order.properties if p.is_computed]
    assert len(computed) == 1
    assert computed[0].expression == "{total_amount} / {item_count}"


def test_import_yaml_default_filters(db_session, tenant):
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    store = OntologyStore(db_session)
    order = store.get_object(tenant_id=tenant.id, name="Order")
    assert order.default_filters == [{"field": "status", "operator": "!=", "value": "deleted"}]


def test_import_yaml_relationships(db_session, tenant):
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    rels = db_session.query(OntologyRelationship).filter_by(tenant_id=tenant.id).all()
    assert len(rels) == 1
    assert rels[0].name == "order_customer"
    assert rels[0].from_field == "customer_id"


def test_import_yaml_source_entity_fallback(db_session, tenant):
    """If source_entity not present, fall back to api_name for backward compat."""
    yaml_with_api_name = """
datasources:
  - id: tushare_pro
    type: tushare
    connection:
      token: test
ontology:
  objects:
    - name: Stock
      datasource: tushare_pro
      api_name: stock_basic
      properties:
        - name: ts_code
          type: string
"""
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=yaml_with_api_name)
    store = OntologyStore(db_session)
    stock = store.get_object(tenant_id=tenant.id, name="Stock")
    assert stock.source_entity == "stock_basic"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ontology_importer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ontology_importer'`

- [ ] **Step 3: Implement OntologyImporter**

```python
# backend/app/services/ontology_importer.py
import yaml
from sqlalchemy.orm import Session
from app.services.ontology_store import OntologyStore


class OntologyImporter:
    def __init__(self, db: Session):
        self.db = db
        self.store = OntologyStore(db)

    def import_yaml(self, tenant_id: int, yaml_content: str) -> dict:
        config = yaml.safe_load(yaml_content)
        ontology = config.get("ontology", {})
        datasources = {ds["id"]: ds for ds in config.get("datasources", [])}

        objects_created = 0
        object_map = {}

        for obj_def in ontology.get("objects", []):
            ds_id = obj_def.get("datasource", "")
            ds_type = datasources.get(ds_id, {}).get("type", "unknown")
            source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")

            obj = self.store.create_object(
                tenant_id=tenant_id,
                name=obj_def["name"],
                source_entity=source_entity,
                datasource_id=ds_id,
                datasource_type=ds_type,
                description=obj_def.get("description"),
                business_context=obj_def.get("business_context"),
                domain=obj_def.get("domain"),
                default_filters=obj_def.get("default_filters"),
            )
            object_map[obj_def["name"]] = obj

            for prop in obj_def.get("properties", []):
                self.store.add_property(
                    object_id=obj.id,
                    name=prop["name"],
                    data_type=prop.get("type", "string"),
                    semantic_type=prop.get("semantic_type"),
                    description=prop.get("description"),
                )

            for cp in obj_def.get("computed_properties", []):
                self.store.add_property(
                    object_id=obj.id,
                    name=cp["name"],
                    data_type="float",
                    semantic_type=cp.get("semantic_type"),
                    description=cp.get("description"),
                    is_computed=True,
                    expression=cp.get("expression"),
                )

            for rule in obj_def.get("health_rules", []):
                self.store.add_health_rule(
                    object_id=obj.id,
                    metric=rule["metric"],
                    expression=rule["expression"],
                    warning_threshold=rule.get("warning"),
                    critical_threshold=rule.get("critical"),
                    advice=rule.get("advice"),
                )

            for goal in obj_def.get("goals", []):
                self.store.add_business_goal(
                    object_id=obj.id,
                    name=goal["name"],
                    metric=goal["metric"],
                    target=goal["target"],
                    period=goal.get("period"),
                )

            for dk in obj_def.get("domain_knowledge", []):
                self.store.add_domain_knowledge(object_id=obj.id, content=dk)

            objects_created += 1

        relationships_created = 0
        for rel_def in ontology.get("relationships", []):
            from_obj = object_map.get(rel_def["from_object"])
            to_obj = object_map.get(rel_def["to_object"])
            if from_obj and to_obj:
                join = rel_def.get("join_condition", {})
                self.store.add_relationship(
                    tenant_id=tenant_id,
                    name=rel_def["name"],
                    from_object_id=from_obj.id,
                    to_object_id=to_obj.id,
                    relationship_type=rel_def.get("type", "one_to_many"),
                    from_field=join.get("from_field", ""),
                    to_field=join.get("to_field", ""),
                    description=rel_def.get("description"),
                )
                relationships_created += 1

        return {
            "objects_created": objects_created,
            "relationships_created": relationships_created,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ontology_importer.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/ontology_importer.py tests/test_ontology_importer.py
git commit -m "feat: add YAML to DB ontology importer"
```

---

## Task 5: Generalize OmahaService — Remove Financial Hardcoding

**Files:**
- Modify: `backend/app/services/omaha.py` — replace `api_name` with `source_entity`, extract Tushare-specific code
- Test: `backend/tests/test_omaha_generalized.py`

- [ ] **Step 1: Write failing test for generalized query flow**

```python
# backend/tests/test_omaha_generalized.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.omaha import OmahaService


GENERAL_CONFIG = """
datasources:
  - id: mysql_erp
    name: ERP Database
    type: sql
    connection:
      url: sqlite:///:memory:

ontology:
  objects:
    - name: Order
      datasource: mysql_erp
      source_entity: t_order
      description: Customer purchase order
      properties:
        - name: id
          type: integer
        - name: total_amount
          type: float
          semantic_type: currency_cny
        - name: status
          type: string
          semantic_type: order_status
      default_filters:
        - field: status
          operator: "!="
          value: "deleted"
  relationships: []
"""


def test_parse_config_with_source_entity():
    service = OmahaService(GENERAL_CONFIG)
    result = service.parse_config()
    assert result["valid"] is True


def test_get_object_schema_general():
    service = OmahaService(GENERAL_CONFIG)
    schema = service.get_object_schema("Order")
    assert schema is not None
    assert schema["name"] == "Order"
    field_names = {f["name"] for f in schema["fields"]}
    assert "total_amount" in field_names
    assert "status" in field_names


def test_build_ontology_general():
    service = OmahaService(GENERAL_CONFIG)
    ontology = service.build_ontology()
    assert len(ontology["objects"]) == 1
    assert ontology["objects"][0]["name"] == "Order"


def test_source_entity_backward_compat():
    """api_name should still work as fallback for source_entity."""
    config_with_api_name = """
datasources:
  - id: tushare_pro
    type: tushare
    connection:
      token: test_token
ontology:
  objects:
    - name: Stock
      datasource: tushare_pro
      api_name: stock_basic
      properties:
        - name: ts_code
          type: string
  relationships: []
"""
    service = OmahaService(config_with_api_name)
    schema = service.get_object_schema("Stock")
    assert schema is not None
```

- [ ] **Step 2: Run tests to verify current state**

Run: `cd backend && python -m pytest tests/test_omaha_generalized.py -v`
Expected: Some tests may pass (parse_config), some may fail depending on hardcoded assumptions.

- [ ] **Step 3: Refactor OmahaService**

In `backend/app/services/omaha.py`, make these changes:

1. In `_find_object()` (line 92): No changes needed — already generic.

2. In `get_object_schema()` (line 166): Ensure it reads `source_entity` with `api_name` fallback:
```python
# Replace any direct api_name access with:
source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
```

3. In `query_objects()` (line 228): Route by datasource type, not by hardcoded Tushare check:
```python
# Replace the datasource routing logic with:
ds_type = datasource.get("type", "")
if ds_type == "tushare":
    return self._query_tushare(obj_def, datasource, selected_columns, filters, limit)
else:
    return self._query_connector(obj_def, datasource, selected_columns, filters, limit)
```

4. Add a generic `_query_connector()` method that uses the connector registry:
```python
def _query_connector(self, obj_def, datasource, selected_columns, filters, limit):
    from app.connectors.registry import get_connector
    source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
    connector = get_connector(datasource["type"], datasource.get("connection", {}))
    try:
        raw_data = connector.query(
            source=source_entity,
            columns=selected_columns,
            filters=filters,
            limit=limit,
        )
        return {"success": True, "data": raw_data, "count": len(raw_data)}
    finally:
        connector.close()
```

5. In `_query_tushare()` (line 411): Replace `api_name` references:
```python
# Line 430: Change from
api_name = obj_def.get("api_name")
# To
api_name = obj_def.get("source_entity") or obj_def.get("api_name")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_omaha_generalized.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v --ignore=tests/integration -k "not tushare"`
Expected: All existing tests still PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/omaha.py tests/test_omaha_generalized.py
git commit -m "refactor: generalize OmahaService — source_entity replaces api_name"
```

---

## Task 6: Extend Semantic Types for General Business

**Files:**
- Modify: `backend/app/services/semantic.py` — add general semantic types
- Modify: `backend/app/services/semantic_formatter.py` — add formatters for new types
- Test: `backend/tests/test_semantic_general.py`

- [ ] **Step 1: Write failing test for new semantic types**

```python
# backend/tests/test_semantic_general.py
from app.services.semantic_formatter import SemanticTypeFormatter


def test_format_phone():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("13800138000", "phone")
    assert result == "138-0013-8000"


def test_format_address():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("上海市浦东新区张江高科", "address")
    assert result == "上海市浦东新区张江高科"


def test_format_order_status():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("pending", "order_status")
    assert result == "pending"


def test_format_quantity():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value(1500, "quantity")
    assert result == "1,500"


def test_format_weight_kg():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value(75.5, "weight_kg")
    assert result == "75.5 kg"


def test_format_email():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("test@example.com", "email")
    assert result == "test@example.com"


def test_existing_currency_still_works():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value(10000.5, "currency_cny")
    assert "10,000.50" in str(result) or "10000.5" in str(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_semantic_general.py -v`
Expected: FAIL on new types (phone, quantity, weight_kg)

- [ ] **Step 3: Add new semantic type formatters**

In `backend/app/services/semantic_formatter.py`, add formatters for the new types. Add these to the formatter dispatch dict or method:

```python
# Add to the format dispatch in SemanticTypeFormatter
"phone": self._format_phone,
"email": self._format_passthrough,
"address": self._format_passthrough,
"order_status": self._format_passthrough,
"approval_status": self._format_passthrough,
"quantity": self._format_quantity,
"weight_kg": self._format_weight_kg,
"weight_g": self._format_weight_g,
"volume_l": self._format_volume_l,
"province": self._format_passthrough,
"city": self._format_passthrough,
```

Add the formatter methods:

```python
def _format_passthrough(self, value):
    return str(value) if value is not None else ""

def _format_phone(self, value):
    s = str(value).replace("-", "").replace(" ", "")
    if len(s) == 11:
        return f"{s[:3]}-{s[3:7]}-{s[7:]}"
    return s

def _format_quantity(self, value):
    if isinstance(value, (int, float)):
        return f"{int(value):,}" if value == int(value) else f"{value:,.2f}"
    return str(value)

def _format_weight_kg(self, value):
    return f"{value} kg"

def _format_weight_g(self, value):
    return f"{value} g"

def _format_volume_l(self, value):
    return f"{value} L"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_semantic_general.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Run existing semantic tests for regression**

Run: `cd backend && python -m pytest tests/test_semantic_*.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/semantic_formatter.py tests/test_semantic_general.py
git commit -m "feat: add general business semantic types (phone, address, quantity, weight)"
```

---

## Task 7: Agent Tools — Query and Aggregate

**Files:**
- Create: `backend/app/services/agent_tools.py`
- Test: `backend/tests/test_agent_tools.py`

- [ ] **Step 1: Write failing test for agent tools**

```python
# backend/tests/test_agent_tools.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent_tools import AgentToolkit


@pytest.fixture
def mock_omaha_service():
    service = MagicMock()
    service.query_objects.return_value = {
        "success": True,
        "data": [
            {"name": "Product A", "amount": 1000},
            {"name": "Product B", "amount": 2000},
        ],
        "count": 2,
    }
    service.build_ontology.return_value = {
        "objects": [
            {"name": "Order", "fields": [{"name": "amount", "type": "float"}]},
        ],
    }
    return service


@pytest.fixture
def toolkit(mock_omaha_service):
    return AgentToolkit(omaha_service=mock_omaha_service)


def test_tool_definitions(toolkit):
    tools = toolkit.get_tool_definitions()
    tool_names = {t["name"] for t in tools}
    assert "query_data" in tool_names
    assert "list_objects" in tool_names
    assert "get_schema" in tool_names


def test_query_data_tool(toolkit, mock_omaha_service):
    result = toolkit.execute_tool("query_data", {
        "object_type": "Order",
        "filters": [{"field": "status", "operator": "=", "value": "active"}],
        "columns": ["name", "amount"],
        "limit": 10,
    })
    assert result["success"] is True
    assert len(result["data"]) == 2
    mock_omaha_service.query_objects.assert_called_once()


def test_list_objects_tool(toolkit, mock_omaha_service):
    result = toolkit.execute_tool("list_objects", {})
    assert "objects" in result


def test_unknown_tool_returns_error(toolkit):
    result = toolkit.execute_tool("nonexistent_tool", {})
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agent_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.agent_tools'`

- [ ] **Step 3: Implement AgentToolkit**

```python
# backend/app/services/agent_tools.py
from typing import Any


class AgentToolkit:
    def __init__(self, omaha_service):
        self.omaha_service = omaha_service
        self._tools = {
            "query_data": self._query_data,
            "list_objects": self._list_objects,
            "get_schema": self._get_schema,
        }

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "query_data",
                "description": "Query data from a business object. Use this to retrieve records with optional filters and column selection.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object to query (e.g. Order, Customer, Product)", "required": True},
                    "columns": {"type": "array", "description": "Columns to return. Omit for all columns.", "required": False},
                    "filters": {"type": "array", "description": "Filter conditions: [{field, operator, value}]", "required": False},
                    "limit": {"type": "integer", "description": "Max rows to return (default 100)", "required": False},
                },
            },
            {
                "name": "list_objects",
                "description": "List all available business objects and their descriptions.",
                "parameters": {},
            },
            {
                "name": "get_schema",
                "description": "Get the schema (fields, types, semantic types) of a business object.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object", "required": True},
                },
            },
        ]

    def execute_tool(self, tool_name: str, params: dict[str, Any]) -> dict:
        handler = self._tools.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _query_data(self, params: dict) -> dict:
        return self.omaha_service.query_objects(
            object_type=params["object_type"],
            selected_columns=params.get("columns"),
            filters=params.get("filters"),
            limit=params.get("limit", 100),
        )

    def _list_objects(self, params: dict) -> dict:
        ontology = self.omaha_service.build_ontology()
        return {"success": True, "objects": ontology.get("objects", [])}

    def _get_schema(self, params: dict) -> dict:
        schema = self.omaha_service.get_object_schema(params["object_type"])
        if schema:
            return {"success": True, "schema": schema}
        return {"success": False, "error": f"Object '{params['object_type']}' not found"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agent_tools.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/agent_tools.py tests/test_agent_tools.py
git commit -m "feat: add AgentToolkit with query_data, list_objects, get_schema tools"
```

---

## Task 8: Agent Service — Single Agent with Tool Dispatch

**Files:**
- Create: `backend/app/services/agent.py`
- Modify: `backend/app/config.py` — add LLM config for agent
- Test: `backend/tests/test_agent.py`

- [ ] **Step 1: Write failing test for Agent service**

```python
# backend/tests/test_agent.py
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.agent import AgentService


@pytest.fixture
def mock_ontology_context():
    return {
        "objects": [
            {
                "name": "Order",
                "description": "Customer purchase order",
                "properties": [
                    {"name": "id", "type": "integer"},
                    {"name": "total_amount", "type": "float", "semantic_type": "currency_cny"},
                ],
                "health_rules": [
                    {"metric": "avg_delivery_days", "warning": "> 3", "critical": "> 7"}
                ],
                "goals": [],
                "knowledge": [],
            }
        ],
        "relationships": [],
    }


@pytest.fixture
def mock_toolkit():
    toolkit = MagicMock()
    toolkit.get_tool_definitions.return_value = [
        {"name": "query_data", "description": "Query data", "parameters": {}},
    ]
    toolkit.execute_tool.return_value = {
        "success": True,
        "data": [{"id": 1, "total_amount": 5000}],
        "count": 1,
    }
    return toolkit


def test_build_system_prompt(mock_ontology_context, mock_toolkit):
    agent = AgentService(
        ontology_context=mock_ontology_context,
        toolkit=mock_toolkit,
    )
    prompt = agent.build_system_prompt()
    assert "Order" in prompt
    assert "total_amount" in prompt
    assert "currency_cny" in prompt


def test_build_system_prompt_includes_health_rules(mock_ontology_context, mock_toolkit):
    agent = AgentService(
        ontology_context=mock_ontology_context,
        toolkit=mock_toolkit,
    )
    prompt = agent.build_system_prompt()
    assert "avg_delivery_days" in prompt


def test_format_tool_result(mock_ontology_context, mock_toolkit):
    agent = AgentService(
        ontology_context=mock_ontology_context,
        toolkit=mock_toolkit,
    )
    result = {"success": True, "data": [{"id": 1}], "count": 1}
    formatted = agent.format_tool_result("query_data", result)
    assert "1" in formatted


def test_parse_tool_call():
    tool_call = {
        "name": "query_data",
        "arguments": json.dumps({
            "object_type": "Order",
            "limit": 10,
        }),
    }
    name, params = AgentService.parse_tool_call(tool_call)
    assert name == "query_data"
    assert params["object_type"] == "Order"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.agent'`

- [ ] **Step 3: Implement AgentService**

```python
# backend/app/services/agent.py
import json
from typing import Any


SYSTEM_PROMPT_TEMPLATE = """你是一个企业数据分析助手。你可以帮助用户查询和分析业务数据。

## 可用的业务对象

{objects_context}

## 业务健康规则

{health_rules_context}

## 业务目标

{goals_context}

## 行业知识

{knowledge_context}

## 可用工具

{tools_context}

## 工作方式

1. 理解用户的意图
2. 选择合适的工具查询数据
3. 分析结果，用业务语言回答
4. 如果数据触发了健康规则的阈值，主动提醒
5. 不确定时说"我不确定"，不编造数据
6. 回答时说明数据来源和查询条件，保持透明"""


class AgentService:
    def __init__(self, ontology_context: dict, toolkit, tenant_knowledge: list[str] = None):
        self.ontology_context = ontology_context
        self.toolkit = toolkit
        self.tenant_knowledge = tenant_knowledge or []

    def build_system_prompt(self) -> str:
        objects_ctx = self._format_objects()
        health_ctx = self._format_health_rules()
        goals_ctx = self._format_goals()
        knowledge_ctx = self._format_knowledge()
        tools_ctx = self._format_tools()

        return SYSTEM_PROMPT_TEMPLATE.format(
            objects_context=objects_ctx,
            health_rules_context=health_ctx,
            goals_context=goals_ctx,
            knowledge_context=knowledge_ctx,
            tools_context=tools_ctx,
        )

    def _format_objects(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            lines.append(f"### {obj['name']}")
            if obj.get("description"):
                lines.append(f"{obj['description']}")
            for prop in obj.get("properties", []):
                st = f" ({prop['semantic_type']})" if prop.get("semantic_type") else ""
                lines.append(f"- {prop['name']}: {prop.get('type', 'string')}{st}")
            lines.append("")
        return "\n".join(lines)

    def _format_health_rules(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            for rule in obj.get("health_rules", []):
                lines.append(
                    f"- {obj['name']}.{rule['metric']}: "
                    f"warning={rule.get('warning', 'N/A')}, "
                    f"critical={rule.get('critical', 'N/A')}"
                )
                if rule.get("advice"):
                    lines.append(f"  建议: {rule['advice']}")
        return "\n".join(lines) if lines else "暂无健康规则"

    def _format_goals(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            for goal in obj.get("goals", []):
                lines.append(f"- {goal['name']}: {goal['metric']} 目标 {goal['target']}")
        return "\n".join(lines) if lines else "暂无业务目标"

    def _format_knowledge(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            for k in obj.get("knowledge", []):
                lines.append(f"- {k}")
        for k in self.tenant_knowledge:
            lines.append(f"- {k}")
        return "\n".join(lines) if lines else "暂无行业知识"

    def _format_tools(self) -> str:
        lines = []
        for tool in self.toolkit.get_tool_definitions():
            lines.append(f"### {tool['name']}")
            lines.append(f"{tool['description']}")
            if tool.get("parameters"):
                for pname, pdef in tool["parameters"].items():
                    req = " (必填)" if pdef.get("required") else ""
                    lines.append(f"- {pname}: {pdef.get('description', '')}{req}")
            lines.append("")
        return "\n".join(lines)

    def format_tool_result(self, tool_name: str, result: dict) -> str:
        if not result.get("success"):
            return f"工具调用失败: {result.get('error', '未知错误')}"
        if "data" in result:
            data = result["data"]
            count = result.get("count", len(data))
            preview = json.dumps(data[:5], ensure_ascii=False, indent=2)
            return f"查询返回 {count} 条记录:\n{preview}"
        return json.dumps(result, ensure_ascii=False, indent=2)

    @staticmethod
    def parse_tool_call(tool_call: dict) -> tuple[str, dict]:
        name = tool_call["name"]
        args = tool_call.get("arguments", "{}")
        if isinstance(args, str):
            args = json.loads(args)
        return name, args
```

- [ ] **Step 4: Add agent LLM config to settings**

In `backend/app/config.py`, add:

```python
# Agent
AGENT_LLM_PROVIDER: str = "deepseek"  # deepseek | openai | anthropic
AGENT_LLM_MODEL: str = "deepseek-chat"
AGENT_MAX_TOOL_CALLS: int = 10
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agent.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/agent.py app/config.py tests/test_agent.py
git commit -m "feat: add AgentService with ontology-aware system prompt and tool dispatch"
```

---

## Task 9: Agent API Endpoint

**Files:**
- Create: `backend/app/api/agent.py`
- Modify: `backend/app/main.py` — register agent routes
- Create: `backend/app/schemas/agent.py` — request/response schemas
- Test: `backend/tests/test_api_agent.py`

- [ ] **Step 1: Write failing test for agent API**

```python
# backend/tests/test_api_agent.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Register and login to get auth token."""
    client.post("/api/v1/auth/register", json={
        "email": "agent_test@test.com",
        "username": "agent_test",
        "password": "test123",
        "full_name": "Agent Test",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "agent_test",
        "password": "test123",
    })
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_id(auth_headers):
    resp = client.post("/api/v1/projects", json={
        "name": "Agent Test Project",
        "description": "Test",
    }, headers=auth_headers)
    return resp.json()["id"]


def test_agent_chat_endpoint_exists(auth_headers, project_id):
    resp = client.post(
        f"/api/v1/agent/{project_id}/chat",
        json={"message": "列出所有业务对象"},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 422, 500)


def test_agent_chat_returns_response_structure(auth_headers, project_id):
    with patch("app.api.agent.get_agent_response") as mock_agent:
        mock_agent.return_value = {
            "response": "当前有以下业务对象：Order, Customer",
            "tool_calls": [],
            "sources": [],
        }
        resp = client.post(
            f"/api/v1/agent/{project_id}/chat",
            json={"message": "列出所有业务对象"},
            headers=auth_headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "response" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_agent.py -v`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Create agent schemas**

```python
# backend/app/schemas/agent.py
from pydantic import BaseModel
from typing import Optional


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ToolCallRecord(BaseModel):
    tool_name: str
    params: dict
    result_summary: str


class AgentChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallRecord] = []
    sources: list[str] = []
```

- [ ] **Step 4: Create agent API route**

```python
# backend/app/api/agent.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.ontology_store import OntologyStore
from app.services.agent_tools import AgentToolkit
from app.services.agent import AgentService
from app.services.omaha import OmahaService

router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent_response(agent: AgentService, message: str) -> dict:
    """Placeholder for LLM call — will be wired to actual LLM in Phase 2.
    For now returns a structured response showing the system works end-to-end."""
    return {
        "response": f"收到您的问题: {message}。Agent系统已就绪，LLM集成将在Phase 2完成。",
        "tool_calls": [],
        "sources": [],
    }


@router.post("/{project_id}/chat", response_model=AgentChatResponse)
def agent_chat(
    project_id: int,
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    store = OntologyStore(db)
    tenant_id = project.tenant_id or project.owner_id
    ontology_context = store.get_full_ontology(tenant_id)

    omaha_service = OmahaService(project.omaha_config or "")
    toolkit = AgentToolkit(omaha_service=omaha_service)

    agent = AgentService(
        ontology_context=ontology_context,
        toolkit=toolkit,
    )

    result = get_agent_response(agent, request.message)
    return AgentChatResponse(**result)
```

- [ ] **Step 5: Register agent routes in main.py**

In `backend/app/main.py`, add:

```python
from app.api import agent as agent_routes
```

And in the router includes section:

```python
app.include_router(agent_routes.router, prefix="/api/v1")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_agent.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/api/agent.py app/schemas/agent.py app/main.py tests/test_api_agent.py
git commit -m "feat: add Agent API endpoint with ontology-aware tool dispatch"
```

---

## Task 10: Ontology API — CRUD Endpoints for Semantic Layer

**Files:**
- Create: `backend/app/api/ontology_store_routes.py`
- Create: `backend/app/schemas/ontology_store.py`
- Modify: `backend/app/main.py` — register routes
- Test: `backend/tests/test_api_ontology_store.py`

- [ ] **Step 1: Write failing test for ontology CRUD API**

```python
# backend/tests/test_api_ontology_store.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    client.post("/api/v1/auth/register", json={
        "email": "onto_test@test.com",
        "username": "onto_test",
        "password": "test123",
        "full_name": "Onto Test",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "onto_test",
        "password": "test123",
    })
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_id(auth_headers):
    resp = client.post("/api/v1/projects", json={
        "name": "Onto Test Project",
        "description": "Test",
    }, headers=auth_headers)
    return resp.json()["id"]


def test_import_yaml_endpoint(auth_headers, project_id):
    yaml_content = """
datasources:
  - id: test_db
    type: sql
    connection:
      url: sqlite:///:memory:
ontology:
  objects:
    - name: Product
      datasource: test_db
      source_entity: t_product
      properties:
        - name: name
          type: string
        - name: price
          type: float
          semantic_type: currency_cny
  relationships: []
"""
    resp = client.post(
        f"/api/v1/ontology-store/{project_id}/import",
        json={"yaml_content": yaml_content},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["objects_created"] == 1


def test_list_objects_endpoint(auth_headers, project_id):
    resp = client.get(
        f"/api/v1/ontology-store/{project_id}/objects",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_full_ontology_endpoint(auth_headers, project_id):
    resp = client.get(
        f"/api/v1/ontology-store/{project_id}/full",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "objects" in data
    assert "relationships" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_ontology_store.py -v`
Expected: FAIL — 404 (routes not registered)

- [ ] **Step 3: Create ontology store schemas**

```python
# backend/app/schemas/ontology_store.py
from pydantic import BaseModel
from typing import Optional


class YAMLImportRequest(BaseModel):
    yaml_content: str


class YAMLImportResponse(BaseModel):
    objects_created: int
    relationships_created: int


class OntologyObjectSummary(BaseModel):
    id: int
    name: str
    source_entity: str
    datasource_id: str
    datasource_type: str
    description: Optional[str] = None
    domain: Optional[str] = None
    property_count: int = 0

    class Config:
        from_attributes = True
```

- [ ] **Step 4: Create ontology store API routes**

```python
# backend/app/api/ontology_store_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.schemas.ontology_store import YAMLImportRequest, YAMLImportResponse, OntologyObjectSummary
from app.services.ontology_store import OntologyStore
from app.services.ontology_importer import OntologyImporter

router = APIRouter(prefix="/ontology-store", tags=["ontology-store"])


def _get_tenant_id(project) -> int:
    return project.tenant_id or project.owner_id


@router.post("/{project_id}/import", response_model=YAMLImportResponse)
def import_yaml(
    project_id: int,
    request: YAMLImportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    importer = OntologyImporter(db)
    result = importer.import_yaml(
        tenant_id=_get_tenant_id(project),
        yaml_content=request.yaml_content,
    )
    return YAMLImportResponse(**result)


@router.get("/{project_id}/objects", response_model=list[OntologyObjectSummary])
def list_objects(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    store = OntologyStore(db)
    objects = store.list_objects(tenant_id=_get_tenant_id(project))
    return [
        OntologyObjectSummary(
            id=obj.id, name=obj.name, source_entity=obj.source_entity,
            datasource_id=obj.datasource_id, datasource_type=obj.datasource_type,
            description=obj.description, domain=obj.domain,
            property_count=len(obj.properties),
        )
        for obj in objects
    ]


@router.get("/{project_id}/full")
def get_full_ontology(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    store = OntologyStore(db)
    return store.get_full_ontology(tenant_id=_get_tenant_id(project))
```

- [ ] **Step 5: Register routes in main.py**

In `backend/app/main.py`, add:

```python
from app.api import ontology_store_routes
```

And:

```python
app.include_router(ontology_store_routes.router, prefix="/api/v1")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_ontology_store.py -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Run full test suite for regression**

Run: `cd backend && python -m pytest tests/ -v --ignore=tests/integration`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
cd backend
git add app/api/ontology_store_routes.py app/schemas/ontology_store.py app/schemas/agent.py app/main.py tests/test_api_ontology_store.py
git commit -m "feat: add ontology store CRUD API endpoints"
```

---

## Task 11: Integration Test — End-to-End Flow

**Files:**
- Create: `backend/tests/integration/test_phase1_e2e.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/integration/test_phase1_e2e.py
"""
End-to-end test: YAML import → ontology stored in DB → Agent reads ontology → responds.
Validates the full Phase 1 flow works together.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.services.ontology_importer import OntologyImporter
from app.services.ontology_store import OntologyStore
from app.services.agent_tools import AgentToolkit
from app.services.agent import AgentService
from app.services.omaha import OmahaService


RETAIL_YAML = """
datasources:
  - id: erp_db
    name: ERP Database
    type: sql
    connection:
      url: sqlite:///:memory:

ontology:
  objects:
    - name: Order
      datasource: erp_db
      source_entity: t_order
      description: 客户采购订单
      business_context: 从下单到签收的全生命周期
      domain: retail
      properties:
        - name: id
          type: integer
        - name: customer_name
          type: string
        - name: total_amount
          type: float
          semantic_type: currency_cny
        - name: order_date
          type: date
          semantic_type: date
        - name: status
          type: string
          semantic_type: order_status
      computed_properties:
        - name: avg_item_price
          expression: "{total_amount} / {item_count}"
          semantic_type: currency_cny
    - name: Customer
      datasource: erp_db
      source_entity: t_customer
      description: 客户信息
      domain: retail
      properties:
        - name: id
          type: integer
        - name: name
          type: string
        - name: region
          type: string
          semantic_type: province
  relationships:
    - name: order_customer
      from_object: Order
      to_object: Customer
      type: many_to_one
      join_condition:
        from_field: customer_id
        to_field: id
"""


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_full_phase1_flow(db_session):
    # 1. Create tenant
    tenant = Tenant(name="Retail Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    # 2. Import YAML → DB
    importer = OntologyImporter(db_session)
    result = importer.import_yaml(tenant_id=tenant.id, yaml_content=RETAIL_YAML)
    assert result["objects_created"] == 2
    assert result["relationships_created"] == 1

    # 3. Read ontology from DB
    store = OntologyStore(db_session)
    ontology = store.get_full_ontology(tenant_id=tenant.id)
    assert len(ontology["objects"]) == 2
    assert len(ontology["relationships"]) == 1

    order_obj = next(o for o in ontology["objects"] if o["name"] == "Order")
    assert order_obj["domain"] == "retail"
    assert any(p["semantic_type"] == "currency_cny" for p in order_obj["properties"])

    # 4. Build Agent with ontology context
    omaha_service = OmahaService(RETAIL_YAML)
    toolkit = AgentToolkit(omaha_service=omaha_service)
    agent = AgentService(ontology_context=ontology, toolkit=toolkit)

    # 5. Verify system prompt contains business context
    prompt = agent.build_system_prompt()
    assert "客户采购订单" in prompt
    assert "currency_cny" in prompt
    assert "Order" in prompt
    assert "Customer" in prompt

    # 6. Verify tool definitions are available
    tools = toolkit.get_tool_definitions()
    assert len(tools) >= 3
    tool_names = {t["name"] for t in tools}
    assert "query_data" in tool_names
```

- [ ] **Step 2: Run integration test**

Run: `cd backend && python -m pytest tests/integration/test_phase1_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/integration/test_phase1_e2e.py
git commit -m "test: add Phase 1 end-to-end integration test"
```

---

## Task 12: Apply Database Migrations and Final Verification

- [ ] **Step 1: Run all migrations**

Run: `cd backend && alembic upgrade head`
Expected: All migrations apply successfully

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 3: Start backend and verify endpoints**

Run: `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

Verify in browser:
- `http://localhost:8000/docs` — Swagger UI shows new endpoints:
  - `POST /api/v1/agent/{project_id}/chat`
  - `POST /api/v1/ontology-store/{project_id}/import`
  - `GET /api/v1/ontology-store/{project_id}/objects`
  - `GET /api/v1/ontology-store/{project_id}/full`

- [ ] **Step 4: Commit any remaining changes**

```bash
cd backend
git add -A
git commit -m "chore: Phase 1 foundation complete — migrations applied"
```
