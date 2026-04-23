from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import ConfidenceRating, DifficultyLevel, Revision, StudySession, Subject, Topic


class TopicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_subject(
        self,
        name: str,
        color_tag: str = "#7F77DD",
        *,
        exam_date: date | None = None,
        description: str | None = None,
    ) -> Subject:
        subject = Subject(
            name=name,
            color_tag=color_tag,
            exam_date=exam_date,
            description=description,
        )
        self.session.add(subject)
        self.session.flush()
        return subject

    def create_topic(
        self,
        *,
        subject_id: str,
        name: str,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        parent_topic_id: str | None = None,
        notes: str | None = None,
    ) -> Topic:
        topic = Topic(
            subject_id=subject_id,
            parent_topic_id=parent_topic_id,
            name=name,
            difficulty=difficulty,
            notes=notes,
        )
        self.session.add(topic)
        self.session.flush()
        return topic

    def get_topic(self, topic_id: str) -> Topic | None:
        return self.session.get(Topic, topic_id)

    def list_topics_by_subject(self, subject_id: str) -> list[Topic]:
        stmt = select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.sort_order, Topic.name)
        return list(self.session.scalars(stmt))

    def list_subjects(self) -> list[Subject]:
        stmt = select(Subject).order_by(Subject.name)
        return list(self.session.scalars(stmt))

    def delete_topic(self, topic_id: str) -> None:
        topic = self.session.get(Topic, topic_id)
        if topic is not None:
            self.session.delete(topic)
            self.session.flush()


class RevisionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_revision(
        self,
        *,
        topic_id: str,
        scheduled_date: date,
        confidence_rating: ConfidenceRating | None = None,
        study_session_id: str | None = None,
    ) -> Revision:
        revision = Revision(
            topic_id=topic_id,
            scheduled_date=scheduled_date,
            confidence_rating=confidence_rating,
            study_session_id=study_session_id,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def get_revision(self, revision_id: str) -> Revision | None:
        return self.session.get(Revision, revision_id)

    def list_due_revisions(self, due_on_or_before: date) -> list[Revision]:
        stmt = (
            select(Revision)
            .where(Revision.is_completed.is_(False), Revision.scheduled_date <= due_on_or_before)
            .order_by(Revision.scheduled_date)
        )
        return list(self.session.scalars(stmt))

    def mark_completed(
        self,
        revision_id: str,
        *,
        confidence_rating: ConfidenceRating,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self.session.get(Revision, revision_id)
        if revision is None:
            raise ValueError(f"Revision {revision_id} does not exist")

        revision.is_completed = True
        revision.completed_at = completed_at or datetime.now(UTC).replace(tzinfo=None)
        revision.confidence_rating = confidence_rating
        self.session.flush()
        return revision


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(
        self,
        *,
        started_at: datetime,
        ended_at: datetime | None = None,
        topic_id: str | None = None,
        topics_attempted: int = 0,
        topics_completed: int = 0,
    ) -> StudySession:
        study_session = StudySession(
            topic_id=topic_id,
            started_at=started_at,
            ended_at=ended_at,
            topics_attempted=topics_attempted,
            topics_completed=topics_completed,
        )
        self.session.add(study_session)
        self.session.flush()
        return study_session

    def get_session(self, session_id: str) -> StudySession | None:
        return self.session.get(StudySession, session_id)

    def list_sessions(self) -> list[StudySession]:
        stmt = select(StudySession).order_by(StudySession.started_at)
        return list(self.session.scalars(stmt))
