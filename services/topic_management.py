from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import DifficultyLevel, Subject, Topic
from services.scheduler import SchedulerService


@dataclass(frozen=True)
class TopicTreeNode:
    topic_id: int
    name: str
    subject_id: int
    children: tuple["TopicTreeNode", ...] = field(default_factory=tuple)


class SubjectService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_subject(
        self,
        *,
        name: str,
        color_tag: str = "#7F77DD",
        exam_date: date | None = None,
        description: str | None = None,
    ) -> Subject:
        subject = Subject(
            name=name,
            color=color_tag,
            icon=None,
            exam_date=exam_date,
        )
        self.session.add(subject)
        self.session.flush()
        return subject

    def get_subject(self, subject_id: int | str) -> Subject | None:
        return self.session.get(Subject, int(subject_id))

    def list_subjects(self) -> list[Subject]:
        stmt = select(Subject).order_by(Subject.name)
        return list(self.session.scalars(stmt))

    def update_subject(
        self,
        subject_id: int | str,
        *,
        name: str | None = None,
        color_tag: str | None = None,
        exam_date: date | None = None,
        description: str | None = None,
        is_archived: bool | None = None,
    ) -> Subject:
        subject = self._require_subject(subject_id)
        if name is not None:
            subject.name = name
        if color_tag is not None:
            subject.color = color_tag
        if exam_date is not None:
            subject.exam_date = exam_date
        if is_archived is not None:
            subject.archived = 1 if is_archived else 0
        self.session.flush()
        return subject

    def delete_subject(self, subject_id: int | str) -> None:
        subject = self._require_subject(subject_id)
        self.session.delete(subject)
        self.session.flush()

    def _require_subject(self, subject_id: int | str) -> Subject:
        subject = self.session.get(Subject, int(subject_id))
        if subject is None:
            raise ValueError(f"Subject {subject_id} does not exist")
        return subject


class TopicService:
    def __init__(self, session: Session, scheduler: SchedulerService | None = None) -> None:
        self.session = session
        self.scheduler = scheduler or SchedulerService(session)

    def create_topic(
        self,
        *,
        subject_id: int | str,
        name: str,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        parent_topic_id: int | str | None = None,
        exam_date: date | None = None,
        completion_date: date | None = None,
        notes: str | None = None,
        difficulty_score: float | None = None,
        auto_schedule: bool = True,
    ) -> Topic:
        subject = self._require_subject(subject_id)
        topic = Topic(
            subject_id=subject.id,
            name=name,
            description=notes,
            difficulty=self._difficulty_value(difficulty),
            status="completed" if completion_date else "active",
            target_date=completion_date,
            exam_date_override=exam_date or subject.exam_date,
            estimated_minutes=self._default_estimated_minutes(difficulty),
            mastery_score=self._mastery_from_difficulty(difficulty, difficulty_score),
            review_count=0,
        )
        self.session.add(topic)
        self.session.flush()

        if auto_schedule and topic.status != "completed":
            first_revision = self.scheduler.schedule_new_topic(topic.id)
            self._adjust_initial_schedule_for_exam(topic, first_revision)
            self.session.flush()

        return topic

    def get_topic(self, topic_id: int | str) -> Topic | None:
        return self.session.get(Topic, int(topic_id))

    def list_topics_for_subject(self, subject_id: int | str) -> list[Topic]:
        stmt = select(Topic).where(Topic.subject_id == int(subject_id)).order_by(Topic.name)
        return list(self.session.scalars(stmt))

    def update_topic(
        self,
        topic_id: int | str,
        *,
        name: str | None = None,
        difficulty: DifficultyLevel | None = None,
        progress: int | None = None,
        parent_topic_id: int | str | None = None,
        exam_date: date | None = None,
        completion_date: date | None = None,
        notes: str | None = None,
        is_completed: bool | None = None,
        is_archived: bool | None = None,
    ) -> Topic:
        topic = self._require_topic(topic_id)
        if name is not None:
            topic.name = name
        if difficulty is not None:
            topic.difficulty = self._difficulty_value(difficulty)
            if topic.estimated_minutes is None:
                topic.estimated_minutes = self._default_estimated_minutes(difficulty)
        if progress is not None:
            topic.mastery_score = round(max(0, min(int(progress), 100)), 1)
        if exam_date is not None:
            topic.exam_date_override = exam_date
        if completion_date is not None:
            topic.target_date = completion_date
        if notes is not None:
            topic.description = notes
        if is_completed is not None:
            topic.status = "completed" if is_completed else "active"
        if is_archived is not None:
            topic.status = "archived" if is_archived else "active"
        self.session.flush()
        return topic

    def delete_topic(self, topic_id: int | str) -> None:
        topic = self._require_topic(topic_id)
        self.session.delete(topic)
        self.session.flush()

    def get_topic_tree(self, subject_id: int | str) -> tuple[TopicTreeNode, ...]:
        topics = self.list_topics_for_subject(subject_id)
        return tuple(
            TopicTreeNode(topic_id=topic.id, name=topic.name, subject_id=topic.subject_id)
            for topic in topics
        )

    def get_leaf_topics(self, subject_id: int | str) -> list[Topic]:
        return self.list_topics_for_subject(subject_id)

    def _adjust_initial_schedule_for_exam(self, topic: Topic, revision) -> None:
        exam_date = topic.exam_date_override or topic.subject.exam_date
        if exam_date is None:
            return

        today = self.scheduler._today()
        days_until_exam = (exam_date - today).days
        if days_until_exam <= 0:
            revision.due_at = revision.due_at.replace(year=today.year, month=today.month, day=today.day)
            revision.interval_days = 0.0
            return

    def _require_subject(self, subject_id: int | str) -> Subject:
        subject = self.session.get(Subject, int(subject_id))
        if subject is None:
            raise ValueError(f"Subject {subject_id} does not exist")
        return subject

    def _require_topic(self, topic_id: int | str) -> Topic:
        topic = self.session.get(Topic, int(topic_id))
        if topic is None:
            raise ValueError(f"Topic {topic_id} does not exist")
        return topic

    def _difficulty_value(self, difficulty: DifficultyLevel | str) -> str:
        return difficulty.value if hasattr(difficulty, "value") else str(difficulty).lower()

    def _default_estimated_minutes(self, difficulty: DifficultyLevel | str) -> int:
        key = self._difficulty_value(difficulty)
        return {"easy": 15, "medium": 25, "hard": 35}.get(key, 25)

    def _mastery_from_difficulty(self, difficulty: DifficultyLevel | str, supplied: float | None) -> float:
        if supplied is not None:
            return round(max(0.0, min(float(supplied) * 100 if supplied <= 1 else float(supplied), 100.0)), 1)
        key = self._difficulty_value(difficulty)
        return {"easy": 25.0, "medium": 15.0, "hard": 5.0}.get(key, 15.0)
