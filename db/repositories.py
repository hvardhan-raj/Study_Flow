from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import ConfidenceRating, Revision, StudySession, Subject, Topic


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
        subject = Subject(name=name, color=color_tag, exam_date=exam_date)
        self.session.add(subject)
        self.session.flush()
        return subject

    def create_topic(
        self,
        *,
        subject_id: int | str,
        name: str,
        difficulty: str = "medium",
        parent_topic_id: int | str | None = None,
        notes: str | None = None,
    ) -> Topic:
        level = difficulty.value if hasattr(difficulty, "value") else str(difficulty).lower()
        topic = Topic(
            subject_id=int(subject_id),
            name=name,
            description=notes,
            difficulty=level,
            estimated_minutes={"easy": 15, "medium": 30, "hard": 45}.get(level, 30),
        )
        self.session.add(topic)
        self.session.flush()
        return topic

    def get_topic(self, topic_id: int | str) -> Topic | None:
        return self.session.get(Topic, int(topic_id))

    def list_topics_by_subject(self, subject_id: int | str) -> list[Topic]:
        stmt = select(Topic).where(Topic.subject_id == int(subject_id)).order_by(Topic.name)
        return list(self.session.scalars(stmt))

    def list_subjects(self) -> list[Subject]:
        stmt = select(Subject).order_by(Subject.name)
        return list(self.session.scalars(stmt))

    def delete_topic(self, topic_id: int | str) -> None:
        topic = self.session.get(Topic, int(topic_id))
        if topic is not None:
            self.session.delete(topic)
            self.session.flush()


class RevisionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_revision(
        self,
        *,
        topic_id: int | str,
        scheduled_date: date,
        confidence_rating: ConfidenceRating | None = None,
        study_session_id: int | str | None = None,
    ) -> Revision:
        revision = Revision(
            topic_id=int(topic_id),
            due_at=datetime.combine(scheduled_date, time(11, 0)),
            status="open",
            rating=confidence_rating.value if confidence_rating else None,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def get_revision(self, revision_id: int | str) -> Revision | None:
        return self.session.get(Revision, int(revision_id))

    def list_due_revisions(self, due_on_or_before: date) -> list[Revision]:
        stmt = (
            select(Revision)
            .where(Revision.status == "open", func.date(Revision.due_at) <= due_on_or_before.isoformat())
            .order_by(Revision.due_at)
        )
        return list(self.session.scalars(stmt))

    def mark_completed(
        self,
        revision_id: int | str,
        *,
        confidence_rating: ConfidenceRating,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self.session.get(Revision, int(revision_id))
        if revision is None:
            raise ValueError(f"Revision {revision_id} does not exist")

        revision.status = "completed"
        revision.completed_at = completed_at or datetime.now()
        revision.rating = confidence_rating.value
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
        topic_id: int | str | None = None,
        topics_attempted: int = 0,
        topics_completed: int = 0,
    ) -> StudySession:
        duration_minutes = None
        if ended_at is not None:
            duration_minutes = max(0, round((ended_at - started_at).total_seconds() / 60))
        study_session = StudySession(
            topic_id=int(topic_id) if topic_id is not None else None,
            started_at=started_at,
            ended_at=ended_at,
            duration_minutes=duration_minutes,
            session_type="study",
        )
        self.session.add(study_session)
        self.session.flush()
        return study_session

    def get_session(self, session_id: int | str) -> StudySession | None:
        return self.session.get(StudySession, int(session_id))

    def list_sessions(self) -> list[StudySession]:
        stmt = select(StudySession).order_by(StudySession.started_at)
        return list(self.session.scalars(stmt))
