from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from models import Base


def build_sqlite_url(database_path: str | None = None) -> str:
    path = database_path or str(settings.database_path)
    return str(URL.create("sqlite", database=path))


def create_sqlite_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    engine = create_engine(
        database_url or build_sqlite_url(),
        echo=echo,
        future=True,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or create_sqlite_engine(), autoflush=False, expire_on_commit=False)


def get_session(factory: sessionmaker[Session] | None = None) -> Generator[Session, None, None]:
    session_factory = factory or create_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope(factory: sessionmaker[Session] | None = None) -> Generator[Session, None, None]:
    session_factory = factory or SessionLocal
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


engine = create_sqlite_engine(
    f"sqlite:///{settings.database_path.as_posix()}",
)
SessionLocal = create_session_factory(engine)


def init_database() -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    if _database_needs_reset():
        engine.dispose()
        if settings.database_path.exists():
            settings.database_path.unlink()
    Base.metadata.create_all(engine)


def _database_needs_reset() -> bool:
    if not settings.database_path.exists():
        return False

    inspector = inspect(engine)
    required_columns = {
        "subjects": {"id", "name", "color", "archived", "created_at", "updated_at"},
        "topics": {"id", "subject_id", "name", "difficulty", "status", "mastery_score", "review_count"},
        "revisions": {"id", "topic_id", "due_at", "status", "interval_days", "stability"},
    }
    table_names = set(inspector.get_table_names())
    if not set(required_columns).issubset(table_names):
        return True

    for table_name, columns in required_columns.items():
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        if not columns.issubset(existing):
            return True
    return False
