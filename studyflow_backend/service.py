from .service_db import StudyFlowBackend

"""

import csv
import logging
from datetime import date, datetime, time, timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot

from llm import AssistantContext, LLMService
from nlp import NLPService, load_training_examples, train_model
from services import (
    DesktopNotifier,
    ReminderPreferences,
    SyncConfig,
    SyncService,
    build_exam_warnings,
    build_morning_summary,
    write_revision_calendar,
)

from .defaults import SUBJECTS, build_default_notifications, default_alert_settings
from .models import SubjectMeta
from .presenters import difficulty_color, task_payload
from .storage import load_state, save_state

# Constants
PROGRESS_MASTERED = 80
CONFIDENCE_MAX = 5
SUBJECT_DISPLAY_NAMES = {"Mathematics": "Maths"}
RATING_LABELS = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
RATING_PROGRESS_BOOST = {1: -6, 2: 2, 3: 6, 4: 10}
RATING_CONFIDENCE = {1: 1, 2: 2, 3: 4, 4: 5}
ALERT_SETTING_META = {
    "due_today": ("Due Today", "Notify when revisions are scheduled for today.", "#3B82F6"),
    "overdue": ("Overdue Reviews", "Highlight slipped reviews before new study.", "#EF4444"),
    "ai_suggestions": ("AI Suggestions", "Surface schedule and recall recommendations.", "#8B5CF6"),
    "weekly_reports": ("Weekly Reports", "Show progress summary notifications.", "#10B981"),
    "session_reminders": ("Session Reminders", "Remind before planned study blocks.", "#F59E0B"),
    "streak_reminders": ("Streak Reminders", "Nudge consistency when activity drops.", "#14B8A6"),
}

logger = logging.getLogger(__name__)




class StudyFlowBackend(QObject):
    stateChanged = Signal()

    def __init__(self, store_path: Path | None = None) -> None:
        super().__init__()
        self._store_path = store_path or Path(__file__).resolve().parent.parent / "studyflow_data.json"
        self._today_provider = date.today
        self._today_value = self._today_provider()
        self._selected_date = self._today_value
        self._calendar_view_date = self._today_value
        self._task_filter = "all"
        self._curriculum_filter = "All"
        self._curriculum_search = ""
        self._nlp_service = NLPService()
        self._bootstrap_nlp_model()

        try:
            state = load_state(self._store_path, self._today_value)
            self._settings = state.get("settings", {"notifications": True, "reminders": True, "auto_schedule": True})
            self._alert_settings = self._normalize_alert_settings(state.get("alert_settings", {}))
            self._reminder_preferences = self._normalize_reminder_preferences(state.get("reminder_preferences", {}))
            assistant_messages = state.get("assistant_messages") or self._default_assistant_messages()
            self._assistant_messages = [
                self._normalize_assistant_message(message)
                for message in assistant_messages
            ]
            self._sync_settings = self._normalize_sync_settings(state.get("sync_settings", {}))
            self._sync_history = [self._normalize_sync_history(item) for item in state.get("sync_history", [])]
            self._suggestion_dismissed = state.get("suggestion_dismissed", False)
            self._study_minutes = state.get("study_minutes", [])
            self._topics = state.get("topics", [])
            self._tasks = state.get("tasks", [])
            self._notifications = [
                self._normalize_notification(notification, index)
                for index, notification in enumerate(state.get("notifications", build_default_notifications()))
            ]
        except Exception:
            logger.exception("Failed to initialize persisted StudyFlow state from %s", self._store_path)
            self._settings = {"notifications": True, "reminders": True, "auto_schedule": True}
            self._alert_settings = self._normalize_alert_settings({})
            self._reminder_preferences = self._normalize_reminder_preferences({})
            self._assistant_messages = self._default_assistant_messages()
            self._sync_settings = self._normalize_sync_settings({})
            self._sync_history = []
            self._suggestion_dismissed = False
            self._study_minutes = []
            self._topics = []
            self._tasks = []
            self._notifications = [
                self._normalize_notification(notification, index)
                for index, notification in enumerate(build_default_notifications())
            ]

        self._topics = [self._normalize_topic(topic) for topic in self._topics]
        self._rebuild_missing_tasks()
        self._refresh_reminder_notifications()
        self._desktop_notifier = DesktopNotifier()
        self._llm_service = LLMService()
        self._assistant_status = self._llm_service.status()
        self._sync_service = SyncService(self._sync_config())

    def _save(self) -> None:
        save_state(
            self._store_path,
            {
                "settings": self._settings,
                "alert_settings": self._alert_settings,
                "reminder_preferences": self._reminder_preferences,
                "assistant_messages": self._assistant_messages,
                "sync_settings": self._sync_settings,
                "sync_history": self._sync_history,
                "suggestion_dismissed": self._suggestion_dismissed,
                "study_minutes": self._study_minutes,
                "topics": self._topics,
                "tasks": self._tasks,
                "notifications": self._notifications,
            },
        )

    def _emit(self) -> None:
        self.stateChanged.emit()

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
        elif self._selected_date == previous + timedelta(days=1):
            self._selected_date = current + timedelta(days=1)

        if self._calendar_view_date == previous:
            self._calendar_view_date = current

        self._today_value = current
        return current

    def _subject_meta(self, subject: str) -> SubjectMeta:
        return SUBJECTS.get(subject, SubjectMeta("?", "#64748B"))

    def _normalize_alert_settings(self, settings: dict[str, Any]) -> dict[str, bool]:
        normalized = default_alert_settings()
        legacy_keys = {"study_reminder": "session_reminders", "break_reminder": "streak_reminders"}
        for key, value in settings.items():
            normalized[legacy_keys.get(key, key)] = bool(value)
        return normalized

    def _normalize_reminder_preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "enabled": True,
            "notification_time": "08:00",
            "minimum_due_for_alert": 1,
            "desktop_notifications": False,
        }
        normalized.update(preferences)
        try:
            minimum_due = int(normalized["minimum_due_for_alert"])
        except (TypeError, ValueError):
            minimum_due = 1
        normalized["minimum_due_for_alert"] = max(1, minimum_due)
        normalized["enabled"] = bool(normalized["enabled"])
        normalized["desktop_notifications"] = bool(normalized["desktop_notifications"])
        if not isinstance(normalized["notification_time"], str) or ":" not in normalized["notification_time"]:
            normalized["notification_time"] = "08:00"
        return normalized

    def _reminder_preferences_model(self) -> ReminderPreferences:
        hour, minute = self._reminder_preferences["notification_time"].split(":", maxsplit=1)
        return ReminderPreferences(
            enabled=bool(self._reminder_preferences["enabled"]),
            notification_time=time(hour=int(hour), minute=int(minute)),
            minimum_due_for_alert=int(self._reminder_preferences["minimum_due_for_alert"]),
            desktop_notifications=bool(self._reminder_preferences["desktop_notifications"]),
        )

    def _normalize_sync_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "enabled": False,
            "supabase_url": "",
            "supabase_anon_key": "",
            "device_id": f"device-{uuid4().hex[:10]}",
            "last_sync_at": "",
        }
        normalized.update(settings)
        normalized["enabled"] = bool(normalized["enabled"])
        if not normalized.get("device_id"):
            normalized["device_id"] = f"device-{uuid4().hex[:10]}"
        return normalized

    def _normalize_sync_history(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = dict(item)
        payload.setdefault("id", f"sync-{uuid4().hex[:8]}")
        payload.setdefault("status", "local_only")
        payload.setdefault("message", "")
        payload.setdefault("pushed", 0)
        payload.setdefault("pulled", 0)
        payload.setdefault("conflicts", 0)
        payload.setdefault("created_at", datetime.now().isoformat())
        return payload

    def _sync_config(self) -> SyncConfig:
        return SyncConfig(
            enabled=bool(self._sync_settings["enabled"]),
            supabase_url=str(self._sync_settings.get("supabase_url", "")),
            supabase_anon_key=str(self._sync_settings.get("supabase_anon_key", "")),
            device_id=str(self._sync_settings["device_id"]),
            last_sync_at=str(self._sync_settings.get("last_sync_at", "")),
        )

    def _sync_state(self) -> dict[str, Any]:
        return {
            "settings": self._settings,
            "alert_settings": self._alert_settings,
            "reminder_preferences": self._reminder_preferences,
            "topics": self._topics,
            "tasks": self._tasks,
            "notifications": self._notifications,
        }

    def _mark_all_local_records_pending(self) -> None:
        for collection in (self._topics, self._tasks, self._notifications):
            for item in collection:
                self._sync_service.mark_pending(item)
        for settings in (self._settings, self._alert_settings, self._reminder_preferences):
            settings["sync_status"] = "pending"
            settings["updated_at"] = datetime.now().isoformat()

    def _notification_timestamp(self, index: int) -> datetime:
        return datetime.combine(self._today, datetime.min.time()).replace(hour=12) - timedelta(minutes=index)

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
        item = dict(notification)
        timestamp = item.get("timestamp")
        if isinstance(timestamp, str):
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                parsed_timestamp = self._notification_timestamp(index)
        elif isinstance(timestamp, datetime):
            parsed_timestamp = timestamp
        else:
            parsed_timestamp = self._notification_timestamp(index)

        item.setdefault("id", f"notif-{uuid4().hex[:8]}")
        item.setdefault("title", "StudyFlow Alert")
        item.setdefault("body", "")
        item.setdefault("icon", "!")
        item.setdefault("color", "#3B82F6")
        item.setdefault("read", False)
        item.setdefault("sync_status", "pending")
        item.setdefault("updated_at", parsed_timestamp.isoformat())
        item["timestamp"] = parsed_timestamp.isoformat()
        item["time"] = item.get("time") or self._relative_time_label(parsed_timestamp)
        return item

    def _default_assistant_messages(self) -> list[dict[str, Any]]:
        return [
            self._normalize_assistant_message(
                {
                    "role": "assistant",
                    "text": "I can help decide what to study next, explain due topics, and turn your weak areas into a short plan.",
                    "source": "system",
                }
            )
        ]

    def _normalize_assistant_message(self, message: dict[str, Any]) -> dict[str, Any]:
        item = dict(message)
        timestamp = item.get("timestamp")
        if isinstance(timestamp, str):
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                parsed_timestamp = datetime.now()
        elif isinstance(timestamp, datetime):
            parsed_timestamp = timestamp
        else:
            parsed_timestamp = datetime.now()
        item.setdefault("id", f"msg-{uuid4().hex[:8]}")
        item.setdefault("role", "assistant")
        item.setdefault("text", "")
        item.setdefault("source", "offline")
        item["timestamp"] = parsed_timestamp.isoformat()
        item["time"] = parsed_timestamp.strftime("%H:%M")
        return item

    def _assistant_context(self) -> AssistantContext:
        return AssistantContext(
            due_today=self._tasks_for_bucket("due_today"),
            overdue=self._tasks_for_bucket("overdue"),
            weak_subjects=self.analyticsSubjectRows,
            upcoming_reminders=self.upcomingReminders,
            digest=self.todayDigest,
        )

    def _bootstrap_nlp_model(self) -> None:
        if self._nlp_service.model_path.exists():
            return
        dataset_path = Path(__file__).resolve().parent.parent / "nlp" / "data" / "training.csv"
        if dataset_path.exists():
            examples = load_training_examples(dataset_path)
            train_model(examples, service=self._nlp_service)

    def _normalize_topic(self, topic: dict[str, Any]) -> dict[str, Any]:
        item = dict(topic)
        item.setdefault("id", f"topic-{uuid4().hex[:8]}")
        item.setdefault("subject", "General")
        item.setdefault("difficulty", "Medium")
        item.setdefault("progress", 0)
        item.setdefault("confidence", 3)
        item.setdefault("notes", "")
        item.setdefault("parent_topic_id", None)
        item.setdefault("exam_date", "")
        item.setdefault("completion_date", "")
        item.setdefault("is_completed", False)
        return item

    def _rebuild_missing_tasks(self) -> None:
        task_topics = {task["topic"] for task in self._tasks}
        for topic in self._topics:
            if topic["name"] not in task_topics and not topic.get("is_completed"):
                self._tasks.append(self._build_task_for_topic(topic))

    def _build_task_for_topic(self, topic: dict[str, Any]) -> dict[str, Any]:
        return self._create_task(
            topic_name=topic["name"],
            subject=topic["subject"],
            difficulty=topic["difficulty"],
            confidence=int(topic["confidence"]),
        )

    def _create_task(
        self,
        *,
        topic_name: str,
        subject: str,
        difficulty: str,
        confidence: int,
        offset_days: int | None = None,
        scheduled_at: datetime | None = None,
    ) -> dict[str, Any]:
        normalized_difficulty = difficulty if difficulty in {"Easy", "Medium", "Hard"} else "Medium"
        delay_days = {"Easy": 1, "Medium": 0, "Hard": 0}.get(normalized_difficulty, 1)
        review_hour = {"Easy": 15, "Medium": 11, "Hard": 9}.get(normalized_difficulty, 11)
        if scheduled_at is None:
            due_offset = delay_days if offset_days is None else max(-30, min(offset_days, 365))
            scheduled_at = datetime.combine(
                self._today + timedelta(days=due_offset),
                datetime.min.time(),
            ).replace(hour=review_hour)
        return {
            "id": f"task-{uuid4().hex[:8]}",
            "topic": topic_name,
            "subject": subject,
            "difficulty": normalized_difficulty,
            "scheduled_at": scheduled_at,
            "confidence": max(1, min(int(confidence), CONFIDENCE_MAX)),
            "status": "pending",
            "duration_minutes": {"Easy": 15, "Medium": 25, "Hard": 35}[normalized_difficulty],
            "completed_at": None,
            "completed": False,
        }

    def _task_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        return task_payload(self._today, self._subject_meta(task["subject"]), task)

    def _find_task(self, task_id: str) -> dict[str, Any] | None:
        return next((task for task in self._tasks if task["id"] == task_id), None)

    def _find_topic(self, topic_name: str) -> dict[str, Any] | None:
        return next((topic for topic in self._topics if topic["name"] == topic_name), None)

    def _find_topic_by_id(self, topic_id: str) -> dict[str, Any] | None:
        return next((topic for topic in self._topics if topic["id"] == topic_id), None)

    def _ensure_topic_for_task(self, topic_name: str, subject: str, difficulty: str) -> None:
        if self._find_topic(topic_name) is not None:
            return
        self._topics.append(
            self._normalize_topic(
                {
                    "id": f"topic-{uuid4().hex[:8]}",
                    "name": topic_name,
                    "subject": subject,
                    "difficulty": difficulty,
                    "progress": 0,
                    "confidence": 3,
                    "notes": "",
                }
            )
        )

    def _inbox_tasks(self) -> list[dict[str, Any]]:
        tasks = list(self._tasks)
        if self._task_filter == "pending":
            tasks = [task for task in tasks if not self._is_task_completed(task)]
        elif self._task_filter != "all":
            tasks = [task for task in tasks if self._task_bucket(task) == self._task_filter]
        tasks.sort(
            key=lambda task: (
                self._is_task_completed(task),
                -self._compute_urgency_score(task),
                task["scheduled_at"],
                task["topic"].lower(),
            )
        )
        return [self._task_payload(task) for task in tasks]

    def _subjects_from_topics(self) -> list[str]:
        return sorted(set(SUBJECTS.keys()) | {topic["subject"] for topic in self._topics})

    def _subject_groups(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for topic in self._topics:
            grouped.setdefault(topic["subject"], []).append(topic)
        return grouped

    def _average_progress(self, topics: list[dict[str, Any]] | None = None) -> float:
        items = topics if topics is not None else self._topics
        return round(sum(topic["progress"] for topic in items) / len(items), 1) if items else 0.0

    def _average_confidence_pct(self, topics: list[dict[str, Any]] | None = None) -> int:
        items = topics if topics is not None else self._topics
        if not items:
            return 0
        return round(sum(topic["confidence"] for topic in items) / (len(items) * CONFIDENCE_MAX) * 100)

    def _completed_tasks(self) -> list[dict[str, Any]]:
        return [task for task in self._tasks if self._is_task_completed(task)]

    def _weekly_study_minutes(self) -> int:
        return sum(self._study_minutes[-7:])

    def _study_trend_values(self, days: int = 14) -> list[int]:
        values = self._study_minutes[-days:]
        return [0] * (days - len(values)) + values

    def _filtered_topics(self) -> list[dict[str, Any]]:
        topics = self._topics
        if self._curriculum_filter != "All":
            topics = [topic for topic in topics if topic["difficulty"] == self._curriculum_filter]
        if self._curriculum_search:
            needle = self._curriculum_search.lower()
            topics = [
                topic for topic in topics
                if needle in topic["name"].lower() or needle in topic["subject"].lower()
            ]
        return topics

    def _topic_tree_node(self, topic: dict[str, Any], topic_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
        children = [
            self._topic_tree_node(candidate, topic_lookup)
            for candidate in topic_lookup.values()
            if candidate.get("parent_topic_id") == topic["id"]
        ]
        children.sort(key=lambda item: item["name"])
        return {
            "id": topic["id"],
            "name": topic["name"],
            "subject": topic["subject"],
            "difficulty": topic["difficulty"],
            "difficultyColor": difficulty_color(topic["difficulty"]),
            "progress": topic["progress"],
            "confidence": topic["confidence"],
            "notes": topic.get("notes", ""),
            "examDate": topic.get("exam_date", ""),
            "completionDate": topic.get("completion_date", ""),
            "isCompleted": topic.get("is_completed", False),
            "children": children,
        }

    def _is_task_completed(self, task: dict[str, Any]) -> bool:
        return bool(task.get("completed_at")) or bool(task.get("completed"))

    def _compute_urgency_score(self, task: dict[str, Any]) -> int:
        days_delta = (task["scheduled_at"].date() - self._today).days
        difficulty_weight = {"Easy": 8, "Medium": 16, "Hard": 24}.get(task["difficulty"], 10)
        confidence_penalty = max(0, 6 - int(task["confidence"])) * 5
        overdue_bonus = 0 if days_delta >= 0 else abs(days_delta) * 30
        due_today_bonus = 18 if days_delta == 0 else 0
        upcoming_decay = max(0, 12 - max(days_delta, 0) * 3)
        return difficulty_weight + confidence_penalty + overdue_bonus + due_today_bonus + upcoming_decay

    def _dashboard_task_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        payload = self._task_payload(task)
        payload["urgencyScore"] = self._compute_urgency_score(task)
        payload["isCompleted"] = self._is_task_completed(task)
        payload["bucket"] = self._task_bucket(task)
        payload["confidenceLabel"] = f"Confidence {task['confidence']}/{CONFIDENCE_MAX}"
        return payload

    def _task_bucket(self, task: dict[str, Any]) -> str:
        if self._is_task_completed(task):
            return "completed"
        scheduled_day = task["scheduled_at"].date()
        if scheduled_day < self._today:
            return "overdue"
        if scheduled_day == self._today:
            return "due_today"
        return "upcoming"

    def _tasks_for_bucket(self, bucket: str) -> list[dict[str, Any]]:
        items = [task for task in self._tasks if self._task_bucket(task) == bucket]
        items.sort(key=lambda task: (-self._compute_urgency_score(task), task["scheduled_at"]))
        return [self._dashboard_task_payload(task) for task in items]

    def _upsert_notification(
        self,
        notification_id: str,
        title: str,
        body: str,
        icon: str,
        color: str,
        *,
        read: bool = False,
    ) -> None:
        existing = next((notification for notification in self._notifications if notification["id"] == notification_id), None)
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

    def _add_notification(self, title: str, body: str, icon: str, color: str) -> dict[str, Any]:
        notification = self._normalize_notification(
            {
                "id": f"notif-{uuid4().hex[:8]}",
                "title": title,
                "body": body,
                "icon": icon,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "read": False,
            }
        )
        self._notifications.insert(0, notification)
        self._notifications = self._notifications[:50]
        self._emit()
        return notification

    def _refresh_reminder_notifications(self) -> None:
        if self._alert_settings.get("overdue", True):
            overdue_count = len(self._tasks_for_bucket("overdue"))
            if overdue_count:
                self._upsert_notification(
                    f"smart-overdue-{self._today.isoformat()}",
                    f"{overdue_count} Overdue Review{'s' if overdue_count != 1 else ''}",
                    "Clear overdue material first to protect your recall schedule.",
                    "!",
                    "#EF4444",
                )
        if self._alert_settings.get("due_today", True):
            due_today = self._tasks_for_bucket("due_today")
            if due_today:
                next_task = due_today[0]
                self._upsert_notification(
                    f"smart-due-{self._today.isoformat()}",
                    "Today's Revision Queue",
                    f"{len(due_today)} review{'s' if len(due_today) != 1 else ''} due today. Start with {next_task['name']}.",
                    "T",
                    "#3B82F6",
                )
        if self._alert_settings.get("weekly_reports", True):
            self._upsert_notification(
                f"smart-weekly-{self._today.isocalendar().year}-{self._today.isocalendar().week}",
                "Weekly Report Ready",
                f"You logged {self._weekly_study_minutes()} minutes in recent sessions. Review your intelligence dashboard.",
                "R",
                "#8B5CF6",
                read=True,
            )

    @Property("QVariantList", notify=stateChanged)
    def dashboardStats(self) -> list[dict[str, Any]]:
        completed_today = len(
            [task for task in self._tasks if self._is_task_completed(task) and task["scheduled_at"].date() == self._today]
        )
        total_today = len([task for task in self._tasks if task["scheduled_at"].date() == self._today])
        avg_conf = round(sum(topic["confidence"] for topic in self._topics) / len(self._topics), 1) if self._topics else 0.0
        overdue_count = len(self._tasks_for_bucket("overdue"))
        completion_rate = round((completed_today / total_today) * 100) if total_today else 0
        return [
            {
                "title": "OVERDUE",
                "value": str(overdue_count),
                "subtitle": "Need attention",
                "trend": "High" if overdue_count else "Clear",
                "trendUp": overdue_count == 0,
                "valueColor": "#EF4444" if overdue_count else "#1A2332",
                "accentColor": "#EF4444",
            },
            {
                "title": "DUE TODAY",
                "value": str(total_today),
                "subtitle": "Scheduled reviews",
                "trend": f"{completed_today} done",
                "trendUp": True,
                "valueColor": "#1A2332",
                "accentColor": "#3B82F6",
            },
            {
                "title": "COMPLETION",
                "value": f"{completion_rate}%",
                "subtitle": "Today's pace",
                "trend": "On track" if completion_rate >= 50 else "Warm up",
                "trendUp": completion_rate >= 50,
                "valueColor": "#1A2332",
                "accentColor": "#10B981",
            },
            {
                "title": "AVG CONFIDENCE",
                "value": f"{avg_conf:.1f}/5",
                "subtitle": "Across topics",
                "trend": "Steady recall",
                "trendUp": avg_conf >= 3.5,
                "valueColor": "#1A2332",
                "accentColor": "#8B5CF6",
            },
        ]

    @Property("QVariantMap", notify=stateChanged)
    def dashboardBanner(self) -> dict[str, Any]:
        overdue = len(self._tasks_for_bucket("overdue"))
        due_today = len(self._tasks_for_bucket("due_today"))
        if overdue:
            return {
                "emoji": "!",
                "headline": f"{overdue} overdue review{'s' if overdue != 1 else ''} need attention first",
                "detail": "Clear the oldest cards before starting new material.",
            }
        return {
            "emoji": "•",
            "headline": f"{due_today} review{'s' if due_today != 1 else ''} queued for today",
            "detail": "Stay in rhythm with short, consistent revision sessions.",
        }

    @Property("QVariantMap", notify=stateChanged)
    def dashboardFocus(self) -> dict[str, Any]:
        due_items = self._tasks_for_bucket("due_today")
        top_item = due_items[0] if due_items else None
        avg_conf = round(sum(topic["confidence"] for topic in self._topics) / len(self._topics) * 20) if self._topics else 0
        return {
            "score": avg_conf,
            "nextRevision": top_item["name"] if top_item else "No due topics",
        }

    @Property("QVariantList", notify=stateChanged)
    def dashboardColumns(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "overdue",
                "title": "Overdue",
                "subtitle": "Start here first",
                "accentColor": "#EF4444",
                "count": len(self._tasks_for_bucket("overdue")),
                "items": self._tasks_for_bucket("overdue"),
            },
            {
                "key": "due_today",
                "title": "Due Today",
                "subtitle": "Today's core revision flow",
                "accentColor": "#3B82F6",
                "count": len(self._tasks_for_bucket("due_today")),
                "items": self._tasks_for_bucket("due_today"),
            },
            {
                "key": "upcoming",
                "title": "Upcoming",
                "subtitle": "Planned next reviews",
                "accentColor": "#64748B",
                "count": len(self._tasks_for_bucket("upcoming")),
                "items": self._tasks_for_bucket("upcoming"),
            },
        ]

    @Property("QVariantList", notify=stateChanged)
    def todayTasks(self) -> list[dict[str, Any]]:
        tasks = [task for task in self._tasks if task["scheduled_at"].date() == self._selected_date]
        if self._task_filter != "all":
            tasks = [task for task in tasks if self._task_bucket(task) == self._task_filter]
        return [self._task_payload(task) for task in tasks]

    @Property("QVariantList", notify=stateChanged)
    def inboxTasks(self) -> list[dict[str, Any]]:
        return self._inbox_tasks()

    @Property("QVariantList", notify=stateChanged)
    def taskFilters(self) -> list[dict[str, Any]]:
        items = [
            ("all", "All"),
            ("pending", "Pending"),
            ("overdue", "Overdue"),
            ("due_today", "Due Today"),
            ("upcoming", "Upcoming"),
            ("completed", "Completed"),
        ]
        return [
            {
                "key": key,
                "label": label,
                "active": self._task_filter == key,
                "count": len(
                    [
                        task
                        for task in self._tasks
                        if key == "all"
                        or (key == "pending" and not self._is_task_completed(task))
                        or (key not in {"all", "pending"} and self._task_bucket(task) == key)
                    ]
                ),
            }
            for key, label in items
        ]

    @Property("QVariantList", notify=stateChanged)
    def curriculumSubjects(self) -> list[dict[str, Any]]:
        subjects: dict[str, dict[str, Any]] = {}
        filtered_topics = self._filtered_topics()
        topic_lookup = {topic["id"]: topic for topic in filtered_topics}
        for topic in filtered_topics:
            subject = topic["subject"]
            if subject not in subjects:
                meta = self._subject_meta(subject)
                subjects[subject] = {
                    "subjectName": subject,
                    "iconText": meta.icon,
                    "accentColor": meta.color,
                    "topicCount": 0,
                    "topics": [],
                }
            subjects[subject]["topicCount"] += 1

        for topic in filtered_topics:
            if topic.get("parent_topic_id") is None:
                subjects[topic["subject"]]["topics"].append(self._topic_tree_node(topic, topic_lookup))

        return list(subjects.values())

    @Property("QVariantMap", notify=stateChanged)
    def curriculumSummary(self) -> dict[str, Any]:
        filtered_topics = self._filtered_topics()
        total = len(filtered_topics)
        avg = round(sum(topic["progress"] for topic in filtered_topics) / total, 1) if total > 0 else 0.0
        completed = len([topic for topic in filtered_topics if topic.get("is_completed")])
        subject_count = len({topic["subject"] for topic in filtered_topics})
        return {
            "total_topics": total,
            "avg_progress": avg,
            "stats": [
                {"label": "Subjects", "value": str(subject_count), "color": "#3B82F6"},
                {"label": "Topics", "value": str(total), "color": "#10B981"},
                {"label": "Completed", "value": str(completed), "color": "#F59E0B"},
                {"label": "Avg Progress", "value": f"{avg:.0f}%", "color": "#8B5CF6"},
            ],
        }

    @Property("QVariantList", notify=stateChanged)
    def weekCompletion(self) -> list[dict[str, Any]]:
        today = self._today
        start_of_week = today - timedelta(days=today.weekday())
        current_week = [start_of_week + timedelta(days=i) for i in range(7)]
        rows = []
        total_completed = 0
        total_scheduled = 0
        for day in current_week:
            day_tasks = [task for task in self._tasks if task["scheduled_at"].date() == day]
            completed = len([task for task in day_tasks if self._is_task_completed(task)])
            scheduled = len(day_tasks)
            total_completed += completed
            total_scheduled += scheduled
            rows.append(
                {
                    "day": day.strftime("%a"),
                    "date": day.strftime("%d"),
                    "completed": completed,
                    "scheduled": scheduled,
                    "remaining": max(0, scheduled - completed),
                    "isToday": day == today,
                }
            )
        score = round((total_completed / total_scheduled) * 100) if total_scheduled else 0
        for row in rows:
            row["score"] = score
        return rows

    @Property("QVariantList", notify=stateChanged)
    def dashboardWeekBars(self) -> list[int]:
        base = self._study_minutes[-7:] if len(self._study_minutes) >= 7 else self._study_minutes + [0] * (7 - len(self._study_minutes))
        peak = max(base) if base and max(base) > 0 else 1
        return [round((value / peak) * 100) for value in base]

    @Property("QVariantList", notify=stateChanged)
    def calendarCells(self) -> list[dict[str, Any]]:
        import calendar
        cal = calendar.Calendar(firstweekday=0)
        view_year = self._calendar_view_date.year
        view_month = self._calendar_view_date.month
        
        cells = []
        for week in cal.monthdatescalendar(view_year, view_month):
            for day in week:
                is_valid = (day.month == view_month)
                is_today = (day == self._today)
                is_selected = (day == self._selected_date)
                task_count = len([t for t in self._tasks if t["scheduled_at"].date() == day and not self._is_task_completed(t)])
                cells.append({
                    "dayNum": str(day.day) if is_valid else "",
                    "isValid": is_valid,
                    "isToday": is_today,
                    "isSelected": is_selected,
                    "taskCount": task_count,
                    "dateStr": day.isoformat()
                })
        
        while len(cells) < 42:
            cells.append({
                "dayNum": "",
                "isValid": False,
                "isToday": False,
                "isSelected": False,
                "taskCount": 0,
                "dateStr": ""
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
    def selectedDayLabel(self) -> str:
        return self._selected_date.strftime("%A, %d %B")

    @Property(str, notify=stateChanged)
    def selectedDate(self) -> str:
        return self._selected_date.isoformat()

    @Property("QVariantList", notify=stateChanged)
    def selectedDaySessions(self) -> list[dict[str, Any]]:
        tasks = [task for task in self._tasks if task["scheduled_at"].date() == self._selected_date]
        tasks.sort(key=lambda task: task["scheduled_at"])
        return [
            {
                "id": task["id"],
                "topic": task["topic"],
                "name": task["topic"],
                "subject": SUBJECT_DISPLAY_NAMES.get(task["subject"], task["subject"]),
                "duration": task["duration_minutes"],
                "time": task["scheduled_at"].strftime("%H:%M"),
                "durationText": f"{task['duration_minutes']} min",
                "color": self._subject_meta(task["subject"]).color,
                "subjectColor": self._subject_meta(task["subject"]).color,
                "status": self._task_payload(task)["status"],
                "completed": self._is_task_completed(task),
            }
            for task in tasks
        ]

    @Property(str, notify=stateChanged)
    def selectedDayTotalText(self) -> str:
        total_minutes = sum(session["duration"] for session in self.selectedDaySessions)
        return f"{total_minutes} min"

    @Property("QVariantMap", notify=stateChanged)
    def revisionWeekSummary(self) -> dict[str, Any]:
        weekly_rows = self.weekCompletion
        completed = sum(row["completed"] for row in weekly_rows)
        scheduled = sum(row["scheduled"] for row in weekly_rows)
        remaining = max(0, scheduled - completed)
        missed = len(
            [
                task
                for task in self._tasks
                if task["scheduled_at"].date() < self._today and not self._is_task_completed(task)
            ]
        )
        score = round((completed / scheduled) * 100) if scheduled else 0
        return {
            "completed": completed,
            "remaining": remaining,
            "missed": missed,
            "score": score,
            "scheduled": scheduled,
        }

    @Property("QVariantList", notify=stateChanged)
    def subjectConfidence(self) -> list[dict[str, Any]]:
        rows = []
        for subject, topics in self._subject_groups().items():
            meta = self._subject_meta(subject)
            rows.append(
                {
                    "subject": subject,
                    "pct": self._average_confidence_pct(topics),
                    "progress": self._average_progress(topics),
                    "topicCount": len(topics),
                    "color": meta.color,
                }
            )
        rows.sort(key=lambda row: (-row["pct"], row["subject"]))
        return rows

    @Property(str, notify=stateChanged)
    def taskFilter(self) -> str:
        return self._task_filter

    @Property("QVariantList", notify=stateChanged)
    def topicBalance(self) -> list[float]:
        grouped = {}
        for topic in self._topics:
            subject = topic["subject"]
            grouped.setdefault(subject, []).append(topic["progress"])
        ordered = ["Biology", "Mathematics", "Physics", "Chemistry", "History"]
        return [round(sum(grouped.get(name, [])) / (len(grouped.get(name, [])) * 100), 2) if grouped.get(name, []) else 0.0 for name in ordered]

    @Property(str, notify=stateChanged)
    def curriculumFilter(self) -> str:
        return self._curriculum_filter

    @Property(str, notify=stateChanged)
    def curriculumDifficulty(self) -> str:
        return self._curriculum_filter

    @Property(str, notify=stateChanged)
    def curriculumSearch(self) -> str:
        return self._curriculum_search

    @Property("QVariantList", notify=stateChanged)
    def curriculumSubjectOptions(self) -> list[dict]:
        return [{"id": s, "name": s} for s in self._subjects_from_topics()]

    @Slot(str)
    def setCurriculumSearch(self, text: str) -> None:
        if self._curriculum_search != text:
            self._curriculum_search = text
            self._emit()

    @Slot(str)
    def setCurriculumDifficulty(self, difficulty: str) -> None:
        value = difficulty if difficulty in {"All", "Easy", "Medium", "Hard"} else "All"
        if self._curriculum_filter != value:
            self._curriculum_filter = value
            self._emit()

    @Property("QVariantList", notify=stateChanged)
    def intelligenceStats(self) -> list[dict[str, Any]]:
        completed = len(self._completed_tasks())
        total_tasks = len(self._tasks)
        completion_rate = round((completed / total_tasks) * 100) if total_tasks else 0
        avg_progress = self._average_progress()
        confidence = self._average_confidence_pct()
        hard_topics = len([topic for topic in self._topics if topic["difficulty"] == "Hard" and topic["progress"] < 60])
        return [
            {
                "title": "WEEKLY FOCUS",
                "value": f"{self._weekly_study_minutes()}m",
                "subtitle": "last 7 sessions",
                "trend": "Active" if self._weekly_study_minutes() >= 180 else "Build",
                "trendUp": self._weekly_study_minutes() >= 180,
                "accentColor": "#3B82F6",
                "valueColor": "#1A2332",
            },
            {
                "title": "COMPLETION",
                "value": f"{completion_rate}%",
                "subtitle": f"{completed}/{total_tasks} tasks",
                "trend": "Healthy" if completion_rate >= 60 else "Low",
                "trendUp": completion_rate >= 60,
                "accentColor": "#10B981",
                "valueColor": "#1A2332",
            },
            {
                "title": "MASTERY",
                "value": f"{avg_progress:.0f}%",
                "subtitle": "avg topic progress",
                "trend": "Rising" if avg_progress >= 65 else "Needs reps",
                "trendUp": avg_progress >= 65,
                "accentColor": "#F59E0B",
                "valueColor": "#1A2332",
            },
            {
                "title": "RECALL",
                "value": f"{confidence}%",
                "subtitle": f"{hard_topics} hard weak spots",
                "trend": "Strong" if confidence >= 70 else "Review",
                "trendUp": confidence >= 70,
                "accentColor": "#8B5CF6",
                "valueColor": "#1A2332",
            },
        ]

    @Property("QVariantList", notify=stateChanged)
    def studyTrend(self) -> list[int]:
        return self._study_trend_values()

    @Property("QVariantList", notify=stateChanged)
    def studyTrendLabels(self) -> list[str]:
        start = self._today - timedelta(days=13)
        return [(start + timedelta(days=index)).strftime("%d %b") for index in range(14)]

    @Property("QVariantList", notify=stateChanged)
    def activityHeatmap(self) -> list[int]:
        trend = self._study_trend_values(14)
        cells = []
        for index in range(56):
            day = self._today - timedelta(days=55 - index)
            completed_for_day = len(
                [
                    task
                    for task in self._tasks
                    if self._is_task_completed(task) and task["scheduled_at"].date() == day
                ]
            )
            recent_minutes = trend[index - 42] if index >= 42 else 0
            cells.append(min(100, completed_for_day * 35 + recent_minutes))
        return cells

    @Property("QVariantList", notify=stateChanged)
    def analyticsSubjectRows(self) -> list[dict[str, Any]]:
        rows = []
        for row in self.subjectConfidence:
            weak_topics = [
                topic
                for topic in self._subject_groups().get(row["subject"], [])
                if topic["progress"] < 60 or topic["confidence"] <= 2
            ]
            rows.append(
                {
                    **row,
                    "risk": "High" if len(weak_topics) >= 2 else ("Medium" if weak_topics else "Low"),
                    "nextAction": "Revise weak topics" if weak_topics else "Maintain cadence",
                }
            )
        return rows

    @Property("QVariantList", notify=stateChanged)
    def intelligenceInsights(self) -> list[dict[str, Any]]:
        if not self._topics:
            return [
                {
                    "title": "Add Topics",
                    "body": "Import or create topics so StudyFlow can build personalized analytics.",
                    "color": "#3B82F6",
                    "severity": "Info",
                }
            ]

        weakest = min(self._topics, key=lambda topic: (topic["confidence"], topic["progress"]))
        strongest = max(self._topics, key=lambda topic: (topic["progress"], topic["confidence"]))
        overdue = len(self._tasks_for_bucket("overdue"))
        study_minutes = self._weekly_study_minutes()
        return [
            {
                "title": f"Prioritize {weakest['name']}",
                "body": f"{weakest['subject']} has low recall confidence. Schedule a short active-recall pass before adding new material.",
                "color": "#EF4444" if weakest["confidence"] <= 2 else "#F59E0B",
                "severity": "Focus",
            },
            {
                "title": "Clear Overdue Load",
                "body": f"{overdue} overdue review{'s' if overdue != 1 else ''} are influencing the recall score.",
                "color": "#EF4444" if overdue else "#10B981",
                "severity": "Schedule",
            },
            {
                "title": f"Keep {strongest['subject']} Warm",
                "body": f"{strongest['name']} is your strongest topic. Use lighter reviews to preserve retention without over-spending time.",
                "color": "#10B981",
                "severity": "Maintain",
            },
            {
                "title": "Weekly Study Rhythm",
                "body": f"You logged {study_minutes} minutes across the latest sessions. Aim for steady 25-minute blocks instead of one large catch-up.",
                "color": "#3B82F6",
                "severity": "Habit",
            },
        ]

    @Property("QVariantList", notify=stateChanged)
    def flashcardStats(self) -> list[dict[str, Any]]:
        due_today = len(
            [
                task
                for task in self._tasks
                if not self._is_task_completed(task) and task["scheduled_at"].date() == self._today
            ]
        )
        mastered = len([topic for topic in self._topics if topic["progress"] >= PROGRESS_MASTERED])
        total = len(self._topics)
        return [
            {"label": "Due Today", "value": due_today * 4, "color": "#3B82F6"},
            {"label": "Mastered", "value": mastered * 6, "color": "#10B981"},
            {"label": "Total", "value": total * 2, "color": "#F59E0B"},
        ]

    @Property("QVariantList", notify=stateChanged)
    def settingsColumns(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "Notifications",
                "rows": [
                    {
                        "label": "Push Alerts",
                        "key": "notifications",
                        "kind": "toggle",
                        "toggleOn": bool(self._settings.get("notifications", True)),
                    },
                    {
                        "label": "Reminders",
                        "key": "reminders",
                        "kind": "toggle",
                        "toggleOn": bool(self._settings.get("reminders", True)),
                    },
                    {
                        "label": "Auto Schedule",
                        "key": "auto_schedule",
                        "kind": "toggle",
                        "toggleOn": bool(self._settings.get("auto_schedule", True)),
                    },
                ],
            },
            {
                "title": "Cloud Sync",
                "rows": [
                    {
                        "label": "Cloud Sync",
                        "key": "cloud_sync",
                        "kind": "toggle",
                        "toggleOn": bool(self._sync_settings.get("enabled", False)),
                    },
                    {"label": "Status", "value": self.syncStatus["label"], "kind": "value", "valueColor": self.syncStatus["color"]},
                    {"label": "Device", "value": self._sync_settings["device_id"], "kind": "value"},
                    {"label": "Last Sync", "value": self._sync_settings.get("last_sync_at") or "Never", "kind": "value"},
                ],
            },
        ]

    @Property("QVariantList", notify=stateChanged)
    def alertSettingsRows(self) -> list[dict[str, Any]]:
        return self.alertSettings

    @Property("QVariantList", notify=stateChanged)
    def notifications(self) -> list[dict[str, Any]]:
        normalized = [self._normalize_notification(notification, index) for index, notification in enumerate(self._notifications)]
        normalized.sort(key=lambda notification: notification["timestamp"], reverse=True)
        return normalized

    @Property("QVariantMap", notify=stateChanged)
    def userSettings(self) -> dict[str, Any]:
        return self._settings

    @Property("QVariantList", notify=stateChanged)
    def alertSettings(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "label": ALERT_SETTING_META[key][0],
                "description": ALERT_SETTING_META[key][1],
                "color": ALERT_SETTING_META[key][2],
                "on": bool(self._alert_settings.get(key, False)),
            }
            for key in ALERT_SETTING_META
        ]

    @Property("QVariantMap", notify=stateChanged)
    def todayDigest(self) -> dict[str, Any]:
        overdue = self._tasks_for_bucket("overdue")
        due_today = self._tasks_for_bucket("due_today")
        completed_today = len(
            [task for task in self._tasks if self._is_task_completed(task) and task["scheduled_at"].date() == self._today]
        )
        if overdue:
            summary = f"{len(overdue)} overdue review{'s' if len(overdue) != 1 else ''} need attention first."
        elif due_today:
            summary = f"{len(due_today)} review{'s' if len(due_today) != 1 else ''} are queued for today."
        else:
            summary = "No urgent revisions right now. Keep your streak warm with a light review."
        next_task = due_today[0] if due_today else (self._tasks_for_bucket("upcoming")[0] if self._tasks_for_bucket("upcoming") else None)
        return {
            "summary": summary,
            "nextSession": (
                f"Next session: {next_task['name']} for {next_task['durationMinutes']} min"
                if next_task
                else "No sessions scheduled."
            ),
            "completedToday": completed_today,
            "unread": len([notification for notification in self.notifications if not notification.get("read", False)]),
        }

    @Property("QVariantList", notify=stateChanged)
    def notificationStats(self) -> list[dict[str, Any]]:
        notifications = self.notifications
        unread = len([notification for notification in notifications if not notification.get("read", False)])
        overdue = len(self._tasks_for_bucket("overdue"))
        due_today = len(self._tasks_for_bucket("due_today"))
        return [
            {"label": "Unread", "value": str(unread), "color": "#3B82F6"},
            {"label": "Overdue", "value": str(overdue), "color": "#EF4444"},
            {"label": "Due Today", "value": str(due_today), "color": "#F59E0B"},
        ]

    @Property("QVariantList", notify=stateChanged)
    def upcomingReminders(self) -> list[dict[str, Any]]:
        tasks = [task for task in self._tasks if not self._is_task_completed(task)]
        tasks.sort(key=lambda task: task["scheduled_at"])
        return [
            {
                "id": task["id"],
                "title": task["topic"],
                "subject": task["subject"],
                "when": self._task_payload(task)["scheduledText"],
                "color": self._subject_meta(task["subject"]).color,
            }
            for task in tasks[:5]
        ]

    @Property("QVariantMap", notify=stateChanged)
    def reminderPreferences(self) -> dict[str, Any]:
        next_run = datetime.combine(self._today, time.fromisoformat(self._reminder_preferences["notification_time"]))
        if next_run <= datetime.now():
            next_run += timedelta(days=1)
        return {
            **self._reminder_preferences,
            "next_run": next_run.strftime("%d %b, %H:%M"),
            "summary": (
                f"Daily check at {self._reminder_preferences['notification_time']}, "
                f"alert when {self._reminder_preferences['minimum_due_for_alert']}+ topic is due."
            ),
        }

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
            {"label": "Exam Check", "prompt": "Am I on track for my exam?"},
            {"label": "Weakest Area", "prompt": "Which subject needs the most attention?"},
        ]

    @Property("QVariantMap", notify=stateChanged)
    def assistantContextSummary(self) -> dict[str, Any]:
        context = self._assistant_context()
        return {
            "dueToday": len(context.due_today),
            "overdue": len(context.overdue),
            "weakSubjects": len([subject for subject in context.weak_subjects if subject.get("risk") != "Low"]),
            "nextTopic": (
                context.overdue[0]["name"]
                if context.overdue
                else (context.due_today[0]["name"] if context.due_today else "No due topics")
            ),
        }

    @Property("QVariantMap", notify=stateChanged)
    def syncStatus(self) -> dict[str, Any]:
        self._sync_service = SyncService(self._sync_config())
        return self._sync_service.status(self._sync_state())

    @Property("QVariantMap", notify=stateChanged)
    def syncSettings(self) -> dict[str, Any]:
        return {
            "enabled": bool(self._sync_settings.get("enabled", False)),
            "supabaseUrl": self._sync_settings.get("supabase_url", ""),
            "anonKeyConfigured": bool(self._sync_settings.get("supabase_anon_key", "")),
            "deviceId": self._sync_settings["device_id"],
            "lastSyncAt": self._sync_settings.get("last_sync_at") or "Never",
        }

    @Property("QVariantList", notify=stateChanged)
    def syncHistory(self) -> list[dict[str, Any]]:
        return sorted(self._sync_history, key=lambda item: item["created_at"], reverse=True)[:10]

    @Slot(str)
    def markTaskDone(self, task_id: str) -> None:
        task = self._find_task(task_id)
        if task:
            task["completed"] = True
            task["status"] = "completed"
            task["completed_at"] = datetime.now()
            self._study_minutes.append(task["duration_minutes"])
            self._study_minutes = self._study_minutes[-14:]
            topic = self._find_topic(task["topic"])
            if topic is not None:
                topic["progress"] = min(100, topic["progress"] + 5)
                topic["confidence"] = max(topic["confidence"], min(CONFIDENCE_MAX, int(task["confidence"])))
            self._save()
            self._emit()

    @Slot(str, str, str, str)
    def addTask(self, topic_name: str, subject: str, difficulty: str, schedule_key: str) -> None:
        clean_name = topic_name.strip()
        clean_subject = subject.strip() or "General"
        clean_difficulty = difficulty if difficulty in {"Easy", "Medium", "Hard"} else "Medium"
        if not clean_name:
            return

        schedule_offsets = {
            "overdue": -1,
            "today": 0,
            "tomorrow": 1,
            "this_week": 3,
        }
        offset_days = schedule_offsets.get(schedule_key, 0)
        self._ensure_topic_for_task(clean_name, clean_subject, clean_difficulty)
        topic = self._find_topic(clean_name)
        confidence = int(topic["confidence"]) if topic is not None else 3
        self._tasks.append(
            self._create_task(
                topic_name=clean_name,
                subject=clean_subject,
                difficulty=clean_difficulty,
                confidence=confidence,
                offset_days=offset_days,
            )
        )
        self._save()
        self._emit()
        self._add_notification(
            "Task Added",
            f"{clean_name} was scheduled for {schedule_key.replace('_', ' ')}.",
            "+",
            "#3B82F6",
        )

    @Slot(str)
    def skipTask(self, task_id: str) -> None:
        task = self._find_task(task_id)
        if task is None or self._is_task_completed(task):
            return
        task["scheduled_at"] = task["scheduled_at"] + timedelta(days=1)
        task["status"] = "pending"
        self._save()
        self._emit()

    @Slot()
    def markAllTasksDone(self) -> None:
        changed = False
        visible_ids = {item["id"] for item in self._inbox_tasks()}
        for task in self._tasks:
            if task["id"] not in visible_ids or self._is_task_completed(task):
                continue
            task["completed"] = True
            task["status"] = "completed"
            task["completed_at"] = datetime.now()
            self._study_minutes.append(task["duration_minutes"])
            changed = True
        if not changed:
            return
        self._study_minutes = self._study_minutes[-14:]
        self._save()
        self._emit()

    @Slot()
    def startSession(self) -> None:
        self._add_notification(
            "Session Started",
            "Dashboard quick-start launched. Pick a due topic and rate it when you finish.",
            "play_arrow",
            "#3B82F6",
        )

    @Slot(str, int)
    def completeRevision(self, task_id: str, rating: int) -> None:
        task = self._find_task(task_id)
        if task is None:
            return

        safe_rating = min(max(int(rating), 1), 4)
        task["completed"] = True
        task["status"] = "completed"
        task["completed_at"] = datetime.now()
        task["confidence"] = safe_rating + 1 if safe_rating < 4 else 5
        self._study_minutes.append(task["duration_minutes"])
        self._study_minutes = self._study_minutes[-14:]

        topic = self._find_topic(task["topic"])
        if topic is not None:
            topic["confidence"] = RATING_CONFIDENCE[safe_rating]
            topic["progress"] = min(100, max(0, topic["progress"] + RATING_PROGRESS_BOOST[safe_rating]))

        self._save()
        self._emit()
        self._add_notification(
            "Revision Logged",
            f"{task['topic']} marked complete with rating {RATING_LABELS[safe_rating]}.",
            "check_circle",
            "#10B981",
        )

    @Slot(str, str)
    def addSubject(self, name: str, color_tag: str) -> None:
        clean_name = name.strip()
        if not clean_name or clean_name in self._subjects_from_topics():
            return
        clean_color = color_tag.strip() or "#3B82F6"
        SUBJECTS[clean_name] = SubjectMeta(clean_name[:1].upper(), clean_color)
        self._save()
        self._emit()
        self._add_notification(
            "Subject Added",
            f'"{clean_name}" is now available for topic planning.',
            "+",
            clean_color,
        )

    @Slot(str, str, str, str, str, str)
    def upsertTopic(
        self,
        topic_id: str,
        name: str,
        subject: str,
        difficulty: str,
        parent_topic_id: str,
        notes: str,
    ) -> None:
        clean_name = name.strip()
        clean_subject = subject.strip() or "General"
        if not clean_name or not clean_subject:
            return
        clean_difficulty = difficulty if difficulty in {"Easy", "Medium", "Hard"} else "Medium"
        clean_notes = notes.strip()
        clean_parent = parent_topic_id.strip() or None

        topic = self._find_topic_by_id(topic_id) if topic_id else None
        if topic is None:
            if any(existing["name"].casefold() == clean_name.casefold() and existing["subject"] == clean_subject for existing in self._topics):
                return
            topic = self._normalize_topic(
                {
                    "id": f"topic-{uuid4().hex[:8]}",
                    "name": clean_name,
                    "subject": clean_subject,
                    "difficulty": clean_difficulty,
                    "notes": clean_notes,
                    "parent_topic_id": clean_parent,
                }
            )
            self._topics.append(topic)
            self._tasks.append(self._build_task_for_topic(topic))
            notification_title = "Topic Added"
            notification_body = f'"{clean_name}" was added under {clean_subject}.'
        else:
            previous_name = topic["name"]
            if any(
                existing["id"] != topic["id"]
                and existing["subject"] == clean_subject
                and existing["name"].casefold() == clean_name.casefold()
                for existing in self._topics
            ):
                return
            topic["name"] = clean_name
            topic["subject"] = clean_subject
            topic["difficulty"] = clean_difficulty
            topic["notes"] = clean_notes
            topic["parent_topic_id"] = clean_parent
            related_task = next((task for task in self._tasks if task["topic"] == previous_name), None)
            if related_task is not None:
                related_task["topic"] = clean_name
                related_task["subject"] = clean_subject
                related_task["difficulty"] = topic["difficulty"]
                related_task["duration_minutes"] = {"Easy": 15, "Medium": 25, "Hard": 35}[topic["difficulty"]]
            notification_title = "Topic Updated"
            notification_body = f'"{clean_name}" was updated in {clean_subject}.'

        self._save()
        self._emit()
        self._add_notification(
            notification_title,
            notification_body,
            "+",
            self._subject_meta(clean_subject).color,
        )

    @Slot(str)
    def deleteTopic(self, topic_id: str) -> None:
        topic = self._find_topic_by_id(topic_id)
        if topic is None:
            return
        removed_ids = {topic_id}
        changed = True
        while changed:
            changed = False
            for candidate in self._topics:
                if candidate.get("parent_topic_id") in removed_ids and candidate["id"] not in removed_ids:
                    removed_ids.add(candidate["id"])
                    changed = True
        removed_names = {item["name"] for item in self._topics if item["id"] in removed_ids}
        self._topics = [item for item in self._topics if item["id"] not in removed_ids]
        self._tasks = [task for task in self._tasks if task["topic"] not in removed_names]
        self._save()
        self._emit()

    @Slot(str)
    def markTopicComplete(self, topic_id: str) -> None:
        topic = self._find_topic_by_id(topic_id)
        if topic is None:
            return
        topic["is_completed"] = True
        topic["completion_date"] = self._today.isoformat()
        related_task = next((task for task in self._tasks if task["topic"] == topic["name"]), None)
        if related_task is not None:
            related_task["completed"] = True
            related_task["completed_at"] = datetime.now()
            related_task["status"] = "completed"
        self._save()
        self._emit()

    @Slot(str, result="QVariantMap")
    def suggestTopicDifficulty(self, topic_name: str) -> dict[str, Any]:
        clean_name = topic_name.strip()
        if not clean_name:
            return {"difficulty": "", "confidence": 0.0, "source": "empty"}
        prediction = self._nlp_service.predict_difficulty(clean_name)
        if prediction.difficulty is None:
            return {"difficulty": "", "confidence": round(prediction.confidence, 2), "source": prediction.source}
        return {
            "difficulty": prediction.difficulty.value.capitalize(),
            "confidence": round(prediction.confidence, 2),
            "source": prediction.source,
        }

    @Slot(str, str, bool)
    def importTopics(self, raw_text: str, subject: str, csv_mode: bool) -> None:
        clean_subject = subject.strip() or "General"
        if not raw_text.strip() or not clean_subject:
            return

        entries: list[str] = []
        if csv_mode:
            reader = csv.reader(StringIO(raw_text))
            for row in reader:
                if row and row[0].strip():
                    entries.append(row[0].strip())
        else:
            entries = [line.strip() for line in raw_text.splitlines() if line.strip()]

        existing_names = {
            (topic["subject"], topic["name"].casefold())
            for topic in self._topics
        }
        added = 0
        for entry in entries:
            key = (clean_subject, entry.casefold())
            if key in existing_names:
                continue
            suggestion = self.suggestTopicDifficulty(entry)
            topic = self._normalize_topic(
                {
                    "id": f"topic-{uuid4().hex[:8]}",
                    "name": entry,
                    "subject": clean_subject,
                    "difficulty": suggestion["difficulty"] or "Medium",
                    "notes": "",
                }
            )
            self._topics.append(topic)
            self._tasks.append(self._build_task_for_topic(topic))
            existing_names.add(key)
            added += 1

        if not added:
            return

        self._save()
        self._emit()
        self._add_notification(
            "Bulk Import",
            f"{added} topic{'s' if added != 1 else ''} imported under {clean_subject}.",
            "+",
            self._subject_meta(clean_subject).color,
        )

    @Slot(str)
    def setTaskFilter(self, filter: str) -> None:
        self._task_filter = filter
        self._emit()

    @Slot(str)
    def setCurriculumFilter(self, filter: str) -> None:
        self._curriculum_filter = filter
        self._emit()

    @Slot()
    def acceptSuggestion(self) -> None:
        # Find the "Calculus" task instead of hardcoded ID
        task = next((t for t in self._tasks if t.get("topic") == "Calculus"), None)
        if task:
            task["completed"] = True
            task["status"] = "completed"
            task["completed_at"] = datetime.now()
            self._study_minutes.append(task["duration_minutes"])
            self._study_minutes = self._study_minutes[-14:]
            self._save()
            self._emit()
            self._add_notification("Suggestion Accepted", "Calculus task completed!", "check_circle", "green")

    @Slot()
    def dismissSuggestion(self) -> None:
        self._suggestion_dismissed = True
        self._save()
        self._emit()

    @Slot(int)
    @Slot(str)
    def toggleSetting(self, index: int | str) -> None:
        keys = ["notifications", "reminders", "auto_schedule"]
        if str(index) == "cloud_sync":
            self.toggleCloudSync()
            return
        key = keys[index] if isinstance(index, int) and 0 <= index < len(keys) else str(index)
        if key in keys:
            self._settings[key] = not self._settings[key]
            self._save()
            self._emit()

    @Slot(int)
    @Slot(str)
    def toggleAlertSetting(self, index: int | str) -> None:
        keys = list(ALERT_SETTING_META)
        key = keys[index] if isinstance(index, int) and 0 <= index < len(keys) else str(index)
        if key in self._alert_settings:
            self._alert_settings[key] = not self._alert_settings[key]
            self._refresh_reminder_notifications()
            self._save()
            self._emit()

    @Slot(int)
    def changeCalendarMonth(self, offset: int) -> None:
        import calendar
        new_month = self._calendar_view_date.month + offset - 1
        new_year = self._calendar_view_date.year + new_month // 12
        new_month = new_month % 12 + 1
        max_days = calendar.monthrange(new_year, new_month)[1]
        new_day = min(self._calendar_view_date.day, max_days)
        self._calendar_view_date = self._calendar_view_date.replace(year=new_year, month=new_month, day=new_day)
        self._emit()

    @Slot()
    def goToToday(self) -> None:
        self._selected_date = self._today
        self._calendar_view_date = self._today
        self._emit()

    @Slot()
    def selectToday(self) -> None:
        self._selected_date = self._today
        self._emit()

    @Slot()
    def selectTomorrow(self) -> None:
        self._selected_date = self._today + timedelta(days=1)
        self._emit()

    @Slot(str)
    def selectCalendarDay(self, date_str: str) -> None:
        try:
            self._selected_date = date.fromisoformat(date_str)
            self._emit()
        except ValueError:
            pass  # Ignore invalid dates

    @Slot()
    def clearNotifications(self) -> None:
        self._notifications.clear()
        self._save()
        self._emit()

    @Slot()
    def markAllNotificationsRead(self) -> None:
        for notification in self._notifications:
            notification["read"] = True
        self._save()
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
        self._save()
        self._emit()

    @Slot(result=int)
    def runReminderCheck(self) -> int:
        preferences = self._reminder_preferences_model()
        if not preferences.enabled:
            return 0

        created = 0
        summary = build_morning_summary(
            self._tasks_for_bucket("due_today"),
            self._tasks_for_bucket("overdue"),
            preferences.minimum_due_for_alert,
        )
        if summary is not None and self._alert_settings.get("due_today", True):
            self._add_notification(summary["title"], summary["body"], summary["icon"], summary["color"])
            created += 1
            if preferences.desktop_notifications:
                self._desktop_notifier.notify(summary["title"], summary["body"])

        for warning in build_exam_warnings(self._topics, self._today):
            self._add_notification(warning["title"], warning["body"], warning["icon"], warning["color"])
            created += 1
            if preferences.desktop_notifications:
                self._desktop_notifier.notify(warning["title"], warning["body"])

        if created:
            self._save()
        return created

    @Slot(str, str)
    def updateReminderPreference(self, key: str, value: str) -> None:
        if key not in self._reminder_preferences:
            return
        if key in {"enabled", "desktop_notifications"}:
            self._reminder_preferences[key] = value.lower() in {"1", "true", "yes", "on"}
        elif key == "minimum_due_for_alert":
            try:
                self._reminder_preferences[key] = max(1, int(value))
            except ValueError:
                return
        elif key == "notification_time":
            try:
                time.fromisoformat(value)
            except ValueError:
                return
            self._reminder_preferences[key] = value
        self._save()
        self._emit()

    @Slot(result=str)
    def exportCalendar(self) -> str:
        export_path = Path(__file__).resolve().parent.parent / "data" / "studyflow_revisions.ics"
        write_revision_calendar(self._tasks, export_path)
        self._add_notification(
            "Calendar Export Ready",
            f"Saved upcoming revision sessions to {export_path.name}.",
            "CAL",
            "#3B82F6",
        )
        self._save()
        return str(export_path)

    @Slot(str, result="QVariantMap")
    def sendAssistantMessage(self, prompt: str) -> dict[str, Any]:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return {"text": "", "source": "empty"}

        user_message = self._normalize_assistant_message(
            {"role": "user", "text": clean_prompt, "source": "user", "timestamp": datetime.now()}
        )
        self._assistant_messages.append(user_message)
        response = self._llm_service.answer(clean_prompt, self._assistant_context())
        assistant_message = self._normalize_assistant_message(
            {
                "role": "assistant",
                "text": response["text"],
                "source": response["source"],
                "timestamp": datetime.now(),
            }
        )
        self._assistant_messages.append(assistant_message)
        self._assistant_messages = self._assistant_messages[-40:]
        self._save()
        self._emit()
        return assistant_message

    @Slot()
    def clearAssistantChat(self) -> None:
        self._assistant_messages = self._default_assistant_messages()
        self._save()
        self._emit()

    @Slot()
    def saveSettings(self) -> None:
        self._save()
        self._add_notification("Settings Saved", "Your StudyFlow preferences were saved.", "OK", "#10B981")

    @Slot()
    def clearHistory(self) -> None:
        self._study_minutes.clear()
        self._notifications.clear()
        self._save()
        self._emit()

    @Slot()
    def toggleCloudSync(self) -> None:
        self._sync_settings["enabled"] = not bool(self._sync_settings.get("enabled", False))
        self._sync_service = SyncService(self._sync_config())
        self._save()
        self._emit()

    @Slot(str, str)
    def updateSyncSetting(self, key: str, value: str) -> None:
        if key not in {"supabase_url", "supabase_anon_key"}:
            return
        self._sync_settings[key] = value.strip()
        self._sync_service = SyncService(self._sync_config())
        self._save()
        self._emit()

    @Slot(result="QVariantMap")
    def forceFullSync(self) -> dict[str, Any]:
        self._sync_service = SyncService(self._sync_config())
        self._mark_all_local_records_pending()
        result = self._sync_service.sync(self._sync_state())
        if result.synced_at:
            self._sync_settings["last_sync_at"] = result.synced_at
        history_item = self._normalize_sync_history(
            {
                "status": result.status,
                "message": result.message,
                "pushed": result.pushed,
                "pulled": result.pulled,
                "conflicts": result.conflicts,
                "created_at": datetime.now().isoformat(),
            }
        )
        self._sync_history.insert(0, history_item)
        self._sync_history = self._sync_history[:20]
        self._save()
        self._emit()
        notification = self._add_notification("Sync Updated", result.message, "SYNC", self.syncStatus["color"])
        if result.status == "synced":
            notification["sync_status"] = "synced"
            notification["last_synced_at"] = result.synced_at
            self._save()
            self._emit()
        return history_item

    @Slot(result=str)
    def exportLearningReport(self) -> str:
        export_dir = Path(__file__).resolve().parent.parent / "data"
        export_dir.mkdir(parents=True, exist_ok=True)
        report_path = export_dir / "learning_report.txt"
        stats = {item["title"]: item["value"] for item in self.intelligenceStats}
        insights = "\n".join(f"- {item['title']}: {item['body']}" for item in self.intelligenceInsights)
        subjects = "\n".join(
            f"- {row['subject']}: confidence {row['pct']}%, progress {row['progress']}%, risk {row['risk']}"
            for row in self.analyticsSubjectRows
        )
        report_path.write_text(
            "\n".join(
                [
                    "StudyFlow Learning Report",
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "",
                    "Summary",
                    f"- Weekly focus: {stats.get('WEEKLY FOCUS', '0m')}",
                    f"- Completion: {stats.get('COMPLETION', '0%')}",
                    f"- Mastery: {stats.get('MASTERY', '0%')}",
                    f"- Recall: {stats.get('RECALL', '0%')}",
                    "",
                    "Subject Health",
                    subjects or "- No subjects yet",
                    "",
                    "Insights",
                    insights or "- No insights yet",
                ]
            ),
            encoding="utf-8",
        )
        self._add_notification(
            "Learning Report Exported",
            f"Saved analytics report to {report_path.name}.",
            "R",
            "#8B5CF6",
        )
        return str(report_path)
"""
