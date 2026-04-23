from datetime import datetime
from uuid import uuid4

from models import StudySession
from studyflow_backend.service import StudyFlowBackend


def test_dashboard_columns_split_tasks_by_schedule(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "dashboard_state.json")
    subject = backend.getSubjects()[0]
    backend.addTask(f"Dashboard Upcoming Seed {uuid4().hex}", str(subject["id"]), "Medium", "tomorrow")

    columns = {column["key"]: column for column in backend.dashboardColumns}

    assert columns["overdue"]["count"] >= 1
    assert columns["due_today"]["count"] >= 1
    assert columns["upcoming"]["count"] >= 1
    assert all(item["bucket"] == "overdue" for item in columns["overdue"]["items"])
    assert all(item["bucket"] == "due_today" for item in columns["due_today"]["items"])
    assert all(item["bucket"] == "upcoming" for item in columns["upcoming"]["items"])


def test_complete_revision_updates_task_and_topic_state(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "dashboard_state.json")
    target_task = next(task for task in backend._tasks if not backend._is_task_completed(task))
    target_topic = next(topic for topic in backend._topics if topic["name"] == target_task["topic"])
    original_progress = target_topic["progress"]
    original_confidence = target_topic["confidence"]

    backend.completeRevision(target_task["id"], 4)
    updated_task = next(task for task in backend._tasks if task["id"] == target_task["id"])
    updated_topic = next(topic for topic in backend._topics if topic["name"] == target_task["topic"])

    assert updated_task["completed"] is True
    assert isinstance(updated_task["completed_at"], datetime)
    assert updated_topic["confidence"] >= original_confidence
    assert updated_topic["progress"] > original_progress


def test_start_session_creates_and_stops_study_session(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "dashboard_state.json")

    backend.startSession()
    active = backend.activeSession

    assert active["active"] is True
    assert active["label"] == "End Session"

    backend.stopSession()

    assert backend.activeSession["active"] is False
    with backend._db() as db:
        sessions = db.query(StudySession).order_by(StudySession.id.desc()).all()
        assert sessions
        assert sessions[0].ended_at is not None
        assert sessions[0].duration_minutes is not None
