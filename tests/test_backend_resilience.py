from __future__ import annotations

import json
import logging
from datetime import timedelta

from studyflow_backend.service import StudyFlowBackend
from studyflow_backend.storage import load_state


def test_backend_logs_invalid_state_and_recovers(tmp_path, caplog) -> None:
    state_path = tmp_path / "broken_state.json"
    state_path.write_text(json.dumps({"notifications": 5}), encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        backend = StudyFlowBackend(state_path)

    assert backend.notifications


def test_load_state_handles_corrupt_json(tmp_path) -> None:
    state_path = tmp_path / "corrupt_state.json"
    state_path.write_text("{not-valid-json", encoding="utf-8")

    state = load_state(state_path)

    assert state["settings"]
    assert state["notifications"]


def test_backend_refreshes_today_after_midnight(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "rollover_state.json")
    previous_today = backend._today

    backend._selected_date = previous_today
    backend._calendar_view_date = previous_today
    backend._today_provider = lambda: previous_today + timedelta(days=1)

    assert backend._today == previous_today + timedelta(days=1)
    assert backend._selected_date == previous_today + timedelta(days=1)
    assert backend._calendar_view_date == previous_today + timedelta(days=1)


def test_concurrent_sessions_and_reads_thread_safety(tmp_path) -> None:
    import threading

    from db.session import (
        create_session_factory,
        create_sqlite_engine,
        init_database,
        session_scope,
    )
    from models import DifficultyLevel, Subject, Topic

    db_path = tmp_path / "concurrent.sqlite3"
    engine = create_sqlite_engine(database_path=db_path)
    init_database(engine_override=engine, database_path=db_path)
    factory = create_session_factory(engine)

    with session_scope(factory) as db:
        subj = Subject(name="Concurrent Subj", color="#3B82F6")
        db.add(subj)
        db.flush()
        subj_id = subj.id

    errors: list[Exception] = []

    def worker(worker_id: int) -> None:
        try:
            for i in range(10):
                with session_scope(factory) as db:
                    topic = Topic(
                        subject_id=subj_id,
                        name=f"Topic-{worker_id}-{i}",
                        difficulty=DifficultyLevel.MEDIUM,
                    )
                    db.add(topic)
                    db.flush()
                with session_scope(factory) as db:
                    count = db.query(Topic).filter(Topic.subject_id == subj_id).count()
                    assert count > 0
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert not errors, f"Concurrency errors occurred: {errors}"
    with session_scope(factory) as db:
        total = db.query(Topic).filter(Topic.subject_id == subj_id).count()
        assert total == 50
