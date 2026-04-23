from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import DifficultyLevel, Subject, Topic
from services.scheduler import SchedulerService


@dataclass(frozen=True)
class TopicTreeNode:
    topic_id: str
    name: str
    subject_id: str
    children: tuple["TopicTreeNode", ...] = field(default_factory=tuple)


class SubjectService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_subject(
        self,
        *,
        user_id: str,
        name: str,
        color_tag: str = "#7F77DD",
        exam_date: date | None = None,
        description: str | None = None,
    ) -> Subject:
        subject = Subject(
            user_id=user_id,
            name=name,
            color_tag=color_tag,
            exam_date=exam_date,
            description=description,
        )
        self.session.add(subject)
        self.session.flush()
        return subject

    def get_subject(self, subject_id: str) -> Subject | None:
        return self.session.get(Subject, subject_id)

    def list_subjects_for_user(self, user_id: str) -> list[Subject]:
        stmt = select(Subject).where(Subject.user_id == user_id).order_by(Subject.name)
        return list(self.session.scalars(stmt))

    def update_subject(
        self,
        subject_id: str,
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
            subject.color_tag = color_tag
        if exam_date is not None:
            subject.exam_date = exam_date
        if description is not None:
            subject.description = description
        if is_archived is not None:
            subject.is_archived = is_archived
        self.session.flush()
        return subject

    def delete_subject(self, subject_id: str) -> None:
        subject = self._require_subject(subject_id)
        self.session.delete(subject)
        self.session.flush()

    def _require_subject(self, subject_id: str) -> Subject:
        subject = self.session.get(Subject, subject_id)
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
        subject_id: str,
        name: str,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        parent_topic_id: str | None = None,
        exam_date: date | None = None,
        completion_date: date | None = None,
        notes: str | None = None,
        difficulty_score: float | None = None,
        auto_schedule: bool = True,
    ) -> Topic:
        subject = self._require_subject(subject_id)
        if parent_topic_id is not None:
            self._require_topic(parent_topic_id)

        topic = Topic(
            subject_id=subject_id,
            parent_topic_id=parent_topic_id,
            name=name,
            difficulty=difficulty,
            difficulty_score=difficulty_score if difficulty_score is not None else self._default_difficulty_score(difficulty),
            exam_date=exam_date or subject.exam_date,
            completion_date=completion_date,
            notes=notes,
        )
        self.session.add(topic)
        self.session.flush()

        if auto_schedule and not topic.is_completed:
            first_revision = self.scheduler.schedule_new_topic(topic.id)
            self._adjust_initial_schedule_for_exam(topic, first_revision)
            self.session.flush()

        return topic

    def get_topic(self, topic_id: str) -> Topic | None:
        return self.session.get(Topic, topic_id)

    def list_topics_for_subject(self, subject_id: str) -> list[Topic]:
        stmt = select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.sort_order, Topic.name)
        return list(self.session.scalars(stmt))

    def update_topic(
        self,
        topic_id: str,
        *,
        name: str | None = None,
        difficulty: DifficultyLevel | None = None,
        progress: int | None = None,
        parent_topic_id: str | None = None,
        exam_date: date | None = None,
        completion_date: date | None = None,
        notes: str | None = None,
        is_completed: bool | None = None,
        is_archived: bool | None = None,
    ) -> Topic:
        topic = self._require_topic(topic_id)
        if parent_topic_id == topic_id:
            raise ValueError("A topic cannot be its own parent")
        if parent_topic_id is not None:
            self._require_topic(parent_topic_id)

        if name is not None:
            topic.name = name
        if difficulty is not None:
            topic.difficulty = difficulty
            topic.difficulty_score = self._default_difficulty_score(difficulty)
        if progress is not None:
            topic.progress = max(0, min(int(progress), 100))
        if parent_topic_id is not None:
            topic.parent_topic_id = parent_topic_id
        if exam_date is not None:
            topic.exam_date = exam_date
        if completion_date is not None:
            topic.completion_date = completion_date
        if notes is not None:
            topic.notes = notes
        if is_completed is not None:
            topic.is_completed = is_completed
        if is_archived is not None:
            topic.is_archived = is_archived

        self.session.flush()
        return topic

    def delete_topic(self, topic_id: str) -> None:
        topic = self._require_topic(topic_id)
        self.session.delete(topic)
        self.session.flush()

    def get_topic_tree(self, subject_id: str) -> tuple[TopicTreeNode, ...]:
        stmt = (
            select(Topic)
            .where(Topic.subject_id == subject_id)
            .options(selectinload(Topic.child_topics))
            .order_by(Topic.sort_order, Topic.name)
        )
        topics = list(self.session.scalars(stmt))
        by_parent: dict[str | None, list[Topic]] = {}
        for topic in topics:
            by_parent.setdefault(topic.parent_topic_id, []).append(topic)

        def build(parent_id: str | None) -> tuple[TopicTreeNode, ...]:
            nodes = []
            for topic in by_parent.get(parent_id, []):
                nodes.append(
                    TopicTreeNode(
                        topic_id=topic.id,
                        name=topic.name,
                        subject_id=topic.subject_id,
                        children=build(topic.id),
                    )
                )
            return tuple(nodes)

        return build(None)

    def get_leaf_topics(self, subject_id: str) -> list[Topic]:
        topics = self.list_topics_for_subject(subject_id)
        child_parent_ids = {topic.parent_topic_id for topic in topics if topic.parent_topic_id is not None}
        return [topic for topic in topics if topic.id not in child_parent_ids]

    def _adjust_initial_schedule_for_exam(self, topic: Topic, revision) -> None:
        if topic.exam_date is None:
            return

        today = self.scheduler._today()
        days_until_exam = (topic.exam_date - today).days
        if days_until_exam <= 0:
            topic.fsrs_due_date = today
            revision.scheduled_date = today
            revision.interval_days_after = 1
            return

        desired_interval = max(1, min(revision.interval_days_after or 1, days_until_exam))
        topic.fsrs_due_date = today + timedelta(days=desired_interval)
        revision.interval_days_after = desired_interval

    def _require_subject(self, subject_id: str) -> Subject:
        subject = self.session.get(Subject, subject_id)
        if subject is None:
            raise ValueError(f"Subject {subject_id} does not exist")
        return subject

    def _require_topic(self, topic_id: str) -> Topic:
        topic = self.session.get(Topic, topic_id)
        if topic is None:
            raise ValueError(f"Topic {topic_id} does not exist")
        return topic

    def _default_difficulty_score(self, difficulty: DifficultyLevel) -> float:
        return {
            DifficultyLevel.EASY: 0.3,
            DifficultyLevel.MEDIUM: 0.5,
            DifficultyLevel.HARD: 0.75,
        }[difficulty]
