from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
import logging
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from models import Base

logger = logging.getLogger(__name__)


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


@contextmanager
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
            backup_path = resolved_path.with_name(
                f"{resolved_path.stem}.schema-mismatch-{datetime.now().strftime('%Y%m%dT%H%M%S')}{resolved_path.suffix}"
            )
            resolved_path.replace(backup_path)
            logger.warning("Backed up schema-mismatched database from %s to %s", resolved_path, backup_path)
        active_engine = engine_override or create_sqlite_engine(database_path=resolved_path)
    Base.metadata.create_all(active_engine)
    _ensure_sqlite_artifacts(active_engine)


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


def _ensure_sqlite_artifacts(active_engine: Engine) -> None:
    statements = (
        """
        INSERT OR IGNORE INTO app_settings (key, value)
        VALUES
            ('daily_time_minutes', '120'),
            ('preferred_time', '18:00')
        """,
        "CREATE INDEX IF NOT EXISTS idx_revisions_due_status ON revisions(due_at, status)",
        "CREATE INDEX IF NOT EXISTS idx_revisions_topic_status ON revisions(topic_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_revisions_open_due ON revisions(due_at) WHERE status = 'open'",
        """
        CREATE TRIGGER IF NOT EXISTS trg_topics_updated_at
        AFTER UPDATE ON topics
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE topics SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_revisions_updated_at
        AFTER UPDATE ON revisions
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE revisions SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_sessions_updated_at
        AFTER UPDATE ON study_sessions
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE study_sessions SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_tasks_updated_at
        AFTER UPDATE ON tasks
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_settings_updated_at
        AFTER UPDATE ON app_settings
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE app_settings SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """,
    )

    with active_engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
