import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps.db import get_db
from app.core import settings as settings_module
from app.db.session import Base
from app.main import app
from app.models.entities import Plan, Role


@pytest.fixture(autouse=True)
def disable_platform_login_ratelimit_in_tests(monkeypatch):
    """Tests have no Redis; keep platform password/MFA paths deterministic."""
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("PLATFORM_LOGIN_RATELIMIT_ENABLED", "false")
    yield
    settings_module.get_settings.cache_clear()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db: Session = SessionLocal()

    roles = [
        ("platform_admin", "Platform Admin"),
        ("tenant_admin", "Tenant Admin"),
        ("director", "Director"),
        ("sales_user", "Sales User"),
        ("account_manager", "Account Manager"),
        ("service_manager", "Service Manager"),
        ("marketing_user", "Marketing User"),
    ]
    for code, desc in roles:
        db.add(Role(id=uuid.uuid4(), code=code, description=desc))
    db.add(Plan(id=uuid.uuid4(), code="starter", name="Starter", price_monthly_cents=1000, is_active=True))
    db.commit()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

