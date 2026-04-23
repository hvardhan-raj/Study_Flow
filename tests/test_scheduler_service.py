from __future__ import annotations

from datetime import date, datetime

from db.repositories import TopicRepository
from models import ConfidenceRating, DifficultyLevel, PerformanceLog, Revision
from services.scheduler import SchedulerService


def _build_scheduler(session, today_value: date) -> SchedulerService:
    return SchedulerService(session, today_provider=lambda: today_value)


def test_schedule_new_topic_creates_first_revision(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Mathematics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Derivatives")

    revision = _build_scheduler(session, date(2026, 4, 9)).schedule_new_topic(topic.id)
    session.commit()

    refreshed_topic = topic_repo.get_topic(topic.id)
    assert revision.scheduled_date == date(2026, 4, 9)
    assert refreshed_topic is not None
    assert refreshed_topic.fsrs_due_date == date(2026, 4, 9)
    assert refreshed_topic.fsrs_review_count == 0


def test_record_revision_advances_interval_and_creates_single_follow_up(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Physics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Kinematics")
    scheduler = _build_scheduler(session, date(2026, 4, 9))

    first_revision = scheduler.schedule_new_topic(topic.id)
    next_revision = scheduler.record_revision(
        first_revision.id,
        rating=ConfidenceRating.GOOD,
        completed_at=datetime(2026, 4, 9, 10, 0, 0),
    )
    session.commit()

    refreshed_topic = topic_repo.get_topic(topic.id)
    open_revisions = session.query(Revision).filter(Revision.topic_id == topic.id, Revision.is_completed.is_(False)).all()
    assert refreshed_topic is not None
    assert refreshed_topic.fsrs_review_count == 1
    assert next_revision.scheduled_date > date(2026, 4, 9)
    assert len(open_revisions) == 1
    assert open_revisions[0].id == next_revision.id


def test_get_due_today_and_overdue_only_return_open_revisions(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Chemistry")
    due_topic = topic_repo.create_topic(subject_id=subject.id, name="Moles")
    overdue_topic = topic_repo.create_topic(subject_id=subject.id, name="Atomic Structure")

    scheduler = _build_scheduler(session, date(2026, 4, 12))
    due_revision = scheduler.schedule_new_topic(due_topic.id, scheduled_for=date(2026, 4, 12))
    overdue_revision = scheduler.schedule_new_topic(overdue_topic.id, scheduled_for=date(2026, 4, 10))
    scheduler.record_revision(due_revision.id, rating=ConfidenceRating.GOOD, completed_at=datetime(2026, 4, 12, 9, 0, 0))
    session.commit()

    due_items = scheduler.get_due_today()
    overdue_items = scheduler.get_overdue()

    assert not due_items
    assert [item.id for item in overdue_items] == [overdue_revision.id]


def test_reschedule_after_miss_penalizes_revision_without_duplicates(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Biology")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Photosynthesis")

    scheduler = _build_scheduler(session, date(2026, 4, 15))
    revision = scheduler.schedule_new_topic(topic.id, scheduled_for=date(2026, 4, 10))
    missed = scheduler.reschedule_after_miss(revision.id)
    session.commit()

    refreshed_topic = topic_repo.get_topic(topic.id)
    logs = session.query(PerformanceLog).filter(PerformanceLog.revision_id == revision.id).all()
    open_revisions = session.query(Revision).filter(Revision.topic_id == topic.id, Revision.is_completed.is_(False)).all()
    assert missed.is_missed is True
    assert missed.scheduled_days_overdue == 5
    assert refreshed_topic is not None
    assert refreshed_topic.fsrs_due_date == date(2026, 4, 16)
    assert len(logs) == 1
    assert logs[0].scheduler_source == "missed_review"
    assert len(open_revisions) == 1


def test_confidence_and_difficulty_change_future_interval(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("History")
    hard_topic = topic_repo.create_topic(subject_id=subject.id, name="Roman Empire", difficulty=DifficultyLevel.HARD)
    easy_topic = topic_repo.create_topic(subject_id=subject.id, name="Renaissance", difficulty=DifficultyLevel.EASY)

    scheduler = _build_scheduler(session, date(2026, 4, 20))
    hard_follow_up = scheduler.record_revision(
        scheduler.schedule_new_topic(hard_topic.id).id,
        rating=ConfidenceRating.HARD,
        completed_at=datetime(2026, 4, 20, 9, 0, 0),
    )
    easy_follow_up = scheduler.record_revision(
        scheduler.schedule_new_topic(easy_topic.id).id,
        rating=ConfidenceRating.EASY,
        completed_at=datetime(2026, 4, 20, 9, 5, 0),
    )
    session.commit()

    assert easy_follow_up.scheduled_date > hard_follow_up.scheduled_date
    assert easy_follow_up.interval_days_after > hard_follow_up.interval_days_after


def test_overdue_completion_penalizes_next_interval(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Geography")
    on_time_topic = topic_repo.create_topic(subject_id=subject.id, name="Rivers")
    overdue_topic = topic_repo.create_topic(subject_id=subject.id, name="Mountains")

    scheduler = _build_scheduler(session, date(2026, 4, 10))
    on_time_revision = scheduler.schedule_new_topic(on_time_topic.id, scheduled_for=date(2026, 4, 10))
    overdue_revision = scheduler.schedule_new_topic(overdue_topic.id, scheduled_for=date(2026, 4, 7))

    on_time_follow_up = scheduler.record_revision(on_time_revision.id, rating=ConfidenceRating.GOOD, completed_at=datetime(2026, 4, 10, 9, 0, 0))
    overdue_follow_up = scheduler.record_revision(overdue_revision.id, rating=ConfidenceRating.GOOD, completed_at=datetime(2026, 4, 10, 9, 0, 0))
    session.commit()

    assert overdue_follow_up.interval_days_after < on_time_follow_up.interval_days_after
