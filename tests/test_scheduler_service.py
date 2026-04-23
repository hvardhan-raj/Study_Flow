from __future__ import annotations

from datetime import date, datetime

from db.repositories import TopicRepository, create_user
from models import ConfidenceRating, DifficultyLevel, PerformanceLog, Revision
from services.scheduler import SchedulerService


def _build_scheduler(session, today_value: date) -> SchedulerService:
    return SchedulerService(session, today_provider=lambda: today_value)


def test_schedule_new_topic_creates_first_revision(session) -> None:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "Mathematics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Derivatives")

    scheduler = _build_scheduler(session, date(2026, 4, 9))
    revision = scheduler.schedule_new_topic(topic.id)
    session.commit()

    refreshed_topic = topic_repo.get_topic(topic.id)
    assert revision.scheduled_date == date(2026, 4, 9)
    assert refreshed_topic is not None
    assert refreshed_topic.fsrs_due_date == date(2026, 4, 9)
    assert refreshed_topic.fsrs_review_count == 0


def test_record_revision_advances_interval_and_creates_follow_up(session) -> None:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "Physics")
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
    assert refreshed_topic is not None
    assert refreshed_topic.fsrs_review_count == 1
    assert refreshed_topic.fsrs_due_date == next_revision.scheduled_date
    assert next_revision.scheduled_date > date(2026, 4, 9)
    assert next_revision.interval_days_after >= 1


def test_get_due_today_and_overdue_split_open_revisions(session) -> None:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "Chemistry")
    due_topic = topic_repo.create_topic(subject_id=subject.id, name="Moles")
    overdue_topic = topic_repo.create_topic(subject_id=subject.id, name="Atomic Structure")

    scheduler = _build_scheduler(session, date(2026, 4, 12))
    due_revision = scheduler.schedule_new_topic(due_topic.id, scheduled_for=date(2026, 4, 12))
    overdue_revision = scheduler.schedule_new_topic(overdue_topic.id, scheduled_for=date(2026, 4, 10))
    session.commit()

    due_items = scheduler.get_due_today()
    overdue_items = scheduler.get_overdue()

    assert [item.id for item in due_items] == [due_revision.id]
    assert [item.id for item in overdue_items] == [overdue_revision.id]


def test_reschedule_after_miss_marks_revision_and_logs_penalty(session) -> None:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "Biology")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Photosynthesis")

    scheduler = _build_scheduler(session, date(2026, 4, 15))
    revision = scheduler.schedule_new_topic(topic.id, scheduled_for=date(2026, 4, 10))
    session.commit()

    missed = scheduler.reschedule_after_miss(revision.id)
    session.commit()

    refreshed_topic = topic_repo.get_topic(topic.id)
    logs = session.query(PerformanceLog).filter(PerformanceLog.revision_id == revision.id).all()
    assert missed.is_missed is True
    assert missed.scheduled_days_overdue == 5
    assert refreshed_topic is not None
    assert refreshed_topic.fsrs_due_date == date(2026, 4, 15)
    assert len(logs) == 1
    assert logs[0].scheduler_source == "missed_review"


def test_confidence_feedback_changes_future_interval(session) -> None:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "History")
    hard_topic = topic_repo.create_topic(
        subject_id=subject.id,
        name="Roman Empire",
        difficulty=DifficultyLevel.HARD,
    )
    easy_topic = topic_repo.create_topic(
        subject_id=subject.id,
        name="Renaissance",
        difficulty=DifficultyLevel.EASY,
    )

    scheduler = _build_scheduler(session, date(2026, 4, 20))
    hard_revision = scheduler.schedule_new_topic(hard_topic.id)
    easy_revision = scheduler.schedule_new_topic(easy_topic.id, scheduled_for=date(2026, 4, 20))

    hard_follow_up = scheduler.record_revision(
        hard_revision.id,
        rating=ConfidenceRating.HARD,
        completed_at=datetime(2026, 4, 20, 9, 0, 0),
    )
    easy_follow_up = scheduler.record_revision(
        easy_revision.id,
        rating=ConfidenceRating.EASY,
        completed_at=datetime(2026, 4, 20, 9, 5, 0),
    )
    session.commit()

    assert easy_follow_up.scheduled_date > hard_follow_up.scheduled_date
    assert easy_follow_up.interval_days_after > hard_follow_up.interval_days_after
    assert session.query(Revision).count() == 4
