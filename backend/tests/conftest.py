import pytest
from fastapi.testclient import TestClient

from sqlalchemy import text

from api.app.db import SessionLocal
from api.app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_jobs():
    """Queue tests assert on which job gets claimed, so they need an empty table."""
    s = SessionLocal()
    try:
        s.execute(text("DELETE FROM jobs"))
        s.commit()
    finally:
        s.close()
    yield


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def login(client: TestClient, email: str, password: str = "pramaan") -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()
