from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from threading import Event, Thread
from typing import Any

from PySide6.QtCore import QObject, Signal
from time_utils import local_now, naive_local_now

@dataclass(frozen=True)
class ReminderPreferences:
    enabled: bool = True
    notification_time: time = time(8, 0)
    minimum_due_for_alert: int = 1
    desktop_notifications: bool = False


class DesktopNotifier:
    def __init__(self, app_name: str = "StudyFlow") -> None:
        self.app_name = app_name

    def notify(self, title: str, message: str) -> bool:
        try:
            from plyer import notification
        except ImportError:
            return False

        notification.notify(title=title, message=message, app_name=self.app_name, timeout=8)
        return True


class ReminderScheduler(QObject):
    jobRequested = Signal()

    def __init__(
        self,
        job: Callable[[], None] | None = None,
        preferences: ReminderPreferences | None = None,
    ) -> None:
        super().__init__()
        self.job = job
        self.preferences = preferences or ReminderPreferences()
        self._stop_event = Event()
        self._thread: Thread | None = None
        if job is not None:
            self.jobRequested.connect(job)

    def start(self) -> None:
        if not self.preferences.enabled or self._thread is not None:
            return
        self._thread = Thread(target=self._run_loop, name="studyflow-reminders", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._thread = None

    def run_once(self) -> None:
        if self.preferences.enabled:
            self.jobRequested.emit()

    def next_run_at(self, now: datetime | None = None) -> datetime:
        current = now or local_now()
        run_at = datetime.combine(current.date(), self.preferences.notification_time, tzinfo=current.tzinfo)
        if run_at <= current:
            run_at += timedelta(days=1)
        return run_at

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            wait_seconds = max(1, int((self.next_run_at() - local_now()).total_seconds()))
            if self._stop_event.wait(wait_seconds):
                return
            self.run_once()


def build_morning_summary(
    due_today: list[dict[str, Any]],
    overdue: list[dict[str, Any]],
    minimum_due_for_alert: int = 1,
) -> dict[str, Any] | None:
    if len(due_today) < minimum_due_for_alert and not overdue:
        return None
    if overdue:
        return {
            "title": f"{len(overdue)} overdue review{'s' if len(overdue) != 1 else ''}",
            "body": "Start with overdue topics before opening new material.",
            "color": "#EF4444",
            "icon": "!",
        }
    return {
        "title": f"{len(due_today)} review{'s' if len(due_today) != 1 else ''} due today",
        "body": f"Begin with {due_today[0]['name']} to keep your recall schedule healthy.",
        "color": "#3B82F6",
        "icon": "T",
    }


def build_exam_warnings(topics: list[dict[str, Any]], today: date, warning_days: int = 14) -> list[dict[str, Any]]:
    warnings = []
    for topic in topics:
        raw_exam_date = topic.get("exam_date") or topic.get("examDate")
        if not raw_exam_date:
            continue
        try:
            exam_date = date.fromisoformat(raw_exam_date)
        except ValueError:
            continue
        days_until = (exam_date - today).days
        if 0 <= days_until <= warning_days:
            warnings.append(
                {
                    "title": f"{topic['name']} exam in {days_until} day{'s' if days_until != 1 else ''}",
                    "body": f"Prioritize {topic['subject']} review blocks this week.",
                    "color": "#F59E0B",
                    "icon": "E",
                }
            )
    return warnings


def write_revision_calendar(tasks: list[dict[str, Any]], output_path: Path, now: datetime | None = None) -> Path:
    timestamp = (now or naive_local_now()).strftime("%Y%m%dT%H%M%S")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StudyFlow//Smart Study Schedule//EN",
        "CALSCALE:GREGORIAN",
    ]
    for task in sorted(tasks, key=lambda item: item["scheduled_at"]):
        if task.get("completed_at"):
            continue
        starts_at = task["scheduled_at"]
        ends_at = starts_at + timedelta(minutes=int(task.get("duration_minutes", 25)))
        uid = f"{task['id']}@studyflow.local"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{timestamp}",
                f"DTSTART:{starts_at.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{ends_at.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:StudyFlow revision - {_escape_ics(task['topic'])}",
                f"DESCRIPTION:{_escape_ics(task['subject'])} | {task['difficulty']} | Confidence {task['confidence']}/5",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return output_path


def _escape_ics(value: str) -> str:
    return value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
