from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable

from sqlalchemy import func, select
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
REVIEW_HOUR_BY_DIFFICULTY: dict[str, int] = {
    "easy": 15,
    "medium": 11,
    "hard": 9,
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
RATING_TO_MASTERY_DELTA: dict[ConfidenceRating, float] = {
    ConfidenceRating.AGAIN: -12.0,
    ConfidenceRating.HARD: 3.0,
    ConfidenceRating.GOOD: 8.0,
    ConfidenceRating.EASY: 12.0,
}
MIN_STABILITY = 0.35
MAX_STABILITY = 365.0
MAX_INTERVAL_DAYS = 365


@dataclass(frozen=True)
class ScheduleSnapshot:
    interval_days: int
    stability: float
    difficulty_adjustment: float
    source: str


class SchedulerService:
    """Deterministic single-user revision scheduling service."""

    def __init__(self, session: Session, today_provider: Callable[[], date] | None = None) -> None:
        self.session = session
        self._today_provider = today_provider or date.today

    def _today(self) -> date:
        return self._today_provider()

    def get_due_today(self, *, for_date: date | None = None) -> list[Revision]:
        current_date = for_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.status == "open", func.date(Revision.due_at) == current_date.isoformat())
            .order_by(Revision.due_at, Revision.created_at)
        )
        return list(self.session.scalars(stmt))

    def get_overdue(self, *, for_date: date | None = None) -> list[Revision]:
        current_date = for_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.status == "open", func.date(Revision.due_at) < current_date.isoformat())
            .order_by(Revision.due_at, Revision.created_at)
        )
        return list(self.session.scalars(stmt))

    def get_upcoming(self, *, from_date: date | None = None) -> list[Revision]:
        current_date = from_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.status == "open", func.date(Revision.due_at) > current_date.isoformat())
            .order_by(Revision.due_at, Revision.created_at)
        )
        return list(self.session.scalars(stmt))

    def schedule_new_topic(self, topic_id: int | str, *, scheduled_for: date | None = None) -> Revision:
        topic = self._require_topic(topic_id)
        self._ensure_single_active_revision(topic.id)

        difficulty = self._difficulty_key(topic)
        interval_days = INITIAL_INTERVAL_BY_DIFFICULTY[difficulty]
        stability = INITIAL_STABILITY_BY_DIFFICULTY[difficulty]
        due_day = scheduled_for or self._today()

        revision = Revision(
            topic_id=topic.id,
            due_at=self._next_available_due_datetime(due_day, difficulty),
            status="open",
            interval_days=float(interval_days),
            previous_interval_days=0.0,
            stability=stability,
            difficulty_adjustment=self._base_difficulty_adjustment(topic),
            overdue_days=0.0,
            notes="initial_schedule",
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def record_revision(
        self,
        revision_id: int | str,
        *,
        rating: ConfidenceRating,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self._require_revision(revision_id)
        if revision.status != "open":
            raise ValueError(f"Revision {revision_id} is not open")

        topic = revision.topic
        finished_at = completed_at or datetime.combine(self._today(), time(9, 0))
        review_day = finished_at.date()
        overdue_days = max((review_day - revision.due_at.date()).days, 0)
        previous_interval = max(int(round(revision.interval_days or self._fallback_previous_interval(topic))), 1)
        snapshot = self._build_next_snapshot(
            topic=topic,
            rating=rating,
            previous_interval=previous_interval,
            overdue_days=overdue_days,
            review_day=review_day,
            current_revision=revision,
        )

        revision.status = "completed"
        revision.completed_at = finished_at
        revision.rating = rating.value
        revision.previous_interval_days = float(previous_interval)
        revision.interval_days = float(snapshot.interval_days)
        revision.stability = snapshot.stability
        revision.difficulty_adjustment = snapshot.difficulty_adjustment
        revision.overdue_days = float(overdue_days)
        revision.notes = snapshot.source

        topic.review_count = int(topic.review_count or 0) + 1
        topic.last_reviewed_at = finished_at
        topic.mastery_score = self._next_mastery_score(topic.mastery_score, rating, overdue_days)

        next_revision = Revision(
            topic_id=topic.id,
            due_at=self._next_available_due_datetime(review_day + timedelta(days=snapshot.interval_days), self._difficulty_key(topic), exclude_revision_id=revision.id),
            status="open",
            scheduled_from_revision_id=revision.id,
            interval_days=float(snapshot.interval_days),
            previous_interval_days=float(previous_interval),
            stability=snapshot.stability,
            difficulty_adjustment=snapshot.difficulty_adjustment,
            overdue_days=0.0,
            notes=snapshot.source,
        )
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                logged_at=finished_at,
                source="revision_review",
                score=topic.mastery_score,
                confidence=self._confidence_score_from_rating(rating, overdue_days),
                outcome=rating.value,
                notes=f"{snapshot.source}; overdue_days={overdue_days}; next_interval={snapshot.interval_days}",
            )
        )
        self.session.add(next_revision)
        self.session.flush()
        return next_revision

    def review(
        self,
        topic_id: int | str,
        rating: ConfidenceRating,
        *,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self._active_revision_for_topic(topic_id)
        if revision is None:
            raise ValueError(f"Topic {topic_id} has no active revision to review")
        return self.record_revision(revision.id, rating=rating, completed_at=completed_at)

    def reschedule_after_miss(self, revision_id: int | str, *, reschedule_from: date | None = None) -> Revision:
        revision = self._require_revision(revision_id)
        if revision.status != "open":
            raise ValueError(f"Revision {revision_id} is not open")

        topic = revision.topic
        current_day = reschedule_from or self._today()
        overdue_days = max((current_day - revision.due_at.date()).days, 0)
        previous_interval = max(int(round(revision.interval_days or self._fallback_previous_interval(topic))), 1)
        next_interval = max(1, min(previous_interval, round(previous_interval * 0.5)))
        next_stability = max((revision.stability or INITIAL_STABILITY_BY_DIFFICULTY[self._difficulty_key(topic)]) * 0.65, MIN_STABILITY)
        next_adjustment = min(max((revision.difficulty_adjustment or self._base_difficulty_adjustment(topic)) + 0.08, -0.4), 0.6)
        next_interval = self._cap_interval_for_exam(topic, current_day, next_interval)

        revision.status = "missed"
        revision.completed_at = datetime.combine(current_day, time(8, 0))
        revision.previous_interval_days = float(previous_interval)
        revision.interval_days = float(next_interval)
        revision.stability = next_stability
        revision.difficulty_adjustment = next_adjustment
        revision.overdue_days = float(overdue_days)
        revision.notes = "missed_review"

        replacement = Revision(
            topic_id=topic.id,
            due_at=self._next_available_due_datetime(current_day + timedelta(days=next_interval), self._difficulty_key(topic), exclude_revision_id=revision.id),
            status="open",
            scheduled_from_revision_id=revision.id,
            interval_days=float(next_interval),
            previous_interval_days=float(previous_interval),
            stability=next_stability,
            difficulty_adjustment=next_adjustment,
            overdue_days=0.0,
            notes="missed_review",
        )
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                logged_at=revision.completed_at,
                source="missed_review",
                score=topic.mastery_score,
                confidence=0.2,
                outcome="missed",
                notes=f"overdue_days={overdue_days}; next_interval={next_interval}",
            )
        )
        self.session.add(replacement)
        self.session.flush()
        return replacement

    def _build_next_snapshot(
        self,
        *,
        topic: Topic,
        rating: ConfidenceRating,
        previous_interval: int,
        overdue_days: int,
        review_day: date,
        current_revision: Revision,
    ) -> ScheduleSnapshot:
        difficulty = self._difficulty_key(topic)
        stability = current_revision.stability or INITIAL_STABILITY_BY_DIFFICULTY[difficulty]
        adjustment = current_revision.difficulty_adjustment
        if adjustment is None:
            adjustment = self._base_difficulty_adjustment(topic)

        if rating == ConfidenceRating.AGAIN:
            interval_days = 1
            next_stability = max(stability * 0.55, MIN_STABILITY)
            next_adjustment = min(max(adjustment + RATING_TO_DIFFICULTY_DELTA[rating], -0.4), 0.6)
            interval_days = self._cap_interval_for_exam(topic, review_day, interval_days)
            return ScheduleSnapshot(interval_days, round(next_stability, 3), round(next_adjustment, 3), "recovery_review")

        review_bonus = 1.0 + min((topic.review_count or 0) * 0.04, 0.4)
        interval_factor = self._difficulty_interval_factor(difficulty)
        overdue_factor = self._overdue_penalty(overdue_days)
        raw_interval = previous_interval * RATING_TO_GROWTH[rating] * review_bonus * interval_factor * overdue_factor
        interval_days = max(1, min(round(raw_interval), MAX_INTERVAL_DAYS))
        interval_days = self._cap_interval_for_exam(topic, review_day, interval_days)

        next_stability = max(min(stability * RATING_TO_GROWTH[rating] * overdue_factor, MAX_STABILITY), MIN_STABILITY)
        next_adjustment = min(max(adjustment + RATING_TO_DIFFICULTY_DELTA[rating], -0.4), 0.6)
        return ScheduleSnapshot(interval_days, round(next_stability, 3), round(next_adjustment, 3), "deterministic")

    def _difficulty_key(self, topic: Topic) -> str:
        difficulty = topic.difficulty.value if hasattr(topic.difficulty, "value") else topic.difficulty
        return str(difficulty or "medium").lower()

    def _difficulty_interval_factor(self, difficulty: str) -> float:
        return {
            "easy": 1.15,
            "medium": 1.0,
            "hard": 0.72,
        }.get(difficulty, 1.0)

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

    def _days_until_exam(self, topic: Topic, current_day: date) -> int | None:
        exam_date = topic.exam_date_override or topic.subject.exam_date
        if exam_date is None:
            return None
        return (exam_date - current_day).days

    def _combine_due_datetime(self, due_day: date, difficulty: str) -> datetime:
        return datetime.combine(due_day, time(REVIEW_HOUR_BY_DIFFICULTY.get(difficulty, 11), 0))

    def _next_available_due_datetime(
        self,
        due_day: date,
        difficulty: str,
        *,
        exclude_revision_id: int | None = None,
    ) -> datetime:
        preferred_dt = self._combine_due_datetime(due_day, difficulty)
        stmt = select(Revision.due_at).where(func.date(Revision.due_at) == due_day.isoformat())
        if exclude_revision_id is not None:
            stmt = stmt.where(Revision.id != int(exclude_revision_id))
        existing = {item.replace(second=0, microsecond=0) for item in self.session.scalars(stmt)}
        if preferred_dt not in existing:
            return preferred_dt

        candidate_hours = range(8, 21)
        ordered_slots = sorted(
            (datetime.combine(due_day, time(hour, minute)) for hour in candidate_hours for minute in (0, 30)),
            key=lambda slot: (abs((slot - preferred_dt).total_seconds()), slot),
        )
        for slot in ordered_slots:
            if slot not in existing:
                return slot

        latest = max(existing) if existing else preferred_dt
        overflow = latest + timedelta(minutes=30)
        if overflow.date() != due_day:
            return datetime.combine(due_day, time(20, 30))
        return overflow

    def _base_difficulty_adjustment(self, topic: Topic) -> float:
        return {
            "easy": -0.1,
            "medium": 0.0,
            "hard": 0.12,
        }.get(self._difficulty_key(topic), 0.0)

    def _confidence_score_from_rating(self, rating: ConfidenceRating, overdue_days: int) -> float:
        base = {
            ConfidenceRating.AGAIN: 0.2,
            ConfidenceRating.HARD: 0.45,
            ConfidenceRating.GOOD: 0.75,
            ConfidenceRating.EASY: 0.9,
        }[rating]
        return round(max(0.1, min(1.0, base - overdue_days * 0.04)), 4)

    def _next_mastery_score(self, current_score: float | None, rating: ConfidenceRating, overdue_days: int) -> float:
        score = float(current_score or 0.0) + RATING_TO_MASTERY_DELTA[rating] - overdue_days * 1.5
        return round(max(0.0, min(100.0, score)), 1)

    def _fallback_previous_interval(self, topic: Topic) -> int:
        stmt = (
            select(Revision)
            .where(Revision.topic_id == topic.id, Revision.status == "completed")
            .order_by(Revision.completed_at.desc(), Revision.id.desc())
        )
        latest = self.session.scalars(stmt).first()
        if latest is None or latest.interval_days is None:
            return INITIAL_INTERVAL_BY_DIFFICULTY[self._difficulty_key(topic)]
        return max(1, int(round(latest.interval_days)))

    def _active_revision_for_topic(self, topic_id: int | str) -> Revision | None:
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.topic_id == int(topic_id), Revision.status == "open")
            .order_by(Revision.due_at, Revision.created_at)
        )
        return self.session.scalars(stmt).first()

    def _ensure_single_active_revision(self, topic_id: int) -> None:
        if self._active_revision_for_topic(topic_id) is not None:
            raise ValueError(f"Topic {topic_id} already has an active scheduled revision")

    def _require_topic(self, topic_id: int | str) -> Topic:
        topic = self.session.get(Topic, int(topic_id))
        if topic is None:
            raise ValueError(f"Topic {topic_id} does not exist")
        return topic

    def _require_revision(self, revision_id: int | str) -> Revision:
        revision = self.session.get(Revision, int(revision_id))
        if revision is None:
            raise ValueError(f"Revision {revision_id} does not exist")
        return revision
