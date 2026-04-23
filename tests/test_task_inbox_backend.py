from datetime import timedelta

from studyflow_backend.service import StudyFlowBackend


def test_add_task_creates_task_and_topic(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")
    original_task_count = len(backend._tasks)
    original_topic_count = len(backend._topics)

    backend.addTask("Essay Outline", "History", "Medium", "tomorrow")

    assert len(backend._tasks) == original_task_count + 1
    assert len(backend._topics) == original_topic_count + 1
    task = next(task for task in backend._tasks if task["topic"] == "Essay Outline")
    assert task["subject"] == "History"
    assert task["difficulty"] == "Medium"
    assert task["scheduled_at"].date() == backend._today + timedelta(days=1)
    assert any(item["topic"] == "Essay Outline" for item in backend.inboxTasks)


def test_skip_task_moves_due_date_forward(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")
    task = next(task for task in backend._tasks if not backend._is_task_completed(task))
    original_date = task["scheduled_at"].date()

    backend.skipTask(task["id"])

    assert task["scheduled_at"].date() == original_date + timedelta(days=1)


def test_mark_all_tasks_done_completes_visible_filter_only(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")
    backend.setTaskFilter("overdue")
    overdue_ids = {item["id"] for item in backend.inboxTasks}

    backend.markAllTasksDone()

    assert overdue_ids
    assert all(backend._find_task(task_id)["completed"] for task_id in overdue_ids)
    remaining_pending = [
        task for task in backend._tasks if task["id"] not in overdue_ids and not backend._is_task_completed(task)
    ]
    assert remaining_pending


def test_task_filters_and_settings_are_simplified(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "task_state.json")

    filter_keys = [item["key"] for item in backend.taskFilters]
    section_titles = [section["title"] for section in backend.settingsColumns]

    assert filter_keys == ["all", "pending", "overdue", "due_today", "upcoming", "completed"]
    assert "Account" not in section_titles
