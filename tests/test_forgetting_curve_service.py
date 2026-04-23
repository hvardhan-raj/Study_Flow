from __future__ import annotations

from datetime import date, datetime, timedelta

from db.repositories import TopicRepository, create_user
from models import ConfidenceRating, Revision
from services import ForgettingCurveModel, SchedulerService


def _build_scheduler(session, today_value: date, model_dir) -> SchedulerService:
    forgetting_curve_model = ForgettingCurveModel(session, model_dir=model_dir)
    return SchedulerService(
        session,
        today_provider=lambda: today_value,
        forgetting_curve_model=forgetting_curve_model,
    )


def _seed_personal_history(session, tmp_path, record_count: int = 20) -> tuple[SchedulerService, str]:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "Mathematics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Series and Sequences")

    scheduler = _build_scheduler(session, date(2026, 4, 1), tmp_path)
    current_day = date(2026, 4, 1)
    revision = scheduler.schedule_new_topic(topic.id, scheduled_for=current_day)
    for index in range(record_count):
        completed_at = datetime.combine(current_day, datetime.min.time()).replace(hour=9)
        revision = scheduler.record_revision(
            revision.id,
            rating=ConfidenceRating.GOOD if index % 3 else ConfidenceRating.EASY,
            completed_at=completed_at,
        )
        current_day = revision.scheduled_date
    session.commit()
    return scheduler, user.id


def test_forgetting_curve_trains_after_minimum_history(session, tmp_path) -> None:
    scheduler, user_id = _seed_personal_history(session, tmp_path, record_count=20)

    artifact = scheduler.forgetting_curve_model.load(user_id)

    assert artifact is not None
    assert artifact.trained_on_records >= 20
    assert len(artifact.examples) >= 20


def test_scheduler_falls_back_to_fsrs_without_enough_history(session, tmp_path) -> None:
    user = create_user(session)
    topic_repo = TopicRepository(session)
    subject = topic_repo.create_subject(user.id, "Physics")
    topic = topic_repo.create_topic(subject_id=subject.id, name="Momentum")

    scheduler = _build_scheduler(session, date(2026, 4, 9), tmp_path)
    first_revision = scheduler.schedule_new_topic(topic.id)
    next_revision = scheduler.record_revision(
        first_revision.id,
        rating=ConfidenceRating.GOOD,
        completed_at=datetime(2026, 4, 9, 10, 0, 0),
    )
    session.commit()

    completed_revision = session.get(Revision, first_revision.id)
    assert completed_revision is not None
    assert completed_revision.personalized_interval_days is None
    assert completed_revision.fsrs_interval_days == next_revision.interval_days_after
    assert next_revision.scheduler_source == "fsrs"


def test_scheduler_uses_personalized_interval_after_training(session, tmp_path) -> None:
    scheduler, user_id = _seed_personal_history(session, tmp_path, record_count=20)

    user_topic = (
        session.query(Revision)
        .filter(Revision.is_completed.is_(False))
        .order_by(Revision.created_at.desc())
        .first()
    )
    assert user_topic is not None

    follow_up = scheduler.record_revision(
        user_topic.id,
        rating=ConfidenceRating.GOOD,
        completed_at=datetime.combine(user_topic.scheduled_date, datetime.min.time()).replace(hour=11),
    )
    session.commit()

    completed_revision = session.get(Revision, user_topic.id)
    assert completed_revision is not None
    assert completed_revision.personalized_interval_days is not None
    assert completed_revision.fsrs_interval_days is not None
    assert follow_up.scheduler_source == "personalized"
    assert scheduler.forgetting_curve_model.load(user_id) is not None


def test_model_retrains_after_ten_new_records(session, tmp_path) -> None:
    scheduler, user_id = _seed_personal_history(session, tmp_path, record_count=20)
    initial_artifact = scheduler.forgetting_curve_model.load(user_id)
    assert initial_artifact is not None

    open_revisions = (
        session.query(Revision)
        .filter(Revision.is_completed.is_(False))
        .order_by(Revision.scheduled_date)
        .all()
    )
    current_revision = open_revisions[-1]
    current_day = current_revision.scheduled_date
    for _ in range(10):
        current_day = current_day + timedelta(days=1)
        current_revision = scheduler.record_revision(
            current_revision.id,
            rating=ConfidenceRating.GOOD,
            completed_at=datetime.combine(current_day, datetime.min.time()).replace(hour=8),
        )
    session.commit()

    updated_artifact = scheduler.forgetting_curve_model.load(user_id)
    assert updated_artifact is not None
    assert updated_artifact.trained_on_records >= initial_artifact.trained_on_records + 10
