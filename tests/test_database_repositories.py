from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from db.repositories import RevisionRepository, SessionRepository, TopicRepository
from models import ConfidenceRating, Revision, Topic


def test_topic_and_revision_crud_flow(session) -> None:
    topic_repo = TopicRepository(session)
    revision_repo = RevisionRepository(session)

    subject = topic_repo.create_subject("Mathematics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Calculus Limits", difficulty="hard")
    revision = revision_repo.create_revision(topic_id=topic.id, scheduled_date=date(2026, 4, 10))
    session.commit()

    stored_topic = topic_repo.get_topic(topic.id)
    due_revisions = revision_repo.list_due_revisions(date(2026, 4, 10))

    assert stored_topic is not None
    assert stored_topic.name == "Calculus Limits"
    assert stored_topic.difficulty == "hard"
    assert [item.id for item in due_revisions] == [revision.id]


def test_foreign_key_constraint_prevents_orphan_topic(session) -> None:
    with pytest.raises(IntegrityError):
        TopicRepository(session).create_topic(subject_id="99999", name="Impossible Topic")


def test_cascade_delete_removes_revisions(session) -> None:
    topic_repo = TopicRepository(session)
    revision_repo = RevisionRepository(session)

    subject = topic_repo.create_subject("Physics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Newtonian Mechanics")
    revision_repo.create_revision(topic_id=topic.id, scheduled_date=date(2026, 4, 12))
    session.commit()

    topic_repo.delete_topic(topic.id)
    session.commit()

    assert session.query(Topic).count() == 0
    assert session.query(Revision).count() == 0


def test_session_repository_tracks_local_study_sessions(session) -> None:
    session_repo = SessionRepository(session)

    study_session = session_repo.create_session(
        started_at=datetime(2026, 4, 8, 9, 0, 0),
        ended_at=datetime(2026, 4, 8, 9, 30, 0),
    )
    session.commit()

    stored_session = session_repo.get_session(study_session.id)
    listed_sessions = session_repo.list_sessions()

    assert stored_session is not None
    assert stored_session.duration_minutes == 30
    assert [item.id for item in listed_sessions] == [study_session.id]


def test_revision_completion_updates_rating(session) -> None:
    topic_repo = TopicRepository(session)
    revision_repo = RevisionRepository(session)

    subject = topic_repo.create_subject("Chemistry")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Stoichiometry")
    revision = revision_repo.create_revision(topic_id=topic.id, scheduled_date=date(2026, 4, 11))

    revision_repo.mark_completed(revision.id, confidence_rating=ConfidenceRating.GOOD)
    session.commit()

    stored_revision = revision_repo.get_revision(revision.id)
    assert stored_revision is not None
    assert stored_revision.status == "completed"
    assert stored_revision.rating == ConfidenceRating.GOOD.value
