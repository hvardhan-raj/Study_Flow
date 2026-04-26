from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from models import Revision, Subject, Topic
from studyflow_backend.models import SubjectMeta
from studyflow_backend.presenters import difficulty_color, task_payload

CONFIDENCE_MAX = 5
DIFFICULTY_TO_DURATION = {"Easy": 15, "Medium": 30, "Hard": 45}


class StudyFlowReadModel:
    """Read-side view model for QML projections."""

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any],
        today_provider: Callable[[], date],
        curriculum_filter_provider: Callable[[], str],
        curriculum_search_provider: Callable[[], str],
        study_minutes_provider: Callable[[], list[int]],
    ) -> None:
        self._db_factory = db_factory
        self._today_provider = today_provider
        self._curriculum_filter_provider = curriculum_filter_provider
        self._curriculum_search_provider = curriculum_search_provider
        self._study_minutes_provider = study_minutes_provider

    @property
    def today(self) -> date:
        return self._today_provider()

    def _normalized_subject_color(self, color: str) -> str:
        value = str(color or "").strip() or "#64748B"
        if not value.startswith("#") or len(value) != 7:
            return "#64748B"
        try:
            red = int(value[1:3], 16)
            green = int(value[3:5], 16)
            blue = int(value[5:7], 16)
        except ValueError:
            return "#64748B"

        luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
        if luminance <= 165:
            return value

        scale = 165 / max(luminance, 1)
        red = max(0, min(255, round(red * scale)))
        green = max(0, min(255, round(green * scale)))
        blue = max(0, min(255, round(blue * scale)))
        return f"#{red:02X}{green:02X}{blue:02X}"

    def subject_meta(self, subject: Subject | None = None, *, name: str = "", color: str = "#64748B") -> SubjectMeta:
        label = subject.name if subject is not None else name
        shade = subject.color if subject is not None else color
        words = [part[:1] for part in label.split() if part]
        return SubjectMeta(("".join(words)[:2] or "?").upper(), self._normalized_subject_color(shade))

    def difficulty_label(self, difficulty: Any) -> str:
        value = difficulty.value if hasattr(difficulty, "value") else difficulty
        return str(value).capitalize()

    def progress_for_topic(self, topic: Topic) -> int:
        return max(0, min(int(round(topic.mastery_score or 0)), 100))

    def confidence_for_topic(self, topic: Topic) -> int:
        mastery = max(0.0, min(float(topic.mastery_score or 0.0), 100.0))
        difficulty_penalty = {"easy": 0, "medium": 0.35, "hard": 0.7}.get(str(topic.difficulty).lower(), 0.35)
        score = round((mastery / 25.0) + 1 - difficulty_penalty)
        return max(1, min(score, CONFIDENCE_MAX))

    def serialize_topic(self, topic: Topic) -> dict[str, Any]:
        description = topic.description or ""
        description_lines = description.splitlines()
        parent_topic_id = None
        notes = description
        if description_lines:
            first_line = description_lines[0].strip()
            if first_line.startswith("[parent:") and first_line.endswith("]"):
                parent_topic_id = first_line[len("[parent:"):-1].strip() or None
                notes = "\n".join(description_lines[1:]).strip()
        meta = self.subject_meta(topic.subject)
        exam_date_value = topic.exam_date_override or topic.subject.exam_date
        exam_date = exam_date_value.isoformat() if exam_date_value else ""
        completion_date = topic.last_reviewed_at.date().isoformat() if topic.status == "completed" and topic.last_reviewed_at else ""
        difficulty = self.difficulty_label(topic.difficulty)
        return {
            "id": topic.id,
            "subjectId": topic.subject_id,
            "subject": topic.subject.name,
            "name": topic.name,
            "difficulty": difficulty,
            "difficultyColor": difficulty_color(difficulty),
            "progress": self.progress_for_topic(topic),
            "confidence": self.confidence_for_topic(topic),
            "notes": notes,
            "parent_topic_id": int(parent_topic_id) if parent_topic_id else None,
            "exam_date": exam_date,
            "examDate": exam_date,
            "completion_date": completion_date,
            "completionDate": completion_date,
            "is_completed": topic.status == "completed",
            "isCompleted": topic.status == "completed",
            "subjectMeta": {"icon": meta.icon, "color": meta.color},
        }

    def serialize_task(self, revision: Revision) -> dict[str, Any]:
        topic = revision.topic
        difficulty = self.difficulty_label(topic.difficulty)
        return {
            "id": revision.id,
            "topic_id": topic.id,
            "topic": topic.name,
            "subject_id": topic.subject_id,
            "subject": topic.subject.name,
            "difficulty": difficulty,
            "scheduled_at": revision.due_at,
            "confidence": self.confidence_for_topic(topic),
            "duration_minutes": topic.estimated_minutes or DIFFICULTY_TO_DURATION.get(difficulty, 30),
            "completed_at": revision.completed_at,
            "status": revision.status,
            "completed": revision.status != "open",
        }

    def all_topics(self) -> list[dict[str, Any]]:
        with self._db_factory() as db:
            stmt = select(Topic).options(joinedload(Topic.subject)).order_by(Topic.created_at, Topic.name)
            return [self.serialize_topic(topic) for topic in db.scalars(stmt)]

    def all_revisions(self) -> list[Revision]:
        with self._db_factory() as db:
            stmt = (
                select(Revision)
                .options(joinedload(Revision.topic).joinedload(Topic.subject))
                .order_by(Revision.due_at, Revision.created_at)
            )
            return list(db.scalars(stmt))

    def task_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        with self._db_factory() as db:
            subject = db.get(Subject, task["subject_id"])
            meta = self.subject_meta(subject, name=task["subject"])
        return task_payload(self.today, meta, task)

    def task_bucket(self, task: dict[str, Any]) -> str:
        if task["completed"]:
            return "completed"
        day = task["scheduled_at"].date()
        if day < self.today:
            return "overdue"
        if day == self.today:
            return "due_today"
        return "upcoming"

    def compute_urgency_score(self, task: dict[str, Any]) -> int:
        days_delta = (task["scheduled_at"].date() - self.today).days
        difficulty_weight = {"Easy": 8, "Medium": 16, "Hard": 24}.get(task["difficulty"], 10)
        confidence_penalty = max(0, 6 - int(task["confidence"])) * 5
        overdue_bonus = 0 if days_delta >= 0 else abs(days_delta) * 30
        due_today_bonus = 18 if days_delta == 0 else 0
        upcoming_decay = max(0, 12 - max(days_delta, 0) * 3)
        return difficulty_weight + confidence_penalty + overdue_bonus + due_today_bonus + upcoming_decay

    def dashboard_task_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        payload = self.task_payload(task)
        payload["urgencyScore"] = self.compute_urgency_score(task)
        payload["isCompleted"] = bool(task["completed"])
        payload["bucket"] = self.task_bucket(task)
        payload["confidenceLabel"] = f"Confidence {task['confidence']}/{CONFIDENCE_MAX}"
        return payload

    def tasks(self) -> list[dict[str, Any]]:
        return [self.serialize_task(revision) for revision in self.all_revisions()]

    def _mix_subjects(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = {}
        subject_order: list[str] = []
        for task in tasks:
            subject = str(task["subject"])
            if subject not in buckets:
                buckets[subject] = []
                subject_order.append(subject)
            buckets[subject].append(task)

        if len(subject_order) <= 1:
            return tasks

        mixed: list[dict[str, Any]] = []
        while True:
            added = False
            for subject in list(subject_order):
                queue = buckets.get(subject, [])
                if not queue:
                    continue
                mixed.append(queue.pop(0))
                added = True
            if not added:
                break
        return mixed

    def tasks_for_bucket(self, bucket: str) -> list[dict[str, Any]]:
        items = [task for task in self.tasks() if self.task_bucket(task) == bucket]
        items.sort(key=lambda task: (-self.compute_urgency_score(task), task["scheduled_at"]))
        if bucket in {"due_today", "upcoming"}:
            items = self._mix_subjects(items)
        return [self.dashboard_task_payload(task) for task in items]

    def filtered_topics(self) -> list[dict[str, Any]]:
        topics = self.all_topics()
        curriculum_filter = self._curriculum_filter_provider()
        curriculum_search = self._curriculum_search_provider()
        if curriculum_filter != "All":
            topics = [topic for topic in topics if topic["difficulty"] == curriculum_filter]
        if curriculum_search:
            needle = curriculum_search.lower()
            topics = [topic for topic in topics if needle in topic["name"].lower() or needle in topic["subject"].lower()]
        return topics

    def subject_groups(self) -> dict[str, list[dict[str, Any]]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for topic in self.all_topics():
            groups.setdefault(topic["subject"], []).append(topic)
        return groups

    def average_progress(self, topics: list[dict[str, Any]] | None = None) -> float:
        items = topics if topics is not None else self.all_topics()
        return round(sum(topic["progress"] for topic in items) / len(items), 1) if items else 0.0

    def average_confidence_pct(self, topics: list[dict[str, Any]] | None = None) -> int:
        items = topics if topics is not None else self.all_topics()
        return round(sum(topic["confidence"] for topic in items) / (len(items) * CONFIDENCE_MAX) * 100) if items else 0

    def weekly_study_minutes(self) -> int:
        return sum(self._study_minutes_provider()[-7:])

    def study_trend_values(self, days: int = 14) -> list[int]:
        values = self._study_minutes_provider()[-days:]
        return [0] * (days - len(values)) + values
