import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.auth.tenant import Tenant
from app.models.auth.user import User
from app.models.project.project import Project


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
