from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _normalise_url(url: str) -> str:
    """Hosting providers give postgres:// or postgresql:// URLs; nowBuilder talks to Postgres with psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _make_engine(url: str):
    url = _normalise_url(url)
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, **kwargs)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseUnreachable(RuntimeError):
    """The database can't be reached at startup (after waiting); the message says what to check."""


def wait_for_database(attempts: int = 12, delay: float = 5.0, sleep=None) -> None:
    """A new hosted database can take a few minutes to come up: retry for about a minute before giving up,
    then explain in one line instead of a stack trace."""
    import logging
    import time

    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    log = logging.getLogger("nowbuilder")
    sleep = sleep or time.sleep
    last = ""
    for n in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            if n > 1:
                log.warning("Database reachable after %d tries.", n)
            return
        except OperationalError as e:
            last = str(e.orig if getattr(e, "orig", None) else e).splitlines()[0]
            log.warning("Database not reachable yet (try %d of %d): %s", n, attempts, last)
            if n < attempts:
                sleep(delay)
    host = engine.url.host or "(local file)"
    hint = ""
    if "resolve host" in last or "Name or service not known" in last:
        hint = (f" The address {host} can't be found. On Render, an internal database address only works when the "
                "web service and the database are in the same region and the database is Available. Check both "
                "regions, or set NOWBUILDER_DATABASE_URL to the database's External Database URL.")
    elif "password authentication failed" in last:
        hint = " The user name or password in NOWBUILDER_DATABASE_URL is wrong."
    raise DatabaseUnreachable(f"nowBuilder can't reach its database: {last}.{hint}")


# Columns nowBuilder's tables have had since the first version: a table with the same name but without
# them belongs to another app, and nowBuilder must not add its columns to it or mix its data in.
_CORE_COLUMNS = {"users": {"id", "email", "password_hash", "first_name"}, "plans": {"id", "chat_id", "components"},
                 "instances": {"id", "user_id", "instance_type"}, "chats": {"id", "user_id", "title"}}


class ForeignDatabase(DatabaseUnreachable):
    """The database already holds another application's tables."""


def _refuse_foreign_tables() -> None:
    from sqlalchemy import inspect
    insp = inspect(engine)
    foreign = [t for t, cols in _CORE_COLUMNS.items()
               if insp.has_table(t) and not cols <= {c["name"] for c in insp.get_columns(t)}]
    if not foreign and insp.has_table("users") and "password_hash" in {c["name"] for c in insp.get_columns("users")}:
        from sqlalchemy import text
        with engine.connect() as conn:  # nowBuilder accounts always have a password: rows without one are another app's
            if conn.execute(text("SELECT 1 FROM users WHERE password_hash IS NULL LIMIT 1")).first():
                foreign = ["users"]
    if foreign:
        raise ForeignDatabase(
            f"This database already has tables from another application ({', '.join(foreign)} without nowBuilder's columns), so "
            "nowBuilder won't use it: its data could be mixed or changed. Give nowBuilder its own empty database "
            "(a new database, or CREATE DATABASE nowbuilder_app in the same server) and set NOWBUILDER_DATABASE_URL to it.")


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    if engine.dialect.name != "sqlite":
        wait_for_database()
    _refuse_foreign_tables()
    Base.metadata.create_all(engine)
    new_verification = _lacks_column("users", "email_verified_at")
    _add_missing_columns()
    if new_verification:  # people who signed up before email verification existed count as verified
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL"))
    _one_active_membership()
    _release_stuck_plans()


def _release_stuck_plans() -> None:
    """A plan marked busy (building, fixing, deploying) when the backend stopped stays busy forever,
    and every button on it is refused. Nothing runs in a process that just started, so clear them."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("UPDATE plans SET busy = NULL, busy_since = NULL, progress = NULL WHERE busy IS NOT NULL"))


def _lacks_column(table: str, column: str) -> bool:
    from sqlalchemy import inspect
    insp = inspect(engine)
    return insp.has_table(table) and column not in {c["name"] for c in insp.get_columns(table)}


def _one_active_membership() -> None:
    """One active (or turned-off) membership per person, enforced by the database.

    Before 22 Oct, opening the app sent several requests at once and each could create the
    person's own workspace, so some people own several. Empty duplicates (no instances, chats, AI key,
    integrations or other members) are closed; the person keeps the
    workspace they use now (their newest membership). Duplicates that hold data stay, so a
    platform admin can look at them and delete them on the Platform page; until then the index
    can't be created and the in-process lock in `ensure_membership` is the guard."""
    import logging

    from sqlalchemy import func, select, text
    from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

    from .models import AIProviderConfig, Chat, Instance, Integration, Membership, Workspace

    live = ("active", "disabled")
    with SessionLocal() as db:
        dup_users = db.scalars(select(Membership.user_id).where(Membership.status.in_(live))
                               .group_by(Membership.user_id).having(func.count() > 1)).all()
        for uid in dup_users:
            rows = db.scalars(select(Membership).where(Membership.user_id == uid, Membership.status.in_(live))
                              .order_by(Membership.created_at.desc())).all()
            for m in rows[1:]:  # rows[0] is the one the person uses now
                ws_id = m.workspace_id
                others = db.scalar(select(func.count()).select_from(Membership).where(
                    Membership.workspace_id == ws_id, Membership.status.in_(live), Membership.user_id != uid)) or 0
                has_data = others or any(db.scalar(select(func.count()).select_from(t).where(t.workspace_id == ws_id))
                                         for t in (Instance, Chat, AIProviderConfig, Integration))
                if has_data:
                    continue
                m.status = "left"
                ws = db.get(Workspace, ws_id)
                if ws is not None and ws.owner_id == uid:
                    ws.status = "closed"
        db.commit()
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_membership ON memberships (user_id) "
                              "WHERE status IN ('active', 'disabled')"))
    except (IntegrityError, OperationalError, ProgrammingError):
        logging.getLogger(__name__).warning("Some people still belong to more than one workspace with data; "
                                            "delete the ones not in use on the Platform page.")


def _add_missing_columns() -> None:
    """Add columns introduced after a table was first created.

    Stop-gap until Alembic migrations (Chunk 7): only adds nullable columns or ones with a
    simple default, never changes or drops anything.
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                ddl_type = col.type.compile(dialect=engine.dialect)
                default = col.default.arg if col.default is not None and not callable(col.default.arg) else None
                if isinstance(default, bool):
                    clause = f" DEFAULT {'TRUE' if default else 'FALSE'}"
                elif isinstance(default, str):
                    clause = " DEFAULT '" + default.replace("'", "''") + "'"
                else:
                    clause = ""
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl_type}{clause}'))
