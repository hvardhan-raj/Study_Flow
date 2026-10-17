from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, time, timedelta
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from services import DesktopNotifier
from studyflow_backend.defaults import build_default_notifications
from time_utils import ensure_local_timezone, local_now

logger = logging.getLogger(__name__)


class NotificationsController(QObject):
    changed = Signal()

    def __init__(
        self,
        desktop_notifier: DesktopNotifier | None = None,
        save_callback: Callable[[], None] | None = None,
        today_provider: Callable[[], Any] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._desktop_notifier = desktop_notifier or DesktopNotifier()
        self._save_callback = save_callback or (lambda: None)
        self._today_provider = today_provider or local_now
        self._notifications: list[dict[str, Any]] = []
        self._toasts: list[dict[str, Any]] = []

    def initialize_state(self, notifications: list[dict[str, Any]] | None) -> None:
        raw_notifications = (
            notifications if notifications is not None else build_default_notifications()
        )
        self._notifications = [
            self._normalize_notification(item, idx) for idx, item in enumerate(raw_notifications)
        ]

    @property
    def notifications_payload(self) -> list[dict[str, Any]]:
        return list(self._notifications)

    def _notification_timestamp(self, index: int) -> datetime:
        today_val = getattr(self._today_provider(), "date", lambda: self._today_provider())()
        return datetime.combine(today_val, time(12, 0), tzinfo=local_now().tzinfo) - timedelta(
            minutes=index
        )

    def _relative_time_label(self, timestamp: datetime) -> str:
        delta = local_now() - ensure_local_timezone(timestamp)
        if delta.days > 0:
            return "Yesterday" if delta.days == 1 else f"{delta.days}d ago"
        minutes = max(0, round(delta.total_seconds() / 60))
        if minutes < 1:
            return "Now"
        if minutes < 60:
            return f"{minutes}m ago"
        return f"{minutes // 60}h ago"

    def _normalize_icon_name(self, icon: str | None) -> str:
        value = str(icon or "").strip().lower()
        aliases = {
            "!": "alert",
            "t": "calendar",
            "r": "report",
            "ok": "check",
            "ai": "spark",
            "cal": "calendar",
            "play_arrow": "play",
            "stop": "stop",
            "check_circle": "check",
            "refresh": "refresh",
        }
        return aliases.get(value, value or "info")

    def _normalize_notification(
        self, notification: dict[str, Any], index: int = 0
    ) -> dict[str, Any]:
        item = dict(notification) if isinstance(notification, dict) else {}
        timestamp = item.get("timestamp")
        try:
            parsed_timestamp = (
                datetime.fromisoformat(timestamp)
                if isinstance(timestamp, str)
                else self._notification_timestamp(index)
            )
        except ValueError:
            parsed_timestamp = self._notification_timestamp(index)
        item.setdefault("id", f"notif-{index + 1}")
        item.setdefault("title", "StudyFlow Alert")
        item.setdefault("body", "")
        item["icon"] = self._normalize_icon_name(item.get("icon", "info"))
        item.setdefault("color", "#3B82F6")
        item["read"] = bool(item.get("read", False))
        item["timestamp"] = ensure_local_timezone(parsed_timestamp).isoformat()
        item["time"] = self._relative_time_label(parsed_timestamp)
        return item

    def _build_toast(self, level: str, title: str, message: str) -> dict[str, Any]:
        tone = {
            "success": {"color": "#10B981", "icon": "check"},
            "error": {"color": "#EF4444", "icon": "alert"},
            "info": {"color": "#3B82F6", "icon": "info"},
            "warning": {"color": "#F59E0B", "icon": "alert"},
        }.get(level, {"color": "#3B82F6", "icon": "info"})
        return {
            "id": f"toast-{local_now().timestamp():.6f}",
            "level": level,
            "title": title,
            "message": message,
            "color": tone["color"],
            "icon": tone["icon"],
            "duration": 3600,
        }

    def show_toast(self, level: str, title: str, message: str) -> None:
        self._toasts.insert(0, self._build_toast(level, title, message))
        self._toasts = self._toasts[:6]
        self.changed.emit()

    def add_notification(self, title: str, body: str, icon: str, color: str) -> None:
        self._notifications.insert(
            0,
            self._normalize_notification(
                {"title": title, "body": body, "icon": icon, "color": color}
            ),
        )
        self._notifications = self._notifications[:50]
        self._save_callback()
        self.changed.emit()

    def upsert_automated_notification(
        self,
        notification_id: str,
        title: str,
        body: str,
        icon: str,
        color: str,
        *,
        read: bool = False,
        desktop: bool = False,
    ) -> bool:
        existing = next(
            (item for item in self._notifications if item["id"] == notification_id), None
        )
        if existing:
            existing.update(
                {
                    "title": title,
                    "body": body,
                    "icon": self._normalize_icon_name(icon),
                    "color": color,
                    "read": read,
                }
            )
        else:
            self._notifications.insert(
                0,
                self._normalize_notification(
                    {
                        "id": notification_id,
                        "title": title,
                        "body": body,
                        "icon": icon,
                        "color": color,
                        "read": read,
                    }
                ),
            )
            self._notifications = self._notifications[:50]
            self._save_callback()
            self.changed.emit()
            if desktop:
                try:
                    self._desktop_notifier.notify(title, body)
                except Exception:
                    logger.exception("Failed to dispatch desktop notification")
            return True
        return False

    @Property("QVariantList", notify=changed)
    def notifications(self) -> list[dict[str, Any]]:
        return self._notifications

    @Property(int, notify=changed)
    def notificationBadgeCount(self) -> int:
        return sum(1 for item in self._notifications if not item.get("read", False))

    @Property("QVariantList", notify=changed)
    def toasts(self) -> list[dict[str, Any]]:
        return self._toasts

    @Slot(str)
    def dismissToast(self, toast_id: str) -> None:
        before = len(self._toasts)
        self._toasts = [toast for toast in self._toasts if toast.get("id") != toast_id]
        if len(self._toasts) != before:
            self.changed.emit()

    @Slot()
    def clearAllNotifications(self) -> None:
        self._notifications = []
        self._save_callback()
        self.changed.emit()

    @Slot(str)
    def markNotificationRead(self, notification_id: str) -> None:
        for notification in self._notifications:
            if notification.get("id") == notification_id:
                notification["read"] = True
                self._save_callback()
                self.changed.emit()
                break
