from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from models import Base


def build_sqlite_url(database_path: str | Path | None = None) -> str:
    path = str(database_path or settings.database_path)
    return str(URL.create("sqlite", database=path))


def create_sqlite_engine(
    database_url: str | None = None,
    *,
    database_path: str | Path | None = None,
    echo: bool = False,
) -> Engine:
    engine = create_engine(
        database_url or build_sqlite_url(database_path),
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


def create_session_factory(
    engine: Engine | None = None,
    *,
    database_url: str | None = None,
    database_path: str | Path | None = None,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine or create_sqlite_engine(database_url, database_path=database_path),
        autoflush=False,
        expire_on_commit=False,
    )


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


engine = create_sqlite_engine(database_path=settings.database_path)
SessionLocal = create_session_factory(engine)


def init_database(*, engine_override: Engine | None = None, database_path: str | Path | None = None) -> None:
    resolved_path = Path(database_path or settings.database_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    active_engine = engine_override or engine
    if _database_needs_reset(active_engine, resolved_path):
        active_engine.dispose()
        if resolved_path.exists():
            resolved_path.unlink()
    Base.metadata.create_all(active_engine)


def _database_needs_reset(active_engine: Engine, database_path: Path) -> bool:
    if not database_path.exists():
        return False

    inspector = inspect(active_engine)
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
