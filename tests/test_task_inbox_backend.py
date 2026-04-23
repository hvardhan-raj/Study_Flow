from datetime import timedelta
from uuid import uuid4

from studyflow_backend.service import StudyFlowBackend


def test_add_task_creates_task_and_topic(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")
    original_task_count = len(backend._tasks)
    original_topic_count = len(backend._topics)
    history_subject = next(subject for subject in backend.getSubjects() if subject["name"] == "History")
    task_name = f"Essay Outline {uuid4().hex}"

    backend.addTask(task_name, str(history_subject["id"]), "Medium", "tomorrow")

    assert len(backend._tasks) == original_task_count + 1
    assert len(backend._topics) == original_topic_count + 1
    task = next(task for task in backend._tasks if task["topic"] == task_name)
    assert task["difficulty"] == "Medium"
    assert task["scheduled_at"].date() == backend._today + timedelta(days=1)
    assert any(item["topic"] == task_name for item in backend.inboxTasks)


def test_skip_task_reschedules_without_duplicate_open_revision(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")
    task = next(task for task in backend._tasks if not task["completed"])
    original_date = task["scheduled_at"].date()

    backend.skipTask(str(task["id"]))

    updated = next(item for item in backend._tasks if item["topic_id"] == task["topic_id"] and not item["completed"])
    assert updated["scheduled_at"].date() >= original_date + timedelta(days=1)


def test_mark_all_tasks_done_only_closes_visible_pending_items(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")
    history_subject = next(subject for subject in backend.getSubjects() if subject["name"] == "History")
    due_name = f"Due Today {uuid4().hex}"
    backend.addTask(due_name, str(history_subject["id"]), "Medium", "today")
    backend.setTaskFilter("due_today")
    due_today_ids = {item["id"] for item in backend.inboxTasks}

    backend.markAllTasksDone()

    assert due_today_ids
    task_lookup = {item["id"]: item for item in backend._tasks}
    assert all(task_lookup[task_id]["completed"] for task_id in due_today_ids)
    assert any(not task["completed"] for task_id, task in task_lookup.items() if task_id not in due_today_ids)


def test_task_filters_and_settings_are_simplified(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")

    filter_keys = [item["key"] for item in backend.taskFilters]
    section_titles = [section["title"] for section in backend.settingsColumns]

    assert filter_keys == ["all", "pending", "overdue", "due_today", "upcoming", "completed"]
    assert "Account" not in section_titles
