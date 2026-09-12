import os
import pytest
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Production Test Safety Guard: prevent test suites from running against production databases
db_url_str = str(engine.url).lower()
disallowed_keywords = ["neon.tech", "amazonaws.com", "render.com", "supabase.co", "cockroachlabs.cloud"]

if any(keyword in db_url_str for keyword in disallowed_keywords):
    raise RuntimeError(
        f"CRITICAL SAFETY ABORT: Tests attempted to execute against a production database ({engine.url.host})! "
        "Test execution has been terminated immediately to prevent data loss."
    )

from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

if not db_url_str.startswith("sqlite") and "test" not in db_url_str:
    raise RuntimeError(
        f"CRITICAL SAFETY ABORT: Tests must only execute against SQLite or an explicitly designated test database containing '_test' (got {engine.url})."
    )

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def auto_authenticate_legacy_tests(request):
    """
    For domain test suites (written before authentication was enforced across all endpoints),
    provides a mock officer user via dependency_overrides so domain functionality
    (ML, verification, extraction, RAG, etc.) remains fully testable without rewriting
    hundreds of legacy test call sites.

    Security test suites (test_auth, test_customer_portal, test_production_stabilization)
    are explicitly excluded to ensure real JWT/RBAC rejection (401/403) is strictly validated.
    """
    mod_name = request.module.__name__
    if any(k in mod_name for k in ["test_auth", "test_production_stabilization", "test_customer_portal", "test_lifecycle_and_decisions"]):
        yield
        return

    from app.main import app
    from app.api.deps import check_officer_permission, get_current_user
    from app.db.models import UserModel
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        mock_officer = db.query(UserModel).filter(UserModel.id == "usr_legacy_test_officer").first()
        if not mock_officer:
            mock_officer = UserModel(
                id="usr_legacy_test_officer",
                email="legacy_officer@genbank.com",
                name="Legacy Test Officer",
                google_id="gid_legacy_test_officer",
                role="LOAN_OFFICER"
            )
            db.add(mock_officer)
            db.commit()
            db.refresh(mock_officer)
    finally:
        db.close()

    app.dependency_overrides[check_officer_permission] = lambda: mock_officer
    app.dependency_overrides[get_current_user] = lambda: mock_officer
    yield
    app.dependency_overrides.pop(check_officer_permission, None)
    app.dependency_overrides.pop(get_current_user, None)
