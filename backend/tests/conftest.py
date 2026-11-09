import os
import tempfile

_tmp = tempfile.mkdtemp()
# NOWBUILDER_TEST_DATABASE_URL runs the suite on Postgres instead (as hosted), e.g.
# postgresql+psycopg://nowbuilder@localhost:5433/nowbuilder_test
os.environ["NOWBUILDER_DATABASE_URL"] = os.environ.get("NOWBUILDER_TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db"
os.environ["NOWBUILDER_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["NOWBUILDER_REQUIRE_EMAIL_VERIFICATION"] = "false"  # verification has its own tests (test_email_auth.py)
os.environ["NOWBUILDER_SMTP_HOST"] = ""  # emails go to the dev outbox
os.environ["NOWBUILDER_DATA_DIR"] = f"{_tmp}/data"
os.environ["NOWBUILDER_ENCRYPTION_KEY"] = "Q0hBTkdFTUUtdGVzdC1rZXktMzItYnl0ZXMtbG9uZyE="
# Most tests drive Approve and Deploy by hand; automatic deployment has its own tests (test_auto_deploy.py)
os.environ["NOWBUILDER_AUTO_DEPLOY"] = "false"
# No ServiceNow SDK project on the test machine unless a test sets one up
os.environ["NOWBUILDER_SDK_PROJECT_DIR"] = ""
os.environ["NOWBUILDER_SDK_AUTO_SETUP"] = "false"
os.environ["NOWBUILDER_SDK_AUTH_ALIAS"] = ""
os.environ["NOWBUILDER_SDK_SCOPE"] = ""
os.environ["NOWBUILDER_SDK_VERSION"] = ""
os.environ["NOWBUILDER_SDK_INSTANCE_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import servicenow  # noqa: E402

from .fake_snow import FakeInstance  # noqa: E402


def _reset_db() -> None:
    if engine.dialect.name == "postgresql":  # background threads of the last test may still hold connections
        from sqlalchemy import text
        engine.dispose()
        with engine.connect() as conn:
            conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()"))
            conn.commit()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    _reset_db()
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client):
    r = client.post("/api/auth/register", json={"first_name": "Vasu", "last_name": "Dharavath", "email": "vasu@example.com", "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def snow():
    """A fake ServiceNow instance every ServiceNowClient talks to during the test."""
    fake = FakeInstance()
    servicenow.DEFAULT_TRANSPORT = fake.transport
    yield fake
    servicenow.DEFAULT_TRANSPORT = None


def connect_instance(client, headers, name="Dev", url="dev410284", instance_type="Development", **kw):
    body = {"name": name, "instance_type": instance_type, "url": url, "username": "admin", "password": "pw", **kw}
    return client.post("/api/instances", json=body, headers=headers)
