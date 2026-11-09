"""Hosting on Render (22 Oct): database URLs, generated keys, the public address and the built frontend."""
import base64
import os

from cryptography.fernet import Fernet

from app.config import Settings
from app.db import _normalise_url
from app.security import _as_fernet_key


def test_render_database_urls_use_psycopg():
    assert _normalise_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert _normalise_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert _normalise_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert _normalise_url("sqlite:///./nowbuilder.db") == "sqlite:///./nowbuilder.db"


def test_generated_keys_in_either_base64_work():
    raw = bytes(range(200, 232))  # contains bytes that give + and / in standard base64
    std = base64.b64encode(raw).decode()
    assert "+" in std or "/" in std
    f = Fernet(_as_fernet_key(std))
    assert Fernet(_as_fernet_key(base64.urlsafe_b64encode(raw).decode())).decrypt(f.encrypt(b"x")) == b"x"
    real = Fernet.generate_key().decode()
    assert _as_fernet_key(real) == real.encode()
    for bad in ("short", base64.b64encode(b"x" * 16).decode()):
        try:
            _as_fernet_key(bad)
            raise AssertionError("accepted a bad key")
        except ValueError:
            pass


def test_public_address_comes_from_render(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://nowbuilder-demo.onrender.com")
    monkeypatch.delenv("NOWBUILDER_PUBLIC_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.public_url == "https://nowbuilder-demo.onrender.com"
    assert "https://nowbuilder-demo.onrender.com" in s.cors_origin_list
    monkeypatch.setenv("NOWBUILDER_PUBLIC_URL", "https://app.example.com")
    assert Settings(_env_file=None).public_url == "https://app.example.com"


def test_built_frontend_is_served_with_app_links(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "a.js").write_text("js")
    from fastapi.testclient import TestClient

    from app import main
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "static_dir", str(tmp_path))
    app = main.FastAPI()
    monkeypatch.setattr(main, "app", app)
    main._serve_frontend()
    c = TestClient(app)
    assert c.get("/").text == "<html>app</html>"
    assert c.get("/invite/abc").text == "<html>app</html>"  # links open the app
    assert c.get("/assets/a.js").text == "js"
    assert c.get("/api/unknown").status_code == 404
    assert c.get("/../../etc/passwd").text == "<html>app</html>"  # never outside the folder
    assert os.path.exists(tmp_path / "index.html")


def test_startup_waits_for_the_database_and_then_explains(monkeypatch):
    import pytest
    from sqlalchemy import create_engine

    from app import db
    bad = create_engine("postgresql+psycopg://u:p@dpg-nowhere-a.invalid:5432/x", connect_args={"connect_timeout": 2})
    monkeypatch.setattr(db, "engine", bad)
    waits = []
    with pytest.raises(db.DatabaseUnreachable) as e:
        db.wait_for_database(attempts=3, delay=5, sleep=waits.append)
    assert waits == [5, 5]
    msg = str(e.value)
    assert "dpg-nowhere-a.invalid" in msg and "same region" in msg and "External Database URL" in msg


def test_a_database_with_another_apps_tables_is_refused(tmp_path, monkeypatch):
    import pytest
    from sqlalchemy import create_engine, text

    from app import db
    other = create_engine(f"sqlite:///{tmp_path}/other.db")
    with other.begin() as conn:
        conn.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, name TEXT)"))
        conn.execute(text("INSERT INTO users VALUES ('1', 'vasu@example.com', 'Vasu')"))
    monkeypatch.setattr(db, "engine", other)
    with pytest.raises(db.ForeignDatabase) as e:
        db.init_db()
    assert "another application (users" in str(e.value) and "NOWBUILDER_DATABASE_URL" in str(e.value)
    with other.connect() as conn:  # nothing was added to the other app's table
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(users)"))]
    assert cols == ["id", "email", "name"]


def test_an_account_without_a_password_cant_sign_in():
    from app.security import verify_password
    assert verify_password("anything", None) is False and verify_password("anything", "") is False


def test_a_database_already_mixed_with_another_app_is_refused(tmp_path, monkeypatch):
    import pytest
    from sqlalchemy import create_engine, text

    from app import db
    other = create_engine(f"sqlite:///{tmp_path}/mixed.db")
    with other.begin() as conn:  # another app's users table that an earlier nowBuilder start already added columns to
        conn.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, first_name TEXT, password_hash TEXT)"))
        conn.execute(text("INSERT INTO users VALUES ('1', 'vasu@example.com', 'Vasu', NULL)"))
    monkeypatch.setattr(db, "engine", other)
    with pytest.raises(db.ForeignDatabase):
        db.init_db()
