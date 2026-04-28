from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from typing import Any

from .models import SubjectMeta

SUBJECTS: dict[str, SubjectMeta] = {
    "General Aptitude": SubjectMeta("GA", "#EF4444"),
    "Engineering Mathematics": SubjectMeta("EM", "#3B82F6"),
    "Digital Logic": SubjectMeta("DL", "#8B5CF6"),
    "Computer Organization and Architecture": SubjectMeta("COA", "#10B981"),
    "Programming and Data Structures": SubjectMeta("DS", "#F59E0B"),
    "Algorithms": SubjectMeta("AL", "#14B8A6"),
    "Theory of Computation": SubjectMeta("TOC", "#A855F7"),
    "Compiler Design": SubjectMeta("CD", "#EC4899"),
    "Operating Systems": SubjectMeta("OS", "#F97316"),
    "Databases": SubjectMeta("DBMS", "#22C55E"),
    "Computer Networks": SubjectMeta("CN", "#06B6D4"),
}

TOPIC_LIBRARY: list[dict[str, Any]] = [
    {"subject": "General Aptitude", "name": "Verbal Ability", "difficulty": "Easy", "progress": 78, "confidence": 4},
    {"subject": "General Aptitude", "name": "Quantitative Aptitude", "difficulty": "Medium", "progress": 66, "confidence": 3},
    {"subject": "Engineering Mathematics", "name": "Linear Algebra", "difficulty": "Medium", "progress": 62, "confidence": 3},
    {"subject": "Engineering Mathematics", "name": "Calculus", "difficulty": "Hard", "progress": 45, "confidence": 2},
    {"subject": "Engineering Mathematics", "name": "Discrete Mathematics", "difficulty": "Hard", "progress": 50, "confidence": 2},
    {"subject": "Digital Logic", "name": "Boolean Algebra", "difficulty": "Easy", "progress": 85, "confidence": 5},
    {"subject": "Digital Logic", "name": "Combinational Circuits", "difficulty": "Medium", "progress": 70, "confidence": 4},
    {"subject": "Digital Logic", "name": "Sequential Circuits", "difficulty": "Medium", "progress": 58, "confidence": 3},
    {"subject": "Computer Organization and Architecture", "name": "Pipelining", "difficulty": "Hard", "progress": 40, "confidence": 2},
    {"subject": "Computer Organization and Architecture", "name": "Cache Memory", "difficulty": "Hard", "progress": 36, "confidence": 2},
    {"subject": "Computer Organization and Architecture", "name": "Instruction Set Architecture", "difficulty": "Medium", "progress": 55, "confidence": 3},
    {"subject": "Programming and Data Structures", "name": "Arrays and Strings", "difficulty": "Easy", "progress": 88, "confidence": 5},
    {"subject": "Programming and Data Structures", "name": "Stacks and Queues", "difficulty": "Medium", "progress": 74, "confidence": 4},
    {"subject": "Programming and Data Structures", "name": "Trees and Graphs", "difficulty": "Hard", "progress": 48, "confidence": 2},
    {"subject": "Algorithms", "name": "Sorting and Searching", "difficulty": "Medium", "progress": 72, "confidence": 4},
    {"subject": "Algorithms", "name": "Greedy Algorithms", "difficulty": "Hard", "progress": 43, "confidence": 2},
    {"subject": "Algorithms", "name": "Dynamic Programming", "difficulty": "Hard", "progress": 38, "confidence": 2},
    {"subject": "Theory of Computation", "name": "Finite Automata", "difficulty": "Medium", "progress": 60, "confidence": 3},
    {"subject": "Theory of Computation", "name": "Regular Languages", "difficulty": "Easy", "progress": 76, "confidence": 4},
    {"subject": "Theory of Computation", "name": "Turing Machines", "difficulty": "Hard", "progress": 41, "confidence": 2},
    {"subject": "Compiler Design", "name": "Lexical Analysis", "difficulty": "Medium", "progress": 57, "confidence": 3},
    {"subject": "Compiler Design", "name": "Parsing", "difficulty": "Hard", "progress": 34, "confidence": 2},
    {"subject": "Compiler Design", "name": "Intermediate Code Generation", "difficulty": "Hard", "progress": 30, "confidence": 1},
    {"subject": "Operating Systems", "name": "Process Scheduling", "difficulty": "Medium", "progress": 68, "confidence": 4},
    {"subject": "Operating Systems", "name": "Deadlocks", "difficulty": "Hard", "progress": 44, "confidence": 2},
    {"subject": "Operating Systems", "name": "Memory Management", "difficulty": "Hard", "progress": 39, "confidence": 2},
    {"subject": "Databases", "name": "ER Model", "difficulty": "Easy", "progress": 82, "confidence": 5},
    {"subject": "Databases", "name": "SQL Queries", "difficulty": "Medium", "progress": 73, "confidence": 4},
    {"subject": "Databases", "name": "Normalization", "difficulty": "Hard", "progress": 46, "confidence": 2},
    {"subject": "Computer Networks", "name": "OSI Model", "difficulty": "Medium", "progress": 64, "confidence": 3},
    {"subject": "Computer Networks", "name": "TCP/IP", "difficulty": "Medium", "progress": 61, "confidence": 3},
    {"subject": "Computer Networks", "name": "Routing", "difficulty": "Hard", "progress": 42, "confidence": 2},
]


def default_settings() -> dict[str, Any]:
    return {
        "scheduling": {
            "algorithm": "SM-2 (Spaced Repetition)",
            "daily_goal": "2 hours",
            "session_length": "25 min (Pomodoro)",
            "weekend_sessions": False,
        },
        "ai": {
            "model": "Local study assistant",
            "suggestions": True,
            "auto_reschedule": False,
        },
        "appearance": {"theme": "Light", "font_size": "Medium", "compact_ui": False},
        "notifications": {"push_alerts": True, "email_digest": False, "reminder_before": "30 minutes"},
        "data": {"export": "CSV / JSON", "backup": "Local only"},
    }


def default_alert_settings() -> dict[str, bool]:
    return {
        "due_today": True,
        "overdue": True,
        "ai_suggestions": True,
        "weekly_reports": True,
        "session_reminders": False,
        "streak_reminders": False,
    }


def default_study_minutes() -> list[int]:
    return [25, 48, 30, 62, 40, 55, 38, 72, 46, 58, 34, 66, 41, 60]


def default_topics() -> list[dict[str, Any]]:
    return deepcopy(TOPIC_LIBRARY)


def build_default_tasks(today: date) -> list[dict[str, Any]]:
    rows = [
        ("task-1", "Boolean Algebra", "Digital Logic", "Easy", today, time(9, 0), 5),
        ("task-2", "Arrays and Strings", "Programming and Data Structures", "Easy", today, time(11, 0), 5),
        ("task-3", "Process Scheduling", "Operating Systems", "Medium", today, time(14, 0), 4),
        ("task-4", "SQL Queries", "Databases", "Medium", today - timedelta(days=2), time(16, 0), 4),
        ("task-5", "Linear Algebra", "Engineering Mathematics", "Medium", today + timedelta(days=1), time(10, 0), 3),
        ("task-6", "Sorting and Searching", "Algorithms", "Medium", today + timedelta(days=1), time(15, 30), 4),
        ("task-7", "Finite Automata", "Theory of Computation", "Medium", today + timedelta(days=2), time(10, 0), 3),
        ("task-8", "Cache Memory", "Computer Organization and Architecture", "Hard", today + timedelta(days=2), time(16, 0), 2),
        ("task-9", "Deadlocks", "Operating Systems", "Hard", today + timedelta(days=3), time(12, 0), 2),
        ("task-10", "Normalization", "Databases", "Hard", today + timedelta(days=4), time(17, 0), 2),
        ("task-11", "TCP/IP", "Computer Networks", "Medium", today + timedelta(days=5), time(8, 0), 3),
        ("task-12", "Dynamic Programming", "Algorithms", "Hard", today + timedelta(days=6), time(9, 30), 2),
    ]
    return [
        {
            "id": task_id,
            "topic": topic,
            "subject": subject,
            "difficulty": difficulty,
            "scheduled_at": datetime.combine(day, slot),
            "confidence": confidence,
            "status": "pending",
            "duration_minutes": {"Easy": 15, "Medium": 25, "Hard": 35}[difficulty],
            "completed_at": None,
        }
        for task_id, topic, subject, difficulty, day, slot, confidence in rows
    ]

def build_default_notifications() -> list[dict[str, Any]]:
    return [
        {
            "id": "notif-1",
            "icon": "!",
            "title": "Overdue: Deadlocks",
            "body": "This topic slipped by two days. Review it before starting something new.",
            "time": "2h ago",
            "read": False,
            "color": "#EF4444",
        },
        {
            "id": "notif-2",
            "icon": "T",
            "title": "Reminder: SQL Queries",
            "body": "Your next revision starts in 30 minutes.",
            "time": "30m ago",
            "read": False,
            "color": "#F59E0B",
        },
        {
            "id": "notif-3",
            "icon": "AI",
            "title": "AI Suggestion",
            "body": "Move Dynamic Programming earlier for better recall based on recent sessions.",
            "time": "1h ago",
            "read": False,
            "color": "#3B82F6",
        },
        {
            "id": "notif-4",
            "icon": "OK",
            "title": "Session Complete",
            "body": "You finished Process Scheduling and rated the session 4 out of 5.",
            "time": "3h ago",
            "read": True,
            "color": "#10B981",
        },
        {
            "id": "notif-5",
            "icon": "R",
            "title": "Weekly Report Ready",
            "body": "Your study report is ready to review.",
            "time": "Yesterday",
            "read": True,
            "color": "#8B5CF6",
        },
    ]
