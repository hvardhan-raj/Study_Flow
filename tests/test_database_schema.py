from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db.session import create_session_factory, init_database
from models import AppSetting, Revision, Subject, Topic


def test_init_database_seeds_settings_and_sqlite_artifacts(tmp_path) -> None:
    database_path = tmp_path / "schema.sqlite3"

    engine = create_engine(f"sqlite+pysqlite:///{database_path}", future=True, connect_args={"check_same_thread": False})
    init_database(engine_override=engine, database_path=database_path)

    with Session(engine) as session:
        settings = {item.key: item.value for item in session.query(AppSetting).all()}
        trigger_names = {
            row[0]
            for row in session.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            )
        }
        index_names = {
            row[0]
            for row in session.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'index'")
            )
        }

    assert settings["daily_time_minutes"] == "120"
    assert settings["preferred_time"] == "18:00"
    assert {"trg_topics_updated_at", "trg_revisions_updated_at", "trg_sessions_updated_at", "trg_tasks_updated_at", "trg_settings_updated_at"} <= trigger_names
    assert {"idx_revisions_due_status", "idx_revisions_topic_status", "idx_revisions_open_due"} <= index_names


def test_updated_at_trigger_updates_timestamp_for_topic() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = create_session_factory(engine)
    init_database(engine_override=engine, database_path=":memory:")

    with factory() as session:
        subject = Subject(name="Mathematics")
        session.add(subject)
        session.flush()

        topic = Topic(subject_id=subject.id, name="Limits")
        session.add(topic)
        session.commit()

        original_updated_at = topic.updated_at
        session.execute(text("UPDATE topics SET name = :name WHERE id = :id"), {"name": "Limits and Continuity", "id": topic.id})
        session.commit()
        session.refresh(topic)

        assert topic.updated_at >= original_updated_at


def test_revision_constraints_reject_negative_interval_values() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = create_session_factory(engine)
    init_database(engine_override=engine, database_path=":memory:")

    with factory() as session:
        subject = Subject(name="Physics")
        session.add(subject)
        session.flush()

        topic = Topic(subject_id=subject.id, name="Optics")
        session.add(topic)
        session.flush()

        session.add(
            Revision(
                topic_id=topic.id,
                due_at=datetime(2026, 4, 24, 11, 0, 0),
                status="open",
                interval_days=-1.0,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
