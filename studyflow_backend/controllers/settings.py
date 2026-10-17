import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from models import AppSetting
from services import ReminderPreferences, SchedulerService
from studyflow_backend.defaults import default_alert_settings

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULE_SETTINGS = {
    "daily_time_minutes": "120",
    "preferred_time": "18:00",
}

ALERT_SETTING_META = {
    "due_today": ("Due Today", "Notify when revisions are scheduled for today.", "#3B82F6"),
    "overdue": ("Overdue Reviews", "Highlight slipped reviews before new study.", "#EF4444"),
    "ai_suggestions": ("AI Suggestions", "Surface schedule and recall recommendations.", "#8B5CF6"),
    "weekly_reports": ("Weekly Reports", "Show progress summary notifications.", "#10B981"),
    "session_reminders": ("Session Reminders", "Remind before planned study blocks.", "#F59E0B"),
    "streak_reminders": ("Streak Reminders", "Nudge consistency when activity drops.", "#14B8A6"),
}


class SettingsController(QObject):
    changed = Signal()

    def __init__(
        self,
        db_factory: Callable[[], Any],
        today_provider: Callable[[], Any],
        save_callback: Callable[[], None] | None = None,
        toast_callback: Callable[[str, str, str], None] | None = None,
        on_reminders_changed: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db_factory
        self._today_provider = today_provider
        self._save_callback = save_callback or (lambda: None)
        self._toast_callback = toast_callback or (lambda level, title, msg: None)
        self._on_reminders_changed = on_reminders_changed or (lambda: None)

        self._settings: dict[str, Any] = {}
        self._alert_settings: dict[str, bool] = default_alert_settings()
        self._reminder_preferences: dict[str, Any] = {
            "enabled": True,
            "notification_time": "08:00",
            "minimum_due_for_alert": 1,
            "desktop_notifications": False,
        }

    def initialize_state(
        self,
        settings: dict[str, Any] | None,
        alert_settings: dict[str, Any] | None,
        reminder_preferences: dict[str, Any] | None,
    ) -> None:
        self._settings = self._normalize_settings(settings or {})
        self._alert_settings = self._normalize_alert_settings(alert_settings or {})
        self._reminder_preferences = self._normalize_reminder_preferences(
            reminder_preferences or {}
        )

    def _normalize_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        payload = dict(settings) if isinstance(settings, dict) else {}
        notifications = payload.get("notifications", {"enabled": True})
        if isinstance(notifications, bool):
            notifications = {"enabled": notifications}
        elif not isinstance(notifications, dict):
            notifications = {"enabled": True}
        notifications.setdefault("enabled", True)
        payload["notifications"] = notifications
        payload["reminders"] = bool(payload.get("reminders", True))
        payload["auto_schedule"] = bool(payload.get("auto_schedule", True))
        return payload

    def _normalize_alert_settings(self, settings: dict[str, Any]) -> dict[str, bool]:
        normalized = default_alert_settings()
        if isinstance(settings, dict):
            for key, value in settings.items():
                normalized[key] = bool(value)
        return normalized

    def _normalize_reminder_preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "enabled": True,
            "notification_time": "08:00",
            "minimum_due_for_alert": 1,
            "desktop_notifications": False,
        }
        if isinstance(preferences, dict):
            payload.update(preferences)
        payload["enabled"] = bool(payload["enabled"])
        payload["desktop_notifications"] = bool(payload["desktop_notifications"])
        try:
            payload["minimum_due_for_alert"] = max(1, int(payload["minimum_due_for_alert"]))
        except (TypeError, ValueError):
            payload["minimum_due_for_alert"] = 1
        if (
            not isinstance(payload["notification_time"], str)
            or ":" not in payload["notification_time"]
        ):
            payload["notification_time"] = "08:00"
        return payload

    @property
    def settings_payload(self) -> dict[str, Any]:
        return dict(self._settings)

    @property
    def alert_settings_payload(self) -> dict[str, bool]:
        return dict(self._alert_settings)

    @property
    def reminder_preferences_payload(self) -> dict[str, Any]:
        return dict(self._reminder_preferences)

    def reminder_preferences_model(self) -> ReminderPreferences:
        raw_time = str(self._reminder_preferences.get("notification_time", "08:00"))
        try:
            parts = [int(p) for p in raw_time.split(":")[:2]]
            parsed_time = datetime.strptime(f"{parts[0]:02d}:{parts[1]:02d}", "%H:%M").time()
        except (ValueError, IndexError):
            parsed_time = datetime.strptime("08:00", "%H:%M").time()
        return ReminderPreferences(
            enabled=bool(self._reminder_preferences.get("enabled", True)),
            notification_time=parsed_time,
            minimum_due_for_alert=max(
                1, int(self._reminder_preferences.get("minimum_due_for_alert", 1))
            ),
            desktop_notifications=bool(
                self._reminder_preferences.get("desktop_notifications", False)
            ),
        )

    def _get_schedule_setting(self, key: str) -> str:
        default = DEFAULT_SCHEDULE_SETTINGS[key]
        try:
            with self._db() as db:
                setting = db.get(AppSetting, key)
                if setting is None:
                    setting = AppSetting(key=key, value=default)
                    db.add(setting)
                    db.flush()
                    return default
                if setting.value in (None, ""):
                    setting.value = default
                    db.flush()
                    return default
                return str(setting.value)
        except SQLAlchemyError:
            logger.exception("Failed to query schedule setting %s", key)
            return default

    def _set_schedule_setting(self, key: str, value: str) -> None:
        try:
            with self._db() as db:
                setting = db.get(AppSetting, key)
                if setting is None:
                    setting = AppSetting(key=key, value=value)
                    db.add(setting)
                else:
                    setting.value = value
                db.flush()
                today_val = self._today_provider()
                SchedulerService(db, today_provider=lambda: today_val).rebalance_schedule(
                    start_date=today_val,
                    compact=True,
                    compact_horizon_days=7,
                )
        except SQLAlchemyError:
            logger.exception("Database error while updating schedule setting %s", key)
            self._toast_callback(
                "error", "Database Error", "Failed to update schedule in database."
            )
            raise

    @Property("QVariantMap", notify=changed)
    def settings(self) -> dict[str, Any]:
        return self._settings

    @Property("QVariantMap", notify=changed)
    def alertSettings(self) -> dict[str, bool]:
        return self._alert_settings

    @Property("QVariantMap", notify=changed)
    def reminderPreferences(self) -> dict[str, Any]:
        return self._reminder_preferences

    @Property("QVariantMap", notify=changed)
    def scheduleSettings(self) -> dict[str, Any]:
        return {
            "daily_time_minutes": int(self._get_schedule_setting("daily_time_minutes")),
            "preferred_time": self._get_schedule_setting("preferred_time"),
        }

    @Property("QVariantList", notify=changed)
    def settingsColumns(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "Alert Preferences",
                "subtitle": "NOTIFICATION RULES",
                "items": [
                    {
                        "key": key,
                        "title": title,
                        "subtitle": subtitle,
                        "badge": "ALERT",
                        "color": color,
                        "enabled": bool(self._alert_settings.get(key, True)),
                    }
                    for key, (title, subtitle, color) in ALERT_SETTING_META.items()
                ],
            }
        ]

    @Slot(str, "QVariant")
    def updateSetting(self, key: str, value: Any) -> None:
        self._settings[key] = value
        try:
            self._save_callback()
        except OSError:
            logger.exception("Failed to save settings")
            self._toast_callback("error", "Persistence Error", "Could not save setting.")
        self.changed.emit()

    @Slot(str, bool)
    def updateAlertSetting(self, key: str, value: bool) -> None:
        self._alert_settings[key] = bool(value)
        try:
            self._save_callback()
        except OSError:
            logger.exception("Failed to save alert settings")
            self._toast_callback("error", "Persistence Error", "Could not save alert setting.")
        self.changed.emit()

    @Slot("QVariantMap")
    def updateReminderPreferences(self, preferences: dict[str, Any]) -> None:
        self._reminder_preferences = self._normalize_reminder_preferences(preferences)
        try:
            self._save_callback()
            self._on_reminders_changed()
            self._toast_callback("success", "Preferences Updated", "Reminder settings were saved.")
        except OSError:
            logger.exception("Failed to save reminder preferences")
            self._toast_callback(
                "error", "Persistence Error", "Could not save reminder preferences."
            )
        self.changed.emit()

    @Slot(str, str)
    def updateScheduleSetting(self, key: str, value: str) -> None:
        clean = str(value).strip()
        if key == "daily_time_minutes":
            try:
                parsed = max(15, min(720, int(clean)))
            except (TypeError, ValueError):
                parsed = 120
            clean = str(parsed)
        elif key == "preferred_time":
            try:
                hours, minutes = (int(p) for p in clean.split(":")[:2])
                clean = f"{hours:02d}:{minutes:02d}"
            except Exception:
                clean = "18:00"
        try:
            self._set_schedule_setting(key, clean)
            self._save_callback()
            self._toast_callback(
                "success", "Schedule Updated", "Planner timetable settings were updated."
            )
        except (SQLAlchemyError, OSError):
            logger.exception("Failed to persist schedule setting")
        self.changed.emit()

    @Slot()
    def saveSettings(self) -> None:
        try:
            self._save_callback()
            self._toast_callback("success", "Settings Saved", "Your preferences were saved.")
        except OSError:
            logger.exception("Failed to persist settings")
            self._toast_callback(
                "error", "Persistence Error", "Failed to write preferences to disk."
            )

    @Slot()
    def clearHistory(self) -> None:
        try:
            self._save_callback()
            self._toast_callback(
                "warning", "History Cleared", "Study history and notifications were cleared."
            )
        except OSError:
            logger.exception("Failed to clear history")
            self._toast_callback("error", "Error", "Failed to write updated state.")
        self.changed.emit()
