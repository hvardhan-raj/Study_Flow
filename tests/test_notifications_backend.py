from datetime import timedelta

from time_utils import local_now
from studyflow_backend.service import StudyFlowBackend


def test_notifications_are_normalized_for_qml(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")

    notification = backend.notifications[0]

    assert {"id", "title", "body", "icon", "color", "read", "time", "timestamp"} <= set(notification)
    assert isinstance(notification["read"], bool)
    assert backend.notificationStats[0]["label"] == "Unread"


def test_mark_all_and_single_notification_read(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")
    target = next(notification for notification in backend.notifications if not notification["read"])

    backend.markNotificationRead(target["id"])

    assert next(notification for notification in backend.notifications if notification["id"] == target["id"])["read"] is True

    backend.markAllNotificationsRead()

    assert all(notification["read"] for notification in backend.notifications)


def test_alert_settings_and_digest_contracts(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")
    first_setting = backend.alertSettings[0]
    original_value = first_setting["on"]

    backend.toggleAlertSetting(first_setting["key"])

    updated = next(setting for setting in backend.alertSettings if setting["key"] == first_setting["key"])
    assert updated["on"] is (not original_value)
    assert {"summary", "nextSession", "completedToday", "unread"} <= set(backend.todayDigest)
    assert len(backend.upcomingReminders) >= 1


def test_refresh_reminders_keeps_smart_notifications_unique(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")

    backend.refreshReminders()
    backend.refreshReminders()

    smart_ids = [notification["id"] for notification in backend.notifications if notification["id"].startswith("smart-")]
    assert len(smart_ids) == len(set(smart_ids))


def test_calendar_export_and_reminder_preferences(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")

    backend.updateReminderPreference("minimum_due_for_alert", "2")
    export_path = backend.exportCalendar()

    assert backend.reminderPreferences["minimum_due_for_alert"] == 2
    assert export_path.endswith("studyflow_revisions.ics")
    assert any(notification["title"] == "Calendar Export Ready" for notification in backend.notifications)


def test_manual_reminder_check_creates_notifications(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")
    before = len(backend.notifications)

    created = backend.runReminderCheck()

    assert created >= 1
    assert len(backend.notifications) > before


def test_study_due_notification_fires_once_for_scheduled_task(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "notifications_state.json")
    calls: list[tuple[str, str]] = []

    class FakeNotifier:
        def notify(self, title: str, message: str) -> bool:
            calls.append((title, message))
            return True

    now = local_now()
    backend._desktop_notifier = FakeNotifier()
    backend._projection_cache["tasks"] = [
        {
            "id": "task-1",
            "topic": "Photosynthesis",
            "subject": "Biology",
            "scheduled_at": now.replace(tzinfo=None),
            "completed": False,
            "durationMinutes": 25,
            "subjectColor": "#3B82F6",
        },
        {
            "id": "task-2",
            "topic": "Old Task",
            "subject": "History",
            "scheduled_at": (now - timedelta(minutes=3)).replace(tzinfo=None),
            "completed": False,
            "durationMinutes": 25,
            "subjectColor": "#F59E0B",
        },
    ]

    created_first = backend._study_due_notifications(now)
    created_second = backend._study_due_notifications(now)

    assert created_first == 1
    assert created_second == 0
    assert len(calls) == 1
    assert calls[0][0] == "Time to study: Photosynthesis"
