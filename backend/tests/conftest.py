import os
import tempfile
import pytest
from app.db.base import Base
from app.db.session import engine

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
