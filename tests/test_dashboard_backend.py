from datetime import datetime

from studyflow_backend.service import StudyFlowBackend


def test_dashboard_columns_split_tasks_by_schedule(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "dashboard_state.json")

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

    backend.completeRevision(target_task["id"], 4)

    assert target_task["completed"] is True
    assert isinstance(target_task["completed_at"], datetime)
    assert target_topic["confidence"] == 5
    assert target_topic["progress"] > original_progress
