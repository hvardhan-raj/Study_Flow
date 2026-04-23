from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .models import SubjectMeta


def difficulty_color(difficulty: str) -> str:
    return {"Easy": "#10B981", "Medium": "#F59E0B", "Hard": "#EF4444"}.get(difficulty, "#64748B")


def format_schedule_text(today: date, scheduled_at: datetime) -> str:
    scheduled_day = scheduled_at.date()
    if scheduled_day < today:
        days = (today - scheduled_day).days
        return "Overdue" if days == 1 else f"Overdue by {days}d"
    if scheduled_day == today:
        return f"Today {scheduled_at.strftime('%H:%M')}"
    if scheduled_day.toordinal() == today.toordinal() + 1:
        return f"Tomorrow {scheduled_at.strftime('%H:%M')}"
    return scheduled_at.strftime("%a %H:%M")


def task_payload(today: date, subject_meta: SubjectMeta, task: dict[str, Any]) -> dict[str, Any]:
    if task["completed_at"]:
        status = "Done"
        color = "#10B981"
    elif task["scheduled_at"].date() < today:
        status = "Overdue"
        color = "#EF4444"
    elif task["scheduled_at"].date() == today:
        status = "Pending"
        color = "#F59E0B"
    else:
        status = "Upcoming"
        color = "#3B82F6"

    return {
        "id": task["id"],
        "topic": task["topic"],
        "name": task["topic"],
        "subject": task["subject"],
        "subjectShort": "Maths" if task["subject"] == "Mathematics" else task["subject"],
        "difficulty": task["difficulty"],
        "time": f"{task['duration_minutes']}m",
        "status": status,
        "scheduledText": format_schedule_text(today, task["scheduled_at"]),
        "subjectColor": subject_meta.color,
        "difficultyColor": difficulty_color(task["difficulty"]),
        "statusColor": color,
        "confidence": task["confidence"],
        "scheduledDate": task["scheduled_at"].date().isoformat(),
        "durationMinutes": task["duration_minutes"],
    }
