from __future__ import annotations

import csv
import logging
from colorsys import hls_to_rgb
from datetime import date, datetime, time, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QMetaObject, Qt, Signal, Slot
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from config.settings import settings
from db.session import create_session_factory, create_sqlite_engine, init_database, session_scope
from llm import AssistantContext, LLMService
from models import AppSetting, ConfidenceRating, DifficultyLevel, Revision, StudySession, Subject, Topic
from nlp import NLPService, load_training_examples, train_model
from services import (
    DesktopNotifier,
    ReminderPreferences,
    SchedulerService,
    SubjectService,
    TopicService,
    build_exam_warnings,
    build_morning_summary,
    write_revision_calendar,
)

from .defaults import build_default_notifications, default_alert_settings
from .ml_engine import LearningMLEngine
from .models import SubjectMeta
from .presenters import difficulty_color, task_payload
from .storage import load_state, save_state
from .viewmodels import StudyFlowReadModel

logger = logging.getLogger(__name__)

CONFIDENCE_MAX = 5
RATING_LABELS = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
RATING_TO_PROGRESS = {1: -6, 2: 2, 3: 6, 4: 10}
DIFFICULTY_TO_DURATION = {"Easy": 15, "Medium": 30, "Hard": 45}
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


def _rating_from_int(value: int) -> ConfidenceRating:
    return {
        1: ConfidenceRating.AGAIN,
        2: ConfidenceRating.HARD,
        3: ConfidenceRating.GOOD,
        4: ConfidenceRating.EASY,
    }[max(1, min(int(value), 4))]


def seed_defaults(db: Session) -> None:
    if db.query(Subject.id).first() is not None:
        return

    subject_service = SubjectService(db)
    topic_service = TopicService(db, scheduler=SchedulerService(db))
    seeds = [
        ("Mathematics", "#3B82F6", [("Calculus", DifficultyLevel.HARD, 42), ("Linear Algebra", DifficultyLevel.MEDIUM, 64)]),
        ("Physics", "#10B981", [("Kinematics", DifficultyLevel.MEDIUM, 58), ("Magnetism", DifficultyLevel.HARD, 36)]),
        ("History", "#F59E0B", [("Roman Empire", DifficultyLevel.MEDIUM, 71), ("World War I", DifficultyLevel.HARD, 47)]),
    ]
    for subject_name, color, topics in seeds:
        subject = subject_service.create_subject(name=subject_name, color_tag=color)
        for topic_name, difficulty, progress in topics:
            topic = topic_service.create_topic(subject_id=subject.id, name=topic_name, difficulty=difficulty)
            topic.mastery_score = float(progress)


class StudyFlowBackend(QObject):
    stateChanged = Signal()
    intelligenceChanged = Signal()

    def __init__(self, store_path: Path | None = None, database_path: Path | None = None) -> None:
        super().__init__()
        self._store_path = store_path or Path(__file__).resolve().parent.parent / "studyflow_data.json"
        self._database_path = Path(database_path) if database_path is not None else self._resolve_database_path(self._store_path)
        self._engine = create_sqlite_engine(database_path=self._database_path)
        self._session_factory = create_session_factory(self._engine)
        init_database(engine_override=self._engine, database_path=self._database_path)
        self._today_provider = date.today
        self._today_value = self._today_provider()
        self._selected_date = self._today_value
        self._calendar_view_date = self._today_value
        self._task_filter = "all"
        self._curriculum_filter = "All"
        self._curriculum_search = ""
        self._desktop_notifier = DesktopNotifier()
        self._llm_service = LLMService()
        self._assistant_status = self._llm_service.status()
        self._nlp_service = NLPService()
        self._bootstrap_nlp_model()
        self._load_json_state()
        self._view_model = StudyFlowReadModel(
            db_factory=self._db,
            today_provider=lambda: self._today,
            curriculum_filter_provider=lambda: self._curriculum_filter,
            curriculum_search_provider=lambda: self._curriculum_search,
            study_minutes_provider=lambda: list(self._study_minutes),
        )
        self._ensure_database_ready()
        self._ml_engine = LearningMLEngine(
            session_factory=self._session_factory,
            today_provider=lambda: self._today,
            model_path=Path(__file__).resolve().parent.parent / "models" / "learning_model.pkl",
            on_update=self._queue_intelligence_refresh,
        )
        self._ml_engine.start()
        self._refresh_reminder_notifications()

    def _db(self):
        return session_scope(self._session_factory)

    def _scheduler(self, db: Session) -> SchedulerService:
        return SchedulerService(db, today_provider=lambda: self._today)

    def _get_schedule_setting(self, key: str) -> str:
        default = DEFAULT_SCHEDULE_SETTINGS[key]
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

    def _set_schedule_setting(self, key: str, value: str) -> None:
        with self._db() as db:
            setting = db.get(AppSetting, key)
            if setting is None:
                setting = AppSetting(key=key, value=value)
                db.add(setting)
            else:
                setting.value = value
            db.flush()
            self._scheduler(db).rebalance_schedule()

    def _resolve_database_path(self, store_path: Path) -> Path:
        if store_path.name.endswith("_state.json"):
            return store_path.with_suffix(".sqlite3")
        return settings.database_path

    def _ensure_database_ready(self) -> None:
        with self._db() as db:
            leaked_topics = list(db.scalars(select(Topic).where(Topic.name.like("Dashboard Upcoming Seed%"))))
            if leaked_topics:
                for topic in leaked_topics:
                    db.delete(topic)
                logger.warning("Removed %s leaked dashboard test topic(s) from %s", len(leaked_topics), self._database_path)
            seed_defaults(db)

    def _load_json_state(self) -> None:
        try:
            state = load_state(self._store_path)
        except Exception:
            logger.exception("Failed to initialize persisted StudyFlow state from %s", self._store_path)
            state = {
                "settings": {},
                "alert_settings": {},
                "reminder_preferences": {},
                "assistant_messages": [],
                "suggestion_dismissed": False,
                "study_minutes": [],
                "notifications": build_default_notifications(),
            }

        self._settings = self._normalize_settings(state.get("settings", {}))
        self._alert_settings = self._normalize_alert_settings(state.get("alert_settings", {}))
        self._reminder_preferences = self._normalize_reminder_preferences(state.get("reminder_preferences", {}))
        assistant_messages = state.get("assistant_messages") or self._default_assistant_messages()
        self._assistant_messages = [self._normalize_assistant_message(message) for message in assistant_messages]
        self._suggestion_dismissed = bool(state.get("suggestion_dismissed", False))
        self._study_minutes = list(state.get("study_minutes", []))
        self._active_session = self._normalize_active_session(state.get("active_session"))
        self._notifications = [
            self._normalize_notification(notification, index)
            for index, notification in enumerate(state.get("notifications", build_default_notifications()))
        ]
        self._toasts: list[dict[str, Any]] = []

    def _save(self) -> None:
        save_state(
            self._store_path,
            {
                "settings": self._settings,
                "alert_settings": self._alert_settings,
                "reminder_preferences": self._reminder_preferences,
                "assistant_messages": self._assistant_messages,
                "suggestion_dismissed": self._suggestion_dismissed,
                "study_minutes": self._study_minutes,
                "active_session": self._active_session,
                "notifications": self._notifications,
            },
        )

    def _emit(self) -> None:
        self.stateChanged.emit()

    @Slot()
    def _emit_intelligence_changed(self) -> None:
        self.intelligenceChanged.emit()

    def _queue_intelligence_refresh(self) -> None:
        QMetaObject.invokeMethod(self, "_emit_intelligence_changed", Qt.ConnectionType.QueuedConnection)

    def _request_intelligence_refresh(self, *, train: bool = False) -> None:
        self._ml_engine.request_refresh(train=train)

    def _mark_revision_completed_for_intelligence(self) -> None:
        self._ml_engine.mark_revision_completed()

    @Slot()
    def shutdown(self) -> None:
        self._ml_engine.stop()

    @Slot()
    def refreshIntelligence(self) -> None:
        self._request_intelligence_refresh(train=not self._ml_engine.get_intelligence_dashboard().get("model_ready", False))

    @property
    def _today(self) -> date:
        return self._current_today()

    def _current_today(self) -> date:
        current = self._today_provider()
        previous = self._today_value
        if current == previous:
            return current
        if self._selected_date == previous:
            self._selected_date = current
        if self._calendar_view_date == previous:
            self._calendar_view_date = current
        self._today_value = current
        return current

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
        if not isinstance(payload["notification_time"], str) or ":" not in payload["notification_time"]:
            payload["notification_time"] = "08:00"
        return payload

    def _normalize_active_session(self, active_session: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(active_session, dict):
            return None
        session_id = active_session.get("id")
        started_at = active_session.get("started_at")
        topic = active_session.get("topic", "")
        subject = active_session.get("subject", "")
        try:
            parsed_id = int(session_id)
            parsed_started_at = datetime.fromisoformat(str(started_at))
        except (TypeError, ValueError):
            return None
        return {
            "id": parsed_id,
            "started_at": parsed_started_at.isoformat(),
            "topic": str(topic or ""),
            "subject": str(subject or ""),
        }

    def _active_session_payload(self) -> dict[str, Any]:
        active_session = self._active_session
        if active_session is None:
            return {
                "active": False,
                "label": "Start Session",
                "detail": "No active study session",
                "topic": "",
                "subject": "",
                "elapsedMinutes": 0,
                "elapsedSeconds": 0,
                "startedAt": "",
                "timerText": "00:00:00",
            }
        started_at = datetime.fromisoformat(active_session["started_at"])
        elapsed_seconds = max(0, round((datetime.now() - started_at).total_seconds()))
        elapsed_minutes = max(0, elapsed_seconds // 60)
        topic = active_session.get("topic", "")
        subject = active_session.get("subject", "")
        detail = f"{elapsed_minutes} min on {topic}" if topic else f"{elapsed_minutes} min active"
        if subject:
            detail += f" ({subject})"
        return {
            "active": True,
            "label": "End Session",
            "detail": detail,
            "topic": topic,
            "subject": subject,
            "elapsedMinutes": elapsed_minutes,
            "elapsedSeconds": elapsed_seconds,
            "startedAt": started_at.isoformat(),
            "timerText": f"{elapsed_seconds // 3600:02d}:{(elapsed_seconds % 3600) // 60:02d}:{elapsed_seconds % 60:02d}",
        }

    def _notification_timestamp(self, index: int) -> datetime:
        return datetime.combine(self._today, time(12, 0)) - timedelta(minutes=index)

    def _relative_time_label(self, timestamp: datetime) -> str:
        delta = datetime.now() - timestamp
        if delta.days > 0:
            return "Yesterday" if delta.days == 1 else f"{delta.days}d ago"
        minutes = max(0, round(delta.total_seconds() / 60))
        if minutes < 1:
            return "Now"
        if minutes < 60:
            return f"{minutes}m ago"
        return f"{minutes // 60}h ago"

    def _normalize_notification(self, notification: dict[str, Any], index: int = 0) -> dict[str, Any]:
        item = dict(notification) if isinstance(notification, dict) else {}
        timestamp = item.get("timestamp")
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else self._notification_timestamp(index)
        except ValueError:
            parsed_timestamp = self._notification_timestamp(index)
        item.setdefault("id", f"notif-{index + 1}")
        item.setdefault("title", "StudyFlow Alert")
        item.setdefault("body", "")
        item["icon"] = self._normalize_icon_name(item.get("icon", "info"))
        item.setdefault("color", "#3B82F6")
        item["read"] = bool(item.get("read", False))
        item["timestamp"] = parsed_timestamp.isoformat()
        item["time"] = self._relative_time_label(parsed_timestamp)
        return item

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

    def _build_toast(self, level: str, title: str, message: str) -> dict[str, Any]:
        tone = {
            "success": {"color": "#10B981", "icon": "check"},
            "error": {"color": "#EF4444", "icon": "alert"},
            "info": {"color": "#3B82F6", "icon": "info"},
            "warning": {"color": "#F59E0B", "icon": "alert"},
        }.get(level, {"color": "#3B82F6", "icon": "info"})
        return {
            "id": f"toast-{datetime.now().timestamp():.6f}",
            "level": level,
            "title": title,
            "message": message,
            "color": tone["color"],
            "icon": tone["icon"],
            "duration": 3600,
        }

    def _show_toast(self, level: str, title: str, message: str) -> None:
        self._toasts.insert(0, self._build_toast(level, title, message))
        self._toasts = self._toasts[:6]
        self._emit()

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        color = value.strip().lstrip("#")
        if len(color) != 6:
            return (59, 130, 246)
        return tuple(int(color[index:index + 2], 16) for index in range(0, 6, 2))

    def _subject_color_distance(self, left: str, right: str) -> float:
        left_rgb = self._hex_to_rgb(left)
        right_rgb = self._hex_to_rgb(right)
        return sum((left_rgb[index] - right_rgb[index]) ** 2 for index in range(3)) ** 0.5

    def _generate_subject_color(self) -> str:
        with self._db() as db:
            existing = [
                str(color)
                for color in db.scalars(select(Subject.color).where(func.coalesce(Subject.archived, 0) == 0))
                if color
            ]
        if not existing:
            existing = []
        for step in range(1, 360):
            hue = ((step * 137.508) % 360) / 360.0
            red, green, blue = hls_to_rgb(hue, 0.80, 0.52)
            candidate = "#{:02X}{:02X}{:02X}".format(round(red * 255), round(green * 255), round(blue * 255))
            if all(self._subject_color_distance(candidate, current) >= 28 for current in existing):
                return candidate
        return "#A7C5FF"

    def _default_assistant_messages(self) -> list[dict[str, Any]]:
        return [self._normalize_assistant_message({"role": "assistant", "text": "I can help you plan today’s reviews.", "source": "system"})]

    def _normalize_assistant_message(self, message: dict[str, Any]) -> dict[str, Any]:
        item = dict(message)
        item.setdefault("role", "assistant")
        item.setdefault("text", "")
        item.setdefault("source", "offline")
        timestamp = item.get("timestamp")
        if isinstance(timestamp, datetime):
            parsed_timestamp = timestamp
        elif isinstance(timestamp, str):
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                parsed_timestamp = datetime.now()
        else:
            parsed_timestamp = datetime.now()
        item["timestamp"] = parsed_timestamp.isoformat()
        item["time"] = parsed_timestamp.strftime("%H:%M")
        return item

    def _bootstrap_nlp_model(self) -> None:
        if self._nlp_service.model_path.exists():
            return
        dataset_path = Path(__file__).resolve().parent.parent / "nlp" / "data" / "training.csv"
        if dataset_path.exists():
            train_model(load_training_examples(dataset_path), service=self._nlp_service)

    def _subject_meta(self, subject: Subject | None = None, *, name: str = "", color: str = "#64748B") -> SubjectMeta:
        return self._view_model.subject_meta(subject, name=name, color=color)

    def _difficulty_label(self, difficulty: DifficultyLevel) -> str:
        return self._view_model.difficulty_label(difficulty)

    def _progress_for_topic(self, topic: Topic) -> int:
        return self._view_model.progress_for_topic(topic)

    def _confidence_for_topic(self, topic: Topic) -> int:
        return self._view_model.confidence_for_topic(topic)

    def _scheduled_datetime(self, revision: Revision) -> datetime:
        return revision.due_at

    def _serialize_topic(self, topic: Topic) -> dict[str, Any]:
        return self._view_model.serialize_topic(topic)

    def _serialize_task(self, revision: Revision) -> dict[str, Any]:
        return self._view_model.serialize_task(revision)
    def _all_topics(self) -> list[dict[str, Any]]:
        return self._view_model.all_topics()

    def _all_revisions(self) -> list[Revision]:
        return self._view_model.all_revisions()

    @property
    def _topics(self) -> list[dict[str, Any]]:
        return self._all_topics()

    @property
    def _tasks(self) -> list[dict[str, Any]]:
        return [self._serialize_task(revision) for revision in self._all_revisions()]

    def _open_task_rows(self) -> list[dict[str, Any]]:
        return [task for task in self._tasks if not task["completed"]]

    def _is_task_completed(self, task: dict[str, Any]) -> bool:
        return bool(task.get("completed"))

    def _task_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        return self._view_model.task_payload(task)

    def _task_bucket(self, task: dict[str, Any]) -> str:
        return self._view_model.task_bucket(task)

    def _compute_urgency_score(self, task: dict[str, Any]) -> int:
        days_delta = (task["scheduled_at"].date() - self._today).days
        difficulty_weight = {"Easy": 8, "Medium": 16, "Hard": 24}.get(task["difficulty"], 10)
        confidence_penalty = max(0, 6 - int(task["confidence"])) * 5
        overdue_bonus = 0 if days_delta >= 0 else abs(days_delta) * 30
        due_today_bonus = 18 if days_delta == 0 else 0
        upcoming_decay = max(0, 12 - max(days_delta, 0) * 3)
        return difficulty_weight + confidence_penalty + overdue_bonus + due_today_bonus + upcoming_decay

    def _dashboard_task_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        return self._view_model.dashboard_task_payload(task)

    def _tasks_for_bucket(self, bucket: str) -> list[dict[str, Any]]:
        return self._view_model.tasks_for_bucket(bucket)

    def _filtered_topics(self) -> list[dict[str, Any]]:
        return self._view_model.filtered_topics()

    def _subject_groups(self) -> dict[str, list[dict[str, Any]]]:
        return self._view_model.subject_groups()

    def _average_progress(self, topics: list[dict[str, Any]] | None = None) -> float:
        return self._view_model.average_progress(topics)

    def _average_confidence_pct(self, topics: list[dict[str, Any]] | None = None) -> int:
        return self._view_model.average_confidence_pct(topics)

    def _weekly_study_minutes(self) -> int:
        return self._view_model.weekly_study_minutes()

    def _study_trend_values(self, days: int = 14) -> list[int]:
        return self._view_model.study_trend_values(days)

    def _topic_tree_node(self, topic: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
        children = [self._topic_tree_node(candidate, lookup) for candidate in lookup.values() if candidate.get("parent_topic_id") == topic["id"]]
        children.sort(key=lambda item: item["name"])
        return {
            "id": topic["id"],
            "name": topic["name"],
            "subject": topic["subject"],
            "subjectId": topic["subjectId"],
            "difficulty": topic["difficulty"],
            "difficultyColor": topic["difficultyColor"],
            "progress": topic["progress"],
            "confidence": topic["confidence"],
            "notes": topic["notes"],
            "examDate": topic["examDate"],
            "completionDate": topic["completionDate"],
            "isCompleted": topic["isCompleted"],
            "children": children,
        }

    def _upsert_notification(self, notification_id: str, title: str, body: str, icon: str, color: str, *, read: bool = False) -> None:
        existing = next((item for item in self._notifications if item["id"] == notification_id), None)
        payload = self._normalize_notification(
            {
                "id": notification_id,
                "title": title,
                "body": body,
                "icon": icon,
                "color": color,
                "read": read if existing is None else existing.get("read", read),
                "timestamp": existing.get("timestamp") if existing else datetime.now().isoformat(),
            }
        )
        if existing is None:
            self._notifications.insert(0, payload)
        else:
            existing.update(payload)

    def _add_notification(self, title: str, body: str, icon: str, color: str) -> None:
        self._notifications.insert(0, self._normalize_notification({"title": title, "body": body, "icon": icon, "color": color}))
        self._notifications = self._notifications[:50]
        self._save()
        self._emit()

    def _refresh_reminder_notifications(self) -> None:
        overdue_count = len(self._tasks_for_bucket("overdue"))
        if self._alert_settings.get("overdue", True) and overdue_count:
            self._upsert_notification(
                f"smart-overdue-{self._today.isoformat()}",
                f"{overdue_count} Overdue Review{'s' if overdue_count != 1 else ''}",
                "Clear overdue material first to protect your recall schedule.",
                "!",
                "#EF4444",
            )
        due_today = self._tasks_for_bucket("due_today")
        if self._alert_settings.get("due_today", True) and due_today:
            self._upsert_notification(
                f"smart-due-{self._today.isoformat()}",
                "Today's Revision Queue",
                f"{len(due_today)} review{'s' if len(due_today) != 1 else ''} due today. Start with {due_today[0]['name']}.",
                "T",
                "#3B82F6",
            )
        if self._alert_settings.get("weekly_reports", True):
            year, week, _ = self._today.isocalendar()
            self._upsert_notification(
                f"smart-weekly-{year}-{week}",
                "Weekly Report Ready",
                f"You logged {self._weekly_study_minutes()} minutes in recent sessions.",
                "R",
                "#8B5CF6",
                read=True,
            )
        self._save()

    def _assistant_context(self) -> AssistantContext:
        return AssistantContext(
            due_today=self._tasks_for_bucket("due_today"),
            overdue=self._tasks_for_bucket("overdue"),
            weak_subjects=self.analyticsSubjectRows,
            upcoming_reminders=self.upcomingReminders,
            digest=self.todayDigest,
        )
    @Property("QVariantList", notify=stateChanged)
    def dashboardStats(self) -> list[dict[str, Any]]:
        tasks = self._tasks
        due_today = len(self._tasks_for_bucket("due_today"))
        overdue = len(self._tasks_for_bucket("overdue"))
        scheduled_today = len([task for task in tasks if task["scheduled_at"].date() == self._today])
        completed_today = len([task for task in tasks if task["completed"] and task["scheduled_at"].date() == self._today])
        completion_pct = round((completed_today / scheduled_today) * 100) if scheduled_today else 0
        completion_rate = max(0, min(100, completion_pct))
        avg_conf = round(sum(topic["confidence"] for topic in self._topics) / len(self._topics), 1) if self._topics else 0.0
        completion_subtitle = f"{completed_today}/{scheduled_today} sessions completed" if scheduled_today else "No sessions scheduled"
        return [
            {"title": "OVERDUE", "value": str(overdue), "subtitle": "Need attention", "trend": "High" if overdue else "Clear", "trendUp": overdue == 0, "valueColor": "#EF4444" if overdue else "#1A2332", "accentColor": "#EF4444"},
            {"title": "DUE TODAY", "value": str(due_today), "subtitle": "Remaining reviews", "trend": f"{completed_today} done", "trendUp": completed_today > 0 or due_today == 0, "valueColor": "#1A2332", "accentColor": "#3B82F6"},
            {"title": "COMPLETION", "value": f"{completion_rate}%", "subtitle": completion_subtitle, "trend": "Complete" if completion_rate == 100 and scheduled_today else ("On track" if completion_rate >= 50 else "Warm up"), "trendUp": completion_rate >= 50, "valueColor": "#1A2332", "accentColor": "#10B981", "progressValue": completion_rate},
            {"title": "AVG CONFIDENCE", "value": f"{avg_conf:.1f}/5", "subtitle": "Across topics", "trend": "Steady recall", "trendUp": avg_conf >= 3.5, "valueColor": "#1A2332", "accentColor": "#8B5CF6"},
        ]

    @Property("QVariantMap", notify=stateChanged)
    def dashboardBanner(self) -> dict[str, Any]:
        overdue = len(self._tasks_for_bucket("overdue"))
        due_today = len(self._tasks_for_bucket("due_today"))
        if overdue:
            return {"emoji": "!", "headline": f"{overdue} overdue review{'s' if overdue != 1 else ''} need attention first", "detail": "Clear the oldest cards before starting new material."}
        return {"emoji": "*", "headline": f"{due_today} review{'s' if due_today != 1 else ''} queued for today", "detail": "Stay in rhythm with short, consistent revision sessions."}

    @Property("QVariantMap", notify=stateChanged)
    def activeSession(self) -> dict[str, Any]:
        return self._active_session_payload()

    @Property("QVariantList", notify=stateChanged)
    def toasts(self) -> list[dict[str, Any]]:
        return list(self._toasts)

    @Property("QVariantMap", notify=stateChanged)
    def dashboardFocus(self) -> dict[str, Any]:
        due_items = self._tasks_for_bucket("due_today")
        return {"score": self._average_confidence_pct(), "nextRevision": due_items[0]["name"] if due_items else "No due topics"}

    @Property("QVariantList", notify=stateChanged)
    def dashboardColumns(self) -> list[dict[str, Any]]:
        return [
            {"key": "overdue", "title": "Overdue", "subtitle": "Start here first", "accentColor": "#EF4444", "count": len(self._tasks_for_bucket("overdue")), "items": self._tasks_for_bucket("overdue")},
            {"key": "due_today", "title": "Due Today", "subtitle": "Today's core revision flow", "accentColor": "#3B82F6", "count": len(self._tasks_for_bucket("due_today")), "items": self._tasks_for_bucket("due_today")},
            {"key": "upcoming", "title": "Upcoming", "subtitle": "Planned next reviews", "accentColor": "#64748B", "count": len(self._tasks_for_bucket("upcoming")), "items": self._tasks_for_bucket("upcoming")},
        ]

    @Property("QVariantList", notify=stateChanged)
    def inboxTasks(self) -> list[dict[str, Any]]:
        tasks = list(self._tasks)
        if self._task_filter == "pending":
            tasks = [task for task in tasks if not task["completed"]]
        elif self._task_filter != "all":
            tasks = [task for task in tasks if self._task_bucket(task) == self._task_filter]
        tasks.sort(key=lambda task: (task["completed"], -self._compute_urgency_score(task), task["scheduled_at"], task["topic"].lower()))
        return [self._task_payload(task) for task in tasks]

    @Property("QVariantList", notify=stateChanged)
    def taskFilters(self) -> list[dict[str, Any]]:
        keys = [("all", "All"), ("pending", "Pending"), ("overdue", "Overdue"), ("due_today", "Due Today"), ("upcoming", "Upcoming"), ("completed", "Completed")]
        return [{"key": key, "label": label, "active": self._task_filter == key, "count": len([task for task in self._tasks if key == "all" or (key == "pending" and not task["completed"]) or (key not in {"all", "pending"} and self._task_bucket(task) == key)])} for key, label in keys]

    @Property(str, notify=stateChanged)
    def curriculumDifficulty(self) -> str:
        return self._curriculum_filter

    @Property(str, notify=stateChanged)
    def curriculumSearch(self) -> str:
        return self._curriculum_search

    def _curriculum_subject_records(self) -> list[dict[str, Any]]:
        with self._db() as db:
            stmt = select(Subject).where(func.coalesce(Subject.archived, 0) == 0).order_by(Subject.name)
            subjects = list(db.scalars(stmt))

        filtered_topics = self._filtered_topics()
        topics_by_subject: dict[str, list[dict[str, Any]]] = {}
        for topic in filtered_topics:
            topics_by_subject.setdefault(str(topic["subjectId"]), []).append(topic)

        needle = self._curriculum_search.strip().lower()
        show_empty_subjects = self._curriculum_filter == "All"
        rows: list[dict[str, Any]] = []
        for subject in subjects:
            subject_id = str(subject.id)
            subject_topics = topics_by_subject.get(subject_id, [])
            subject_match = bool(needle) and needle in (subject.name or "").lower()
            if not subject_topics and not (show_empty_subjects and (not needle or subject_match)):
                continue
            meta = self._subject_meta(subject, name=subject.name, color=subject.color)
            rows.append({
                "subjectId": subject_id,
                "subjectName": subject.name,
                "iconText": meta.icon,
                "accentColor": meta.color,
                "topicCount": len(subject_topics),
                "topics": subject_topics,
            })
        return rows

    @Property("QVariantList", notify=stateChanged)
    def curriculumSubjects(self) -> list[dict[str, Any]]:
        filtered_topics = self._filtered_topics()
        lookup = {topic["id"]: topic for topic in filtered_topics}
        subjects = self._curriculum_subject_records()
        for subject in subjects:
            subject["topics"] = [
                self._topic_tree_node(topic, lookup)
                for topic in subject["topics"]
                if topic.get("parent_topic_id") is None
            ]
        return subjects

    @Property("QVariantMap", notify=stateChanged)
    def curriculumSummary(self) -> dict[str, Any]:
        filtered_topics = self._filtered_topics()
        total = len(filtered_topics)
        avg = self._average_progress(filtered_topics)
        completed = len([topic for topic in filtered_topics if topic["isCompleted"]])
        subject_count = len({topic["subjectId"] for topic in filtered_topics})
        return {"total_topics": total, "avg_progress": avg, "stats": [{"label": "Subjects", "value": str(subject_count), "color": "#3B82F6"}, {"label": "Topics", "value": str(total), "color": "#10B981"}, {"label": "Completed", "value": str(completed), "color": "#F59E0B"}, {"label": "Avg Progress", "value": f"{avg:.0f}%", "color": "#8B5CF6"}]}

    @Property("QVariantList", notify=stateChanged)
    def curriculumSubjectOptions(self) -> list[dict[str, Any]]:
        return [{"id": subject["subjectId"], "name": subject["subjectName"]} for subject in self._curriculum_subject_records()]

    @Property("QVariantList", notify=stateChanged)
    def weekCompletion(self) -> list[dict[str, Any]]:
        today = self._today
        start_of_week = today - timedelta(days=today.weekday())
        rows = []
        for offset in range(7):
            day = start_of_week + timedelta(days=offset)
            day_tasks = [task for task in self._tasks if task["scheduled_at"].date() == day]
            completed = len([task for task in day_tasks if task["completed"]])
            scheduled = len(day_tasks)
            rows.append({"day": day.strftime("%a"), "date": day.strftime("%d"), "completed": completed, "scheduled": scheduled, "remaining": max(0, scheduled - completed), "isToday": day == today})
        return rows

    @Property("QVariantList", notify=stateChanged)
    def calendarCells(self) -> list[dict[str, Any]]:
        import calendar

        cal = calendar.Calendar(firstweekday=0)
        cells = []
        for week in cal.monthdatescalendar(self._calendar_view_date.year, self._calendar_view_date.month):
            for day in week:
                day_tasks = [task for task in self._tasks if task["scheduled_at"].date() == day]
                open_tasks = [task for task in day_tasks if not task["completed"]]
                indicator_colors: list[str] = []
                for task in day_tasks:
                    color = self._task_payload(task)["statusColor"]
                    if color not in indicator_colors:
                        indicator_colors.append(color)
                status = "idle"
                if any(task["completed"] for task in day_tasks):
                    status = "completed"
                if any(task["scheduled_at"].date() < self._today and not task["completed"] for task in day_tasks):
                    status = "overdue"
                elif any(task["scheduled_at"].date() == self._today and not task["completed"] for task in day_tasks):
                    status = "due_today"
                elif open_tasks:
                    status = "upcoming"
                cells.append({
                    "dayNum": str(day.day) if day.month == self._calendar_view_date.month else "",
                    "isValid": day.month == self._calendar_view_date.month,
                    "isToday": day == self._today,
                    "isSelected": day == self._selected_date,
                    "taskCount": len(open_tasks),
                    "dateStr": day.isoformat(),
                    "status": status,
                    "indicatorColors": indicator_colors[:4],
                    "statusColor": indicator_colors[0] if indicator_colors else "#CBD5E1",
                })
        return cells[:42]

    @Property("QVariantList", notify=stateChanged)
    def calendarLegend(self) -> list[dict[str, Any]]:
        return [
            {"label": "Revision", "color": "#3B82F6"},
            {"label": "Completed", "color": "#10B981"},
            {"label": "Due", "color": "#F59E0B"},
            {"label": "Overdue", "color": "#EF4444"},
        ]

    @Property(str, notify=stateChanged)
    def calendarMonthLabel(self) -> str:
        return self._calendar_view_date.strftime("%B %Y")

    @Property(str, notify=stateChanged)
    def selectedDate(self) -> str:
        return self._selected_date.isoformat()

    @Property(str, notify=stateChanged)
    def selectedDayLabel(self) -> str:
        return self._selected_date.strftime("%A, %d %B")

    @Property("QVariantList", notify=stateChanged)
    def selectedDaySessions(self) -> list[dict[str, Any]]:
        tasks = [task for task in self._tasks if task["scheduled_at"].date() == self._selected_date]
        tasks.sort(key=lambda item: item["scheduled_at"])
        return [{"id": task["id"], "topic": task["topic"], "name": task["topic"], "subject": task["subject"], "duration": task["duration_minutes"], "time": task["scheduled_at"].strftime("%H:%M"), "durationText": f"{task['duration_minutes']} min", "color": self._task_payload(task)["subjectColor"], "subjectColor": self._task_payload(task)["subjectColor"], "status": self._task_payload(task)["status"], "statusColor": self._task_payload(task)["statusColor"], "completed": task["completed"]} for task in tasks]

    @Property(str, notify=stateChanged)
    def selectedDayTotalText(self) -> str:
        return f"{sum(item['duration'] for item in self.selectedDaySessions)} min"

    @Property("QVariantMap", notify=stateChanged)
    def revisionWeekSummary(self) -> dict[str, Any]:
        rows = self.weekCompletion
        completed = sum(row["completed"] for row in rows)
        scheduled = sum(row["scheduled"] for row in rows)
        return {"completed": completed, "remaining": sum(row["remaining"] for row in rows), "missed": len(self._tasks_for_bucket("overdue")), "score": round((completed / scheduled) * 100) if scheduled else 0, "scheduled": scheduled}
    @Property("QVariantList", notify=stateChanged)
    def subjectConfidence(self) -> list[dict[str, Any]]:
        rows = []
        for subject_name, topics in self._subject_groups().items():
            meta = self._subject_meta(name=subject_name, color=topics[0]["subjectMeta"]["color"])
            rows.append({"subject": subject_name, "pct": self._average_confidence_pct(topics), "progress": self._average_progress(topics), "topicCount": len(topics), "color": meta.color})
        rows.sort(key=lambda row: (-row["pct"], row["subject"]))
        return rows

    @Slot(result="QVariantMap")
    def getIntelligenceDashboard(self) -> dict[str, Any]:
        return self.get_intelligence_dashboard()

    def get_intelligence_dashboard(self) -> dict[str, Any]:
        return self._ml_engine.get_intelligence_dashboard()

    @Property("QVariantMap", notify=intelligenceChanged)
    def intelligenceDashboard(self) -> dict[str, Any]:
        return self.getIntelligenceDashboard()

    @Property("QVariantList", notify=stateChanged)
    def intelligenceStats(self) -> list[dict[str, Any]]:
        completed = len([task for task in self._tasks if task["completed"]])
        total = len(self._tasks)
        completion_rate = round((completed / total) * 100) if total else 0
        return [
            {"title": "WEEKLY FOCUS", "value": f"{self._weekly_study_minutes()}m", "subtitle": "last 7 sessions", "trend": "Active" if self._weekly_study_minutes() >= 180 else "Build", "trendUp": self._weekly_study_minutes() >= 180, "accentColor": "#3B82F6", "valueColor": "#1A2332"},
            {"title": "COMPLETION", "value": f"{completion_rate}%", "subtitle": f"{completed}/{total} tasks", "trend": "Healthy" if completion_rate >= 60 else "Low", "trendUp": completion_rate >= 60, "accentColor": "#10B981", "valueColor": "#1A2332"},
            {"title": "MASTERY", "value": f"{self._average_progress():.0f}%", "subtitle": "avg topic progress", "trend": "Rising" if self._average_progress() >= 65 else "Needs reps", "trendUp": self._average_progress() >= 65, "accentColor": "#F59E0B", "valueColor": "#1A2332"},
            {"title": "RECALL", "value": f"{self._average_confidence_pct()}%", "subtitle": "confidence score", "trend": "Strong" if self._average_confidence_pct() >= 70 else "Review", "trendUp": self._average_confidence_pct() >= 70, "accentColor": "#8B5CF6", "valueColor": "#1A2332"},
        ]

    @Property("QVariantList", notify=stateChanged)
    def studyTrend(self) -> list[int]:
        return self._study_trend_values()

    @Property("QVariantList", notify=stateChanged)
    def studyTrendLabels(self) -> list[str]:
        return [
            (self._today - timedelta(days=offset)).strftime("%a")
            for offset in range(13, -1, -1)
        ]

    @Property("QVariantList", notify=stateChanged)
    def activityHeatmap(self) -> list[int]:
        trend = self._study_trend_values(14)
        cells = []
        for index in range(56):
            day = self._today - timedelta(days=55 - index)
            completed_for_day = len([task for task in self._tasks if task["completed"] and task["scheduled_at"].date() == day])
            recent_minutes = trend[index - 42] if index >= 42 else 0
            cells.append(min(100, completed_for_day * 35 + recent_minutes))
        return cells

    @Property("QVariantList", notify=stateChanged)
    def analyticsSubjectRows(self) -> list[dict[str, Any]]:
        rows = []
        for row in self.subjectConfidence:
            weak_topics = [topic for topic in self._subject_groups().get(row["subject"], []) if topic["progress"] < 60 or topic["confidence"] <= 2]
            rows.append({**row, "risk": "High" if len(weak_topics) >= 2 else ("Medium" if weak_topics else "Low"), "nextAction": "Revise weak topics" if weak_topics else "Maintain cadence"})
        return rows

    @Property("QVariantList", notify=stateChanged)
    def intelligenceInsights(self) -> list[dict[str, Any]]:
        if not self._topics:
            return [{"title": "Add Topics", "body": "Create topics so StudyFlow can build analytics.", "color": "#3B82F6", "severity": "Info"}]
        weakest = min(self._topics, key=lambda topic: (topic["confidence"], topic["progress"]))
        strongest = max(self._topics, key=lambda topic: (topic["progress"], topic["confidence"]))
        return [
            {"title": f"Prioritize {weakest['name']}", "body": f"{weakest['subject']} needs a short active-recall pass.", "color": "#EF4444" if weakest["confidence"] <= 2 else "#F59E0B", "severity": "Focus"},
            {"title": "Clear Overdue Load", "body": f"{len(self._tasks_for_bucket('overdue'))} overdue review(s) are influencing the recall score.", "color": "#EF4444" if self._tasks_for_bucket('overdue') else "#10B981", "severity": "Schedule"},
            {"title": f"Keep {strongest['subject']} Warm", "body": f"{strongest['name']} is one of your strongest topics.", "color": "#10B981", "severity": "Maintain"},
        ]

    @Property("QVariantList", notify=stateChanged)
    def notifications(self) -> list[dict[str, Any]]:
        rows = [self._normalize_notification(item, index) for index, item in enumerate(self._notifications)]
        rows.sort(key=lambda item: item["timestamp"], reverse=True)
        return rows

    @Property("QVariantList", notify=stateChanged)
    def notificationStats(self) -> list[dict[str, Any]]:
        unread = len([item for item in self.notifications if not item["read"]])
        return [{"label": "Unread", "value": str(unread), "color": "#3B82F6"}, {"label": "Overdue", "value": str(len(self._tasks_for_bucket("overdue"))), "color": "#EF4444"}, {"label": "Due Today", "value": str(len(self._tasks_for_bucket("due_today"))), "color": "#F59E0B"}]

    @Property("QVariantMap", notify=stateChanged)
    def todayDigest(self) -> dict[str, Any]:
        due_today = self._tasks_for_bucket("due_today")
        overdue = self._tasks_for_bucket("overdue")
        next_task = due_today[0] if due_today else (self._tasks_for_bucket("upcoming")[0] if self._tasks_for_bucket("upcoming") else None)
        if overdue:
            summary = f"{len(overdue)} overdue review{'s' if len(overdue) != 1 else ''} need attention first."
        elif due_today:
            summary = f"{len(due_today)} review{'s' if len(due_today) != 1 else ''} are queued for today."
        else:
            summary = "No urgent revisions right now."
        return {"summary": summary, "nextSession": f"Next session: {next_task['name']} for {next_task['durationMinutes']} min" if next_task else "No sessions scheduled.", "completedToday": len([task for task in self._tasks if task["completed"] and task["scheduled_at"].date() == self._today]), "unread": len([item for item in self.notifications if not item["read"]])}

    @Property("QVariantList", notify=stateChanged)
    def upcomingReminders(self) -> list[dict[str, Any]]:
        tasks = [task for task in self._tasks if not task["completed"]]
        tasks.sort(key=lambda item: item["scheduled_at"])
        return [{"id": task["id"], "title": task["topic"], "subject": task["subject"], "when": self._task_payload(task)["scheduledText"], "color": self._task_payload(task)["subjectColor"], "status": self._task_payload(task)["status"], "statusColor": self._task_payload(task)["statusColor"]} for task in tasks[:5]]

    @Property("QVariantMap", notify=stateChanged)
    def reminderPreferences(self) -> dict[str, Any]:
        next_run = datetime.combine(self._today, time.fromisoformat(self._reminder_preferences["notification_time"]))
        if next_run <= datetime.now():
            next_run += timedelta(days=1)
        return {**self._reminder_preferences, "next_run": next_run.strftime("%d %b, %H:%M"), "summary": f"Daily check at {self._reminder_preferences['notification_time']}, alert when {self._reminder_preferences['minimum_due_for_alert']}+ topic is due."}

    @Property("QVariantList", notify=stateChanged)
    def alertSettings(self) -> list[dict[str, Any]]:
        return [{"key": key, "label": meta[0], "description": meta[1], "color": meta[2], "on": bool(self._alert_settings.get(key, False))} for key, meta in ALERT_SETTING_META.items()]

    @Property("QVariantMap", notify=stateChanged)
    def assistantStatus(self) -> dict[str, Any]:
        return self._assistant_status

    @Property("QVariantList", notify=stateChanged)
    def assistantMessages(self) -> list[dict[str, Any]]:
        return self._assistant_messages

    @Property("QVariantList", constant=True)
    def assistantPrompts(self) -> list[dict[str, str]]:
        due_topic = self._tasks_for_bucket("due_today")[0]["name"] if self._tasks_for_bucket("due_today") else "my next due topic"
        return [
            {"label": "Study Today", "prompt": "What should I study today?"},
            {"label": "Explain Topic", "prompt": f"Explain {due_topic} with a quick recall plan."},
            {"label": "Weak Areas", "prompt": "Which subject needs attention?"},
            {"label": "Exam Track", "prompt": "Am I on track for my exam?"},
        ]

    @Property("QVariantMap", notify=stateChanged)
    def assistantContextSummary(self) -> dict[str, Any]:
        context = self._assistant_context()
        return {"dueToday": len(context.due_today), "overdue": len(context.overdue), "weakSubjects": len([item for item in context.weak_subjects if item.get("risk") != "Low"]), "nextTopic": context.overdue[0]["name"] if context.overdue else (context.due_today[0]["name"] if context.due_today else "No due topics")}

    @Property("QVariantMap", notify=stateChanged)
    def scheduleSettings(self) -> dict[str, Any]:
        return {
            "daily_time_minutes": int(self._get_schedule_setting("daily_time_minutes")),
            "preferred_time": self._get_schedule_setting("preferred_time"),
        }

    @Property("QVariantList", notify=stateChanged)
    def settingsColumns(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "Study Planning",
                "rows": [
                    {
                        "label": "Daily Study Limit",
                        "key": "daily_time_minutes",
                        "kind": "value",
                        "value": f"{self.scheduleSettings['daily_time_minutes']} min",
                    },
                    {
                        "label": "Preferred Study Start Time",
                        "key": "preferred_time",
                        "kind": "value",
                        "value": self.scheduleSettings["preferred_time"],
                    },
                ],
            },
            {"title": "Notifications", "rows": [{"label": "Push Alerts", "key": "notifications", "kind": "toggle", "toggleOn": bool(self._settings.get("notifications", {}).get("enabled", True))}, {"label": "Reminders", "key": "reminders", "kind": "toggle", "toggleOn": bool(self._settings.get("reminders", True))}, {"label": "Auto Schedule", "key": "auto_schedule", "kind": "toggle", "toggleOn": bool(self._settings.get("auto_schedule", True))}]},
        ]

    @Slot(str, str)
    def updateScheduleSetting(self, key: str, value: str) -> None:
        if key == "daily_time_minutes":
            normalized = str(max(15, int(value)))
        elif key == "preferred_time":
            time.fromisoformat(value)
            normalized = value
        else:
            return
        self._set_schedule_setting(key, normalized)
        self._emit()

    @Slot(str, str)
    def addSubject(self, name: str, color: str) -> None:
        clean_name = name.strip()
        if not clean_name:
            self._show_toast("error", "Subject Not Added", "Enter a subject name before saving.")
            return
        try:
            with self._db() as db:
                SubjectService(db).create_subject(name=clean_name, color_tag=color.strip() or self._generate_subject_color())
        except IntegrityError:
            logger.warning("Subject already exists", extra={"subject": clean_name})
            self._show_toast("error", "Subject Not Added", f"{clean_name} already exists.")
            return
        self._request_intelligence_refresh()
        self._show_toast("success", "Subject Added", f"{clean_name} is ready for topics.")
        self._emit()

    @Slot(str, str)
    def renameSubject(self, subject_id: str, name: str) -> None:
        with self._db() as db:
            SubjectService(db).update_subject(subject_id, name=name.strip())
        self._request_intelligence_refresh()
        self._emit()

    @Slot(str)
    def deleteSubject(self, subject_id: str) -> None:
        subject_name = ""
        with self._db() as db:
            subject = db.get(Subject, int(subject_id))
            subject_name = subject.name if subject is not None else "Subject"
            SubjectService(db).delete_subject(subject_id)
        self._request_intelligence_refresh(train=True)
        self._show_toast("success", "Subject Deleted", f"{subject_name} and its topics were removed.")
        self._emit()

    @Slot(str, str, str)
    def addTopic(self, subject_id: str, name: str, difficulty: str) -> None:
        level = DifficultyLevel((difficulty or "Medium").lower())
        with self._db() as db:
            TopicService(db, scheduler=self._scheduler(db)).create_topic(subject_id=subject_id, name=name.strip(), difficulty=level)
        self._request_intelligence_refresh(train=True)
        self._show_toast("success", "Topic Added", f"{name.strip()} was added to your curriculum.")
        self._emit()

    @Slot(str)
    def deleteTopic(self, topic_id: str) -> None:
        topic_name = ""
        with self._db() as db:
            topic = db.get(Topic, int(topic_id))
            topic_name = topic.name if topic is not None else "Topic"
            TopicService(db, scheduler=self._scheduler(db)).delete_topic(topic_id)
        self._request_intelligence_refresh(train=True)
        self._show_toast("success", "Topic Deleted", f"{topic_name} was removed.")
        self._emit()

    @Slot(str, int)
    def updateTopicProgress(self, topic_id: str, progress: int) -> None:
        with self._db() as db:
            TopicService(db, scheduler=self._scheduler(db)).update_topic(topic_id, progress=progress)
        self._request_intelligence_refresh()
        self._emit()

    @Slot(result="QVariantList")
    def getSubjects(self) -> list[dict[str, Any]]:
        return [{"id": item["subjectId"], "name": item["subjectName"], "color": item["accentColor"]} for item in self._curriculum_subject_records()]

    @Slot(result="QVariantList")
    def getTopics(self) -> list[dict[str, Any]]:
        return self._topics

    @Slot(result="QVariantList")
    def getDueRevisions(self) -> list[dict[str, Any]]:
        return self._tasks_for_bucket("overdue") + self._tasks_for_bucket("due_today")

    @Slot(str, int)
    def reviewTopic(self, topic_id: str, rating: int) -> None:
        safe_rating = max(1, min(int(rating), 4))
        with self._db() as db:
            scheduler = self._scheduler(db)
            scheduler.review(topic_id, _rating_from_int(safe_rating), completed_at=datetime.now())
            topic = db.get(Topic, int(topic_id))
            if topic is not None:
                topic.mastery_score = max(0, min(100, (topic.mastery_score or 0) + RATING_TO_PROGRESS[safe_rating]))
        self._study_minutes.append(25)
        self._study_minutes = self._study_minutes[-14:]
        self._save()
        self._mark_revision_completed_for_intelligence()
        self._emit()

    @Slot(str)
    def markTaskDone(self, task_id: str) -> None:
        with self._db() as db:
            revision = db.get(Revision, int(task_id))
            if revision is None or revision.status != "open":
                self._show_toast("error", "Task Update Failed", "That task is no longer available.")
                return
            topic_name = revision.topic.name
            self._scheduler(db).record_revision(revision.id, rating=ConfidenceRating.GOOD, completed_at=datetime.now())
            revision.topic.mastery_score = max(0, min(100, (revision.topic.mastery_score or 0) + RATING_TO_PROGRESS[3]))
        self._study_minutes.append(25)
        self._study_minutes = self._study_minutes[-14:]
        self._save()
        self._mark_revision_completed_for_intelligence()
        self._show_toast("success", "Task Reviewed", f"{topic_name} was marked done.")
        self._emit()

    @Slot(str, int)
    def completeRevision(self, task_id: str, rating: int) -> None:
        with self._db() as db:
            revision = db.get(Revision, int(task_id))
            if revision is None or revision.status != "open":
                self._show_toast("error", "Revision Update Failed", "That revision is no longer open.")
                return
            safe_rating = max(1, min(int(rating), 4))
            topic_name = revision.topic.name
            self._scheduler(db).record_revision(revision.id, rating=_rating_from_int(safe_rating), completed_at=datetime.now())
            revision.topic.mastery_score = max(0, min(100, (revision.topic.mastery_score or 0) + RATING_TO_PROGRESS[safe_rating]))
        self._study_minutes.append(25)
        self._study_minutes = self._study_minutes[-14:]
        self._save()
        self._mark_revision_completed_for_intelligence()
        self._emit()
        self._show_toast("success", "Revision Logged", f"{topic_name} rated {RATING_LABELS[max(1, min(int(rating), 4))]}.")
        self._add_notification("Revision Logged", f"Review marked {RATING_LABELS[max(1, min(int(rating), 4))]}.", "check_circle", "#10B981")

    @Slot(str, str, str, str)
    def addTask(self, topic_name: str, subject_id: str, difficulty: str, schedule_key: str) -> None:
        clean_topic_name = topic_name.strip()
        if not clean_topic_name:
            self._show_toast("error", "Task Not Added", "Enter a task name before creating it.")
            return
        with self._db() as db:
            scheduler = self._scheduler(db)
            service = TopicService(db, scheduler=scheduler)
            topic = service.create_topic(subject_id=subject_id, name=clean_topic_name, difficulty=DifficultyLevel((difficulty or "Medium").lower()), auto_schedule=False)
            offset = {"overdue": -1, "today": 0, "tomorrow": 1, "this_week": 3}.get(schedule_key, 0)
            scheduler.create_first_revision(topic.id, scheduled_for=self._today + timedelta(days=offset))
        self._request_intelligence_refresh(train=True)
        self._show_toast("success", "Task Added", f"{clean_topic_name} was scheduled.")
        self._emit()

    @Slot(str)
    def skipTask(self, task_id: str) -> None:
        with self._db() as db:
            revision = db.get(Revision, int(task_id))
            if revision is None or revision.status != "open":
                self._show_toast("error", "Skip Failed", "That task is no longer available.")
                return
            topic_name = revision.topic.name
            self._scheduler(db).reschedule_after_miss(revision.id, reschedule_from=self._today + timedelta(days=1))
        self._request_intelligence_refresh()
        self._show_toast("info", "Task Skipped", f"{topic_name} was moved to the next slot.")
        self._emit()

    @Slot()
    def markAllTasksDone(self) -> None:
        visible_ids = {int(task["id"]) for task in self.inboxTasks}
        if not visible_ids:
            self._show_toast("info", "Nothing To Mark", "There are no visible tasks to complete.")
            return

        completed_count = 0
        try:
            with self._db() as db:
                revisions = list(
                    db.scalars(
                        select(Revision)
                        .options(joinedload(Revision.topic).joinedload(Topic.subject))
                        .where(Revision.id.in_(visible_ids), Revision.status == "open")
                        .order_by(Revision.due_at, Revision.id)
                    )
                )
                for revision in revisions:
                    self._scheduler(db).record_revision(revision.id, rating=ConfidenceRating.GOOD, completed_at=datetime.now())
                    revision.topic.mastery_score = max(0, min(100, (revision.topic.mastery_score or 0) + RATING_TO_PROGRESS[3]))
                    completed_count += 1
        except Exception:
            logger.exception("Failed to mark visible tasks done")
            self._show_toast("error", "Bulk Update Failed", "StudyFlow could not mark the visible tasks as done.")
            return

        if completed_count == 0:
            self._show_toast("info", "Nothing To Mark", "All visible tasks are already complete.")
            return

        self._study_minutes.extend([25] * completed_count)
        self._study_minutes = self._study_minutes[-14:]
        self._save()
        self._mark_revision_completed_for_intelligence()
        self._show_toast("success", "Tasks Completed", f"Marked {completed_count} visible task{'s' if completed_count != 1 else ''} as done.")
        self._emit()

    @Slot()
    def startSession(self) -> None:
        if self._active_session is not None:
            self.stopSession()
            return

        with self._db() as db:
            stmt = (
                select(Revision)
                .options(joinedload(Revision.topic).joinedload(Topic.subject))
                .where(Revision.status == "open")
                .order_by(Revision.due_at, Revision.created_at)
            )
            revision = db.scalars(stmt).first()
            topic = revision.topic if revision is not None else None
            subject = topic.subject if topic is not None else None
            started_at = datetime.now()
            study_session = StudySession(
                subject_id=subject.id if subject is not None else None,
                topic_id=topic.id if topic is not None else None,
                started_at=started_at,
                session_type="study",
                notes="Started from dashboard",
            )
            db.add(study_session)
            db.flush()
            self._active_session = {
                "id": study_session.id,
                "started_at": started_at.isoformat(),
                "topic": topic.name if topic is not None else "",
                "subject": subject.name if subject is not None else "",
            }

        session_info = self._active_session_payload()
        self._save()
        detail = f"Focusing on {session_info['topic']}." if session_info["topic"] else "Pick a due topic and rate it when you finish."
        self._show_toast("info", "Session Started", detail)
        self._emit()
        self._add_notification("Session Started", detail, "play_arrow", "#3B82F6")

    @Slot()
    def stopSession(self) -> None:
        active_session = self._active_session
        if active_session is None:
            return

        started_at = datetime.fromisoformat(active_session["started_at"])
        ended_at = datetime.now()
        duration_minutes = max(1, round((ended_at - started_at).total_seconds() / 60))
        with self._db() as db:
            session_row = db.get(StudySession, int(active_session["id"]))
            if session_row is not None:
                session_row.ended_at = ended_at
                session_row.duration_minutes = duration_minutes
                session_row.focus_score = float(self._average_confidence_pct())
                if active_session.get("topic"):
                    session_row.notes = f"Completed dashboard session on {active_session['topic']}"

        self._study_minutes.append(duration_minutes)
        self._study_minutes = self._study_minutes[-14:]
        session_topic = active_session.get("topic", "")
        self._active_session = None
        self._save()
        self._emit()
        detail = f"Logged {duration_minutes} minutes on {session_topic}." if session_topic else f"Logged {duration_minutes} study minutes."
        self._show_toast("success", "Session Ended", detail)
        self._add_notification("Session Ended", detail, "stop", "#10B981")

    @Slot(str, str, str, str, str, str)
    def upsertTopic(self, topic_id: str, name: str, subject_id: str, difficulty: str, parent_topic_id: str, notes: str) -> None:
        level = DifficultyLevel((difficulty or "Medium").lower())
        with self._db() as db:
            service = TopicService(db, scheduler=self._scheduler(db))
            if topic_id:
                service.update_topic(topic_id, name=name.strip(), difficulty=level, parent_topic_id=parent_topic_id, notes=notes.strip())
                toast_title = "Topic Updated"
            else:
                service.create_topic(subject_id=subject_id, name=name.strip(), difficulty=level, parent_topic_id=parent_topic_id, notes=notes.strip())
                toast_title = "Topic Added"
        self._request_intelligence_refresh(train=True)
        self._show_toast("success", toast_title, f"{name.strip()} was saved.")
        self._emit()

    @Slot(str)
    def markTopicComplete(self, topic_id: str) -> None:
        topic_name = ""
        with self._db() as db:
            topic = db.get(Topic, int(topic_id))
            topic_name = topic.name if topic is not None else "Topic"
            TopicService(db, scheduler=self._scheduler(db)).update_topic(topic_id, is_completed=True, completion_date=self._today, progress=100)
        self._request_intelligence_refresh()
        self._show_toast("success", "Topic Completed", f"{topic_name} reached 100% progress.")
        self._emit()

    @Slot(str, result="QVariantMap")
    def suggestTopicDifficulty(self, topic_name: str) -> dict[str, Any]:
        prediction = self._nlp_service.predict_difficulty(topic_name.strip())
        return {"difficulty": prediction.difficulty.value.capitalize() if prediction.difficulty else "", "confidence": round(prediction.confidence, 2), "source": prediction.source}

    @Slot(str, str, bool)
    def importTopics(self, raw_text: str, subject_id: str, csv_mode: bool) -> None:
        entries: list[str] = []
        if csv_mode:
            for row in csv.reader(StringIO(raw_text)):
                if row and row[0].strip():
                    entries.append(row[0].strip())
        else:
            entries = [line.strip() for line in raw_text.splitlines() if line.strip()]
        with self._db() as db:
            service = TopicService(db, scheduler=self._scheduler(db))
            for entry in entries:
                suggestion = self.suggestTopicDifficulty(entry)
                difficulty = DifficultyLevel((suggestion["difficulty"] or "Medium").lower())
                try:
                    with db.begin_nested():
                        service.create_topic(subject_id=subject_id, name=entry, difficulty=difficulty)
                        db.flush()
                except IntegrityError:
                    logger.warning("Skipping duplicate or invalid imported topic", extra={"topic": entry, "subject_id": subject_id})
        self._emit()
    @Slot(str)
    def setTaskFilter(self, filter: str) -> None:
        self._task_filter = filter
        self._emit()

    @Slot(str)
    def setCurriculumSearch(self, text: str) -> None:
        self._curriculum_search = text
        self._emit()

    @Slot(str)
    def setCurriculumDifficulty(self, difficulty: str) -> None:
        self._curriculum_filter = difficulty if difficulty in {"All", "Easy", "Medium", "Hard"} else "All"
        self._emit()

    @Slot(str)
    def selectCalendarDay(self, date_str: str) -> None:
        try:
            self._selected_date = date.fromisoformat(date_str)
            self._emit()
        except ValueError:
            return

    @Slot()
    def selectToday(self) -> None:
        self._selected_date = self._today
        self._emit()

    @Slot()
    def goToToday(self) -> None:
        self._selected_date = self._today
        self._calendar_view_date = self._today
        self._emit()

    @Slot(int)
    def changeCalendarMonth(self, offset: int) -> None:
        import calendar

        new_month = self._calendar_view_date.month + offset - 1
        new_year = self._calendar_view_date.year + new_month // 12
        new_month = new_month % 12 + 1
        max_days = calendar.monthrange(new_year, new_month)[1]
        self._calendar_view_date = self._calendar_view_date.replace(year=new_year, month=new_month, day=min(self._calendar_view_date.day, max_days))
        self._emit()

    @Slot()
    def clearNotifications(self) -> None:
        self._notifications.clear()
        self._save()
        self._show_toast("info", "Notifications Cleared", "Recent notifications were removed.")
        self._emit()

    @Slot()
    def markAllNotificationsRead(self) -> None:
        for notification in self._notifications:
            notification["read"] = True
        self._save()
        self._show_toast("success", "Notifications Updated", "All notifications were marked as read.")
        self._emit()

    @Slot(str)
    def markNotificationRead(self, notification_id: str) -> None:
        notification = next((item for item in self._notifications if item["id"] == notification_id), None)
        if notification is None:
            return
        notification["read"] = True
        self._save()
        self._emit()

    @Slot()
    def refreshReminders(self) -> None:
        self._refresh_reminder_notifications()
        self._show_toast("success", "Notifications Refreshed", "Reminder alerts were refreshed.")
        self._emit()

    @Slot(result=int)
    def runReminderCheck(self) -> int:
        preferences = self._reminder_preferences_model()
        if not preferences.enabled:
            return 0
        created = 0
        summary = build_morning_summary(self._tasks_for_bucket("due_today"), self._tasks_for_bucket("overdue"), preferences.minimum_due_for_alert)
        if summary is not None and self._alert_settings.get("due_today", True):
            self._add_notification(summary["title"], summary["body"], summary["icon"], summary["color"])
            created += 1
        for warning in build_exam_warnings(self._topics, self._today):
            self._add_notification(warning["title"], warning["body"], warning["icon"], warning["color"])
            created += 1
        return created

    def _reminder_preferences_model(self) -> ReminderPreferences:
        hour, minute = self._reminder_preferences["notification_time"].split(":", maxsplit=1)
        return ReminderPreferences(enabled=bool(self._reminder_preferences["enabled"]), notification_time=time(hour=int(hour), minute=int(minute)), minimum_due_for_alert=int(self._reminder_preferences["minimum_due_for_alert"]), desktop_notifications=bool(self._reminder_preferences["desktop_notifications"]))

    @Slot(str, str)
    def updateReminderPreference(self, key: str, value: str) -> None:
        if key not in self._reminder_preferences:
            return
        if key in {"enabled", "desktop_notifications"}:
            self._reminder_preferences[key] = value.lower() in {"1", "true", "yes", "on"}
        elif key == "minimum_due_for_alert":
            self._reminder_preferences[key] = max(1, int(value))
        elif key == "notification_time":
            time.fromisoformat(value)
            self._reminder_preferences[key] = value
        self._save()
        self._emit()

    @Slot(result=str)
    def exportCalendar(self) -> str:
        export_path = Path(__file__).resolve().parent.parent / "data" / "studyflow_revisions.ics"
        write_revision_calendar(self._open_task_rows(), export_path)
        self._add_notification("Calendar Export Ready", f"Saved upcoming revision sessions to {export_path.name}.", "CAL", "#3B82F6")
        return str(export_path)

    @Slot(str, result="QVariantMap")
    def sendAssistantMessage(self, prompt: str) -> dict[str, Any]:
        clean = prompt.strip()
        if not clean:
            return {"text": "", "source": "empty"}
        user_message = self._normalize_assistant_message({"role": "user", "text": clean, "source": "user"})
        self._assistant_messages.append(user_message)
        response = self._llm_service.answer(clean, self._assistant_context())
        assistant_message = self._normalize_assistant_message({"role": "assistant", "text": response["text"], "source": response["source"]})
        self._assistant_messages.append(assistant_message)
        self._assistant_messages = self._assistant_messages[-40:]
        self._save()
        self._emit()
        return assistant_message

    @Slot()
    def clearAssistantChat(self) -> None:
        self._assistant_messages = self._default_assistant_messages()
        self._save()
        self._show_toast("info", "Chat Cleared", "Assistant history was reset.")
        self._emit()

    @Slot()
    def saveSettings(self) -> None:
        self._save()
        self._show_toast("success", "Settings Saved", "Your preferences were saved.")

    @Slot()
    def clearHistory(self) -> None:
        self._study_minutes.clear()
        self._notifications.clear()
        self._save()
        self._show_toast("warning", "History Cleared", "Study history and notifications were cleared.")
        self._emit()

    @Slot(str)
    def dismissToast(self, toast_id: str) -> None:
        before = len(self._toasts)
        self._toasts = [toast for toast in self._toasts if toast.get("id") != toast_id]
        if len(self._toasts) != before:
            self._emit()

    @Slot(int)
    @Slot(str)
    def toggleSetting(self, index: int | str) -> None:
        keys = ["notifications", "reminders", "auto_schedule"]
        key = keys[index] if isinstance(index, int) else str(index)
        if key == "notifications":
            self._settings["notifications"]["enabled"] = not bool(self._settings["notifications"]["enabled"])
        elif key in {"reminders", "auto_schedule"}:
            self._settings[key] = not bool(self._settings[key])
        self._save()
        self._emit()

    @Slot(int)
    @Slot(str)
    def toggleAlertSetting(self, index: int | str) -> None:
        keys = list(ALERT_SETTING_META)
        key = keys[index] if isinstance(index, int) else str(index)
        if key not in self._alert_settings:
            return
        self._alert_settings[key] = not self._alert_settings[key]
        self._refresh_reminder_notifications()
        self._emit()

    @Slot(result=str)
    def exportLearningReport(self) -> str:
        export_dir = Path(__file__).resolve().parent.parent / "data"
        export_dir.mkdir(parents=True, exist_ok=True)
        report_path = export_dir / "learning_report.txt"
        report_path.write_text("StudyFlow Learning Report\n", encoding="utf-8")
        self._add_notification("Learning Report Exported", f"Saved analytics report to {report_path.name}.", "R", "#8B5CF6")
        return str(report_path)
