from datetime import datetime, timedelta

from services import (
    ReminderPreferences,
    ReminderScheduler,
    build_exam_warnings,
    build_morning_summary,
    write_revision_calendar,
)


def test_morning_summary_prefers_overdue_items() -> None:
    due_today = [{"name": "Photosynthesis"}]
    overdue = [{"name": "Calculus"}]

    summary = build_morning_summary(due_today, overdue)

    assert summary is not None
    assert "overdue" in summary["title"]
    assert summary["color"] == "#EF4444"


def test_morning_summary_respects_minimum_due_threshold() -> None:
    summary = build_morning_summary([{"name": "Photosynthesis"}], [], minimum_due_for_alert=2)

    assert summary is None


def test_exam_warnings_include_near_exam_topics() -> None:
    warnings = build_exam_warnings(
        [{"name": "Genetics", "subject": "Biology", "exam_date": "2026-04-20"}],
        today=datetime(2026, 4, 14).date(),
    )

    assert warnings[0]["title"] == "Genetics exam in 6 days"


def test_revision_calendar_export_contains_pending_events(tmp_path) -> None:
    output_path = tmp_path / "schedule.ics"
    scheduled_at = datetime(2026, 4, 14, 9, 0)
    tasks = [
        {
            "id": "task-1",
            "topic": "Photosynthesis",
            "subject": "Biology",
            "difficulty": "Medium",
            "confidence": 4,
            "duration_minutes": 25,
            "scheduled_at": scheduled_at,
            "completed_at": None,
        }
    ]

    write_revision_calendar(tasks, output_path, now=scheduled_at)

    contents = output_path.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in contents
    assert "SUMMARY:StudyFlow revision - Photosynthesis" in contents
    assert "DTSTART:20260414T090000" in contents


def test_reminder_scheduler_computes_next_daily_run() -> None:
    scheduler = ReminderScheduler(lambda: None, ReminderPreferences(notification_time=datetime.strptime("08:00", "%H:%M").time()))

    next_run = scheduler.next_run_at(datetime(2026, 4, 14, 9, 0))

    assert next_run == datetime(2026, 4, 15, 8, 0)
    assert next_run - datetime(2026, 4, 14, 9, 0) == timedelta(hours=23)


def test_reminder_scheduler_run_once_emits_connected_job() -> None:
    calls: list[str] = []
    scheduler = ReminderScheduler(lambda: calls.append("ran"))

    scheduler.run_once()

    assert calls == ["ran"]
