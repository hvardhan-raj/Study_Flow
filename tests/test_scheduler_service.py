from __future__ import annotations

from datetime import date, datetime

from db.repositories import TopicRepository
from models import AppSetting, ConfidenceRating, Revision
from services.scheduler import SchedulerService


def _build_scheduler(session, today_value: date) -> SchedulerService:
    return SchedulerService(session, today_provider=lambda: today_value)


def test_create_first_revision_uses_preferred_time(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Mathematics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Derivatives")

    session.merge(AppSetting(key="preferred_time", value="18:00"))
    revision = _build_scheduler(session, date(2026, 4, 9)).create_first_revision(topic.id)
    session.commit()

    assert revision.status == "open"
    assert revision.due_at == datetime(2026, 4, 9, 18, 0, 0)
    assert revision.difficulty_adjustment == 2.5


def test_process_review_applies_sm2_intervals(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Physics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Kinematics")
    scheduler = _build_scheduler(session, date(2026, 4, 9))

    first = scheduler.create_first_revision(topic.id)
    second = scheduler.process_review(first.id, ConfidenceRating.GOOD, completed_at=datetime(2026, 4, 9, 18, 0, 0))
    third = scheduler.process_review(second.id, ConfidenceRating.GOOD, completed_at=datetime(2026, 4, 10, 18, 0, 0))
    fourth = scheduler.process_review(third.id, ConfidenceRating.GOOD, completed_at=datetime(2026, 4, 13, 18, 0, 0))
    session.commit()

    refreshed_topic = topic_repo.get_topic(topic.id)
    completed_rows = (
        session.query(Revision)
        .filter(Revision.topic_id == topic.id, Revision.status == "completed")
        .order_by(Revision.id)
        .all()
    )
    next_open = session.query(Revision).filter(Revision.topic_id == topic.id, Revision.status == "open").one()

    assert refreshed_topic is not None
    assert refreshed_topic.review_count == 3
    assert [row.interval_days for row in completed_rows] == [1.0, 3.0, 8.0]
    assert next_open.id == fourth.id
    assert next_open.due_at.date() == date(2026, 4, 21)


def test_low_quality_review_resets_repetition(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Chemistry")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Moles")
    scheduler = _build_scheduler(session, date(2026, 4, 9))

    revision = scheduler.create_first_revision(topic.id)
    follow_up = scheduler.process_review(revision.id, ConfidenceRating.AGAIN, completed_at=datetime(2026, 4, 9, 18, 0, 0))
    session.commit()

    stored_topic = topic_repo.get_topic(topic.id)
    assert stored_topic is not None
    assert stored_topic.review_count == 0
    assert follow_up.interval_days == 1


def test_get_tasks_for_date_allocates_non_overlapping_time_slots(session) -> None:
    session.merge(AppSetting(key="preferred_time", value="18:00"))
    session.merge(AppSetting(key="daily_time_minutes", value="120"))

    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("History")
    topic_a = topic_repo.create_topic(subject_id=subject.id, name="Ancient Rome", difficulty="easy")
    topic_b = topic_repo.create_topic(subject_id=subject.id, name="World War I", difficulty="medium")
    scheduler = _build_scheduler(session, date(2026, 4, 21))

    scheduler.create_first_revision(topic_a.id, scheduled_for=date(2026, 4, 21))
    scheduler.create_first_revision(topic_b.id, scheduled_for=date(2026, 4, 21))
    tasks = scheduler.get_tasks_for_date(date(2026, 4, 21))
    session.commit()

    assert [task.due_at for task in tasks] == [
        datetime(2026, 4, 21, 18, 0, 0),
        datetime(2026, 4, 21, 18, 20, 0),
    ]


def test_overflow_moves_remaining_tasks_to_next_day(session) -> None:
    session.merge(AppSetting(key="preferred_time", value="18:00"))
    session.merge(AppSetting(key="daily_time_minutes", value="60"))

    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Biology")
    topic_a = topic_repo.create_topic(subject_id=subject.id, name="Photosynthesis", difficulty="hard")
    topic_b = topic_repo.create_topic(subject_id=subject.id, name="Respiration", difficulty="hard")
    scheduler = _build_scheduler(session, date(2026, 4, 15))

    scheduler.create_first_revision(topic_a.id, scheduled_for=date(2026, 4, 15))
    scheduler.create_first_revision(topic_b.id, scheduled_for=date(2026, 4, 15))
    day_one = scheduler.get_tasks_for_date(date(2026, 4, 15))
    day_two = scheduler.get_tasks_for_date(date(2026, 4, 16))
    session.commit()

    assert [task.topic.name for task in day_one] == ["Photosynthesis"]
    assert [task.topic.name for task in day_two] == ["Respiration"]
    assert day_two[0].due_at == datetime(2026, 4, 16, 18, 0, 0)


def test_reschedule_after_miss_keeps_single_open_revision(session) -> None:
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject("Geography")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Rivers")
    scheduler = _build_scheduler(session, date(2026, 4, 10))

    revision = scheduler.create_first_revision(topic.id, scheduled_for=date(2026, 4, 9))
    rescheduled = scheduler.reschedule_after_miss(revision.id, reschedule_from=date(2026, 4, 11))
    session.commit()

    open_revisions = session.query(Revision).filter(Revision.topic_id == topic.id, Revision.status == "open").all()

    assert len(open_revisions) == 1
    assert open_revisions[0].id == rescheduled.id
    assert rescheduled.due_at == datetime(2026, 4, 11, 18, 0, 0)
