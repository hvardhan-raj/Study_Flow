from __future__ import annotations

import calendar
import logging
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from services import write_revision_calendar

logger = logging.getLogger(__name__)


class CalendarController(QObject):
    changed = Signal()

    def __init__(
        self,
        today_provider: Callable[[], date],
        tasks_provider: Callable[[], list[dict[str, Any]]],
        task_payload_provider: Callable[[dict[str, Any]], dict[str, Any]],
        on_notification_added: Callable[[str, str, str, str], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._today_provider = today_provider
        self._tasks_provider = tasks_provider
        self._task_payload_provider = task_payload_provider
        self._on_notification_added = on_notification_added or (lambda t, b, i, c: None)
        today_val = self._today_provider()
        self._selected_date = today_val
        self._calendar_view_date = today_val

    def set_today(self, current: date) -> None:
        if self._selected_date == self._calendar_view_date:
            self._selected_date = current
            self._calendar_view_date = current
            self.changed.emit()

    @Property(str, notify=changed)
    def selectedDate(self) -> str:
        return self._selected_date.isoformat()

    @Property(str, notify=changed)
    def selectedDateFormatted(self) -> str:
        today = self._today_provider()
        if self._selected_date == today:
            return f"Today, {self._selected_date.strftime('%B %d')}"
        if self._selected_date == today + timedelta(days=1):
            return f"Tomorrow, {self._selected_date.strftime('%B %d')}"
        if self._selected_date == today - timedelta(days=1):
            return f"Yesterday, {self._selected_date.strftime('%B %d')}"
        return self._selected_date.strftime("%A, %B %d")

    @Property(str, notify=changed)
    def calendarMonthLabel(self) -> str:
        return self._calendar_view_date.strftime("%B %Y")

    @Property("QVariantList", notify=changed)
    def selectedDaySessions(self) -> list[dict[str, Any]]:
        tasks = [
            task
            for task in self._tasks_provider()
            if task["scheduled_at"].date() == self._selected_date
        ]
        tasks.sort(key=lambda item: item["scheduled_at"])
        rows = []
        for task in tasks:
            payload = self._task_payload_provider(task)
            rows.append(
                {
                    "id": task["id"],
                    "topic": task["topic"],
                    "name": task["topic"],
                    "subject": task["subject"],
                    "duration": task["duration_minutes"],
                    "time": task["scheduled_at"].strftime("%H:%M"),
                    "durationText": f"{task['duration_minutes']} min",
                    "color": payload["subjectColor"],
                    "subjectColor": payload["subjectColor"],
                    "status": payload["status"],
                    "statusColor": payload["statusColor"],
                    "completed": task["completed"],
                }
            )
        return rows

    @Property(str, notify=changed)
    def selectedDayTotalText(self) -> str:
        return f"{sum(item['duration'] for item in self.selectedDaySessions)} min"

    @Property("QVariantList", notify=changed)
    def calendarDays(self) -> list[dict[str, Any]]:
        year = self._calendar_view_date.year
        month = self._calendar_view_date.month
        cal = calendar.Calendar(firstweekday=0)
        month_dates = cal.monthdatescalendar(year, month)
        all_dates = [d for week in month_dates for d in week]

        tasks = self._tasks_provider()
        by_date: dict[date, list[dict[str, Any]]] = {}
        for task in tasks:
            d = task["scheduled_at"].date()
            by_date.setdefault(d, []).append(task)

        today = self._today_provider()
        days_payload = []
        for current_date in all_dates:
            day_tasks = by_date.get(current_date, [])
            days_payload.append(
                {
                    "date": current_date.isoformat(),
                    "dayNumber": current_date.day,
                    "isCurrentMonth": current_date.month == month,
                    "isToday": current_date == today,
                    "isSelected": current_date == self._selected_date,
                    "taskCount": len(day_tasks),
                    "hasTasks": bool(day_tasks),
                    "isCompleted": bool(day_tasks) and all(t["completed"] for t in day_tasks),
                }
            )
        return days_payload

    @Slot(str)
    def selectDate(self, date_str: str) -> None:
        try:
            self._selected_date = date.fromisoformat(date_str)
            self._calendar_view_date = self._selected_date
            self.changed.emit()
        except ValueError:
            pass

    @Slot()
    def previousCalendarMonth(self) -> None:
        year = self._calendar_view_date.year
        month = self._calendar_view_date.month - 1
        if month < 1:
            month = 12
            year -= 1
        self._calendar_view_date = date(year, month, 1)
        self.changed.emit()

    @Slot()
    def nextCalendarMonth(self) -> None:
        year = self._calendar_view_date.year
        month = self._calendar_view_date.month + 1
        if month > 12:
            month = 1
            year += 1
        self._calendar_view_date = date(year, month, 1)
        self.changed.emit()

    @Slot(str, result=str)
    def exportCalendar(self, output_path: str | None = None) -> str:
        clean_path = (output_path or "").strip()
        if clean_path:
            target = Path(clean_path)
        else:
            from config.settings import settings

            target = settings.app_data_dir / "data" / "studyflow_revisions.ics"
        target.parent.mkdir(parents=True, exist_ok=True)
        open_tasks = [t for t in self._tasks_provider() if not t["completed"]]
        write_revision_calendar(open_tasks, target)
        self._on_notification_added(
            "Calendar Export Ready",
            f"Saved upcoming revision sessions to {target.name}.",
            "CAL",
            "#3B82F6",
        )
        return str(target)
