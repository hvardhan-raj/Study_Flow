from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models import ConfidenceRating, PerformanceLog, Revision, Topic

INITIAL_STABILITY_BY_DIFFICULTY: dict[str, float] = {
    "easy": 1.8,
    "medium": 1.2,
    "hard": 0.8,
}
INITIAL_INTERVAL_BY_DIFFICULTY: dict[str, int] = {
    "easy": 2,
    "medium": 1,
    "hard": 1,
}
RATING_TO_GROWTH: dict[ConfidenceRating, float] = {
    ConfidenceRating.AGAIN: 0.45,
    ConfidenceRating.HARD: 1.15,
    ConfidenceRating.GOOD: 1.75,
    ConfidenceRating.EASY: 2.5,
}
RATING_TO_DIFFICULTY_DELTA: dict[ConfidenceRating, float] = {
    ConfidenceRating.AGAIN: 0.12,
    ConfidenceRating.HARD: 0.05,
    ConfidenceRating.GOOD: -0.03,
    ConfidenceRating.EASY: -0.08,
}
MIN_STABILITY = 0.35
MAX_STABILITY = 365.0
MAX_INTERVAL_DAYS = 365


@dataclass(frozen=True)
class ScheduleSnapshot:
    stability: float
    difficulty: float
    interval_days: int
    scheduler_source: str


class SchedulerService:
    """Deterministic single-user revision scheduling."""

    def __init__(self, session: Session, today_provider: callable | None = None) -> None:
        self.session = session
        self._today_provider = today_provider or date.today

    def _today(self) -> date:
        return self._today_provider()

    def get_due_today(self, *, for_date: date | None = None) -> list[Revision]:
        current_date = for_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.is_completed.is_(False), Revision.scheduled_date == current_date)
            .order_by(Revision.created_at)
        )
        return list(self.session.scalars(stmt))

    def get_overdue(self, *, for_date: date | None = None) -> list[Revision]:
        current_date = for_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.is_completed.is_(False), Revision.scheduled_date < current_date)
            .order_by(Revision.scheduled_date, Revision.created_at)
        )
        return list(self.session.scalars(stmt))

    def get_upcoming(self, *, from_date: date | None = None) -> list[Revision]:
        current_date = from_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.is_completed.is_(False), Revision.scheduled_date > current_date)
            .order_by(Revision.scheduled_date, Revision.created_at)
        )
        return list(self.session.scalars(stmt))

    def schedule_new_topic(self, topic_id: str, *, scheduled_for: date | None = None) -> Revision:
        topic = self._require_topic(topic_id)
        start_date = scheduled_for or self._today()
        self._ensure_single_active_revision(topic.id)

        initial_interval = INITIAL_INTERVAL_BY_DIFFICULTY[topic.difficulty.value]
        initial_stability = INITIAL_STABILITY_BY_DIFFICULTY[topic.difficulty.value]
        initial_difficulty = self._normalize_difficulty(topic)

        topic.fsrs_stability = initial_stability
        topic.fsrs_difficulty = initial_difficulty
        topic.fsrs_last_review = None
        topic.fsrs_review_count = 0
        topic.fsrs_due_date = start_date

        revision = Revision(
            topic_id=topic.id,
            scheduled_date=start_date,
            interval_days_before=0,
            interval_days_after=initial_interval,
            fsrs_interval_days=initial_interval,
            scheduler_source="initial_schedule",
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def record_revision(
        self,
        revision_id: str,
        *,
        rating: ConfidenceRating,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self._require_revision(revision_id)
        if revision.is_completed:
            raise ValueError(f"Revision {revision_id} is already completed")

        topic = revision.topic
        finished_at = completed_at or datetime.combine(self._today(), time(9, 0))
        review_day = finished_at.date()
        overdue_days = max((review_day - revision.scheduled_date).days, 0)
        days_since_last_review = self._days_since_last_review(topic, review_day)
        previous_interval = self._previous_interval_days(topic)
        snapshot = self._build_next_snapshot(
            topic=topic,
            rating=rating,
            previous_interval=previous_interval,
            overdue_days=overdue_days,
            review_day=review_day,
        )

        revision.is_completed = True
        revision.is_missed = False
        revision.completed_at = finished_at
        revision.confidence_rating = rating
        revision.interval_days_before = previous_interval
        revision.interval_days_after = snapshot.interval_days
        revision.fsrs_interval_days = snapshot.interval_days
        revision.scheduled_days_overdue = overdue_days
        revision.scheduler_source = snapshot.scheduler_source

        topic.fsrs_stability = snapshot.stability
        topic.fsrs_difficulty = snapshot.difficulty
        topic.fsrs_last_review = review_day
        topic.fsrs_review_count += 1
        topic.fsrs_due_date = review_day + timedelta(days=snapshot.interval_days)

        self._clear_other_open_revisions(topic.id, keep_revision_id=revision.id)
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                revision_id=revision.id,
                days_since_last_review=days_since_last_review,
                review_count_at_time=topic.fsrs_review_count,
                difficulty_score_at_time=topic.difficulty_score,
                scheduled_days_overdue=overdue_days,
                hour_of_day=finished_at.hour,
                day_of_week=finished_at.weekday(),
                confidence_rating=rating,
                predicted_confidence=self._predicted_confidence(snapshot.difficulty, overdue_days),
                scheduler_source=snapshot.scheduler_source,
            )
        )

        next_revision = Revision(
            topic_id=topic.id,
            scheduled_date=topic.fsrs_due_date,
            interval_days_before=snapshot.interval_days,
            interval_days_after=snapshot.interval_days,
            fsrs_interval_days=snapshot.interval_days,
            scheduled_days_overdue=0,
            scheduler_source=snapshot.scheduler_source,
        )
        self.session.add(next_revision)
        self.session.flush()
        return next_revision

    def review(
        self,
        topic_id: str,
        rating: ConfidenceRating,
        *,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self._active_revision_for_topic(topic_id)
        if revision is None:
            raise ValueError(f"Topic {topic_id} has no active revision to review")
        return self.record_revision(revision.id, rating=rating, completed_at=completed_at)

    def reschedule_after_miss(self, revision_id: str, *, reschedule_from: date | None = None) -> Revision:
        revision = self._require_revision(revision_id)
        if revision.is_completed:
            raise ValueError(f"Revision {revision_id} is already completed")

        topic = revision.topic
        current_date = reschedule_from or self._today()
        overdue_days = max((current_date - revision.scheduled_date).days, 0)
        previous_interval = max(revision.interval_days_after or self._previous_interval_days(topic), 1)
        penalized_interval = max(1, min(previous_interval, round(previous_interval * 0.5)))
        penalized_stability = max((topic.fsrs_stability or 1.0) * max(0.45, 1 - overdue_days * 0.08), MIN_STABILITY)

        revision.is_missed = True
        revision.scheduled_days_overdue = overdue_days
        revision.interval_days_before = previous_interval
        revision.interval_days_after = penalized_interval
        revision.scheduler_source = "missed_review"

        topic.fsrs_stability = penalized_stability
        topic.fsrs_difficulty = min(max((topic.fsrs_difficulty or self._normalize_difficulty(topic)) + 0.08, 0.1), 0.95)
        topic.fsrs_due_date = current_date + timedelta(days=penalized_interval)

        self._clear_other_open_revisions(topic.id, keep_revision_id=revision.id)
        revision.scheduled_date = current_date
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                revision_id=revision.id,
                days_since_last_review=self._days_since_last_review(topic, current_date),
                review_count_at_time=topic.fsrs_review_count,
                difficulty_score_at_time=topic.difficulty_score,
                scheduled_days_overdue=overdue_days,
                hour_of_day=None,
                day_of_week=current_date.weekday(),
                confidence_rating=ConfidenceRating.AGAIN,
                predicted_confidence=self._predicted_confidence(topic.fsrs_difficulty or 0.5, overdue_days),
                scheduler_source="missed_review",
            )
        )
        self.session.flush()
        return revision

    def _build_next_snapshot(
        self,
        *,
        topic: Topic,
        rating: ConfidenceRating,
        previous_interval: int,
        overdue_days: int,
        review_day: date,
    ) -> ScheduleSnapshot:
        current_stability = topic.fsrs_stability or INITIAL_STABILITY_BY_DIFFICULTY[topic.difficulty.value]
        current_difficulty = topic.fsrs_difficulty or self._normalize_difficulty(topic)

        if rating == ConfidenceRating.AGAIN:
            interval = 1
            stability = max(current_stability * 0.55, MIN_STABILITY)
            difficulty = min(max(current_difficulty + RATING_TO_DIFFICULTY_DELTA[rating], 0.1), 0.95)
            interval = self._cap_interval_for_exam(topic, review_day, interval)
            return ScheduleSnapshot(round(stability, 3), round(difficulty, 3), interval, "recovery_review")

        base_interval = max(previous_interval, INITIAL_INTERVAL_BY_DIFFICULTY[topic.difficulty.value], 1)
        growth = RATING_TO_GROWTH[rating]
        stability = max(min(current_stability * growth, MAX_STABILITY), MIN_STABILITY)
        interval = max(1, round(base_interval * growth))
        interval = max(1, round(interval * self._difficulty_interval_factor(topic)))
        interval = max(1, int(interval * self._overdue_penalty(overdue_days)))
        interval = self._cap_interval_for_exam(topic, review_day, interval)
        difficulty = min(max(current_difficulty + RATING_TO_DIFFICULTY_DELTA[rating], 0.1), 0.95)
        return ScheduleSnapshot(round(stability, 3), round(difficulty, 3), min(interval, MAX_INTERVAL_DAYS), "deterministic")

    def _difficulty_interval_factor(self, topic: Topic) -> float:
        return {
            "easy": 1.15,
            "medium": 1.0,
            "hard": 0.72,
        }[topic.difficulty.value]

    def _overdue_penalty(self, overdue_days: int) -> float:
        if overdue_days <= 0:
            return 1.0
        return max(0.45, 1 - overdue_days * 0.08)

    def _cap_interval_for_exam(self, topic: Topic, review_day: date, candidate_interval: int) -> int:
        exam_distance = self._days_until_exam(topic, review_day)
        if exam_distance is None:
            return min(candidate_interval, MAX_INTERVAL_DAYS)
        if exam_distance <= 0:
            return 1
        if exam_distance <= 7:
            return max(1, min(candidate_interval, max(1, exam_distance // 2 or 1)))
        if exam_distance <= 21:
            return max(1, min(candidate_interval, max(1, exam_distance - 2)))
        return min(candidate_interval, exam_distance)

    def _predicted_confidence(self, difficulty: float, overdue_days: int) -> float:
        baseline = 1.0 - max(0.0, difficulty - 0.25)
        penalty = overdue_days * 0.05
        return round(max(0.1, min(1.0, baseline - penalty)), 4)

    def _days_until_exam(self, topic: Topic, current_date: date) -> int | None:
        exam_date = topic.exam_date or topic.subject.exam_date
        if exam_date is None:
            return None
        return (exam_date - current_date).days

    def _normalize_difficulty(self, topic: Topic) -> float:
        return min(max(topic.difficulty_score or 0.5, 0.1), 0.95)

    def _previous_interval_days(self, topic: Topic) -> int:
        if topic.fsrs_last_review and topic.fsrs_due_date:
            return max((topic.fsrs_due_date - topic.fsrs_last_review).days, 0)
        return 0

    def _days_since_last_review(self, topic: Topic, current_date: date) -> int:
        if topic.fsrs_last_review is None:
            return 0
        return max((current_date - topic.fsrs_last_review).days, 0)

    def _active_revision_for_topic(self, topic_id: str) -> Revision | None:
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.topic_id == topic_id, Revision.is_completed.is_(False))
            .order_by(Revision.scheduled_date, Revision.created_at)
        )
        return self.session.scalars(stmt).first()

    def _ensure_single_active_revision(self, topic_id: str) -> None:
        if self._active_revision_for_topic(topic_id) is not None:
            raise ValueError(f"Topic {topic_id} already has an active scheduled revision")

    def _clear_other_open_revisions(self, topic_id: str, *, keep_revision_id: str) -> None:
        stmt = select(Revision).where(
            Revision.topic_id == topic_id,
            Revision.is_completed.is_(False),
            Revision.id != keep_revision_id,
        )
        for duplicate in self.session.scalars(stmt):
            self.session.delete(duplicate)

    def _require_topic(self, topic_id: str) -> Topic:
        topic = self.session.get(Topic, topic_id)
        if topic is None:
            raise ValueError(f"Topic {topic_id} does not exist")
        return topic

    def _require_revision(self, revision_id: str) -> Revision:
        revision = self.session.get(Revision, revision_id)
        if revision is None:
            raise ValueError(f"Revision {revision_id} does not exist")
        return revision
