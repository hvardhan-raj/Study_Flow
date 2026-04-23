from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import ConfidenceRating, PerformanceLog, Revision, Topic
from services.fsrs import FSRSScheduler, FSRSState

REVIEW_HOUR_BY_DIFFICULTY: dict[str, int] = {
    "easy": 15,
    "medium": 11,
    "hard": 9,
}
RATING_TO_MASTERY_DELTA: dict[ConfidenceRating, float] = {
    ConfidenceRating.AGAIN: -12.0,
    ConfidenceRating.HARD: 3.0,
    ConfidenceRating.GOOD: 8.0,
    ConfidenceRating.EASY: 12.0,
}
MAX_INTERVAL_DAYS = 365


@dataclass(frozen=True)
class ScheduleSnapshot:
    interval_days: int
    stability: float
    difficulty: float
    retrievability: float
    source: str


class SchedulerService:
    """FSRS-backed single-user scheduler with one active revision per topic."""

    def __init__(
        self,
        session: Session,
        today_provider: Callable[[], date] | None = None,
        fsrs: FSRSScheduler | None = None,
    ) -> None:
        self.session = session
        self._today_provider = today_provider or date.today
        self._fsrs = fsrs or FSRSScheduler()

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

        due_day = scheduled_for or self._today()
        initial_state = self._fsrs.initial_state(topic_difficulty=self._baseline_difficulty(topic))
        revision = Revision(
            topic_id=topic.id,
            due_at=self._next_available_due_datetime(due_day, self._difficulty_key(topic)),
            status="open",
            interval_days=0.0,
            previous_interval_days=0.0,
            stability=initial_state.stability,
            difficulty_adjustment=initial_state.difficulty,
            overdue_days=0.0,
            notes="fsrs_initial",
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
        elapsed_days = self._elapsed_days_for_revision(revision, overdue_days)
        baseline_difficulty = self._baseline_difficulty(topic)
        state = FSRSState(
            difficulty=revision.difficulty_adjustment or baseline_difficulty,
            stability=revision.stability or self._fsrs.initial_state(topic_difficulty=baseline_difficulty).stability,
        )
        fsrs_result = self._fsrs.review(
            state=state,
            rating=rating,
            elapsed_days=elapsed_days,
            baseline_difficulty=baseline_difficulty,
        )
        interval_days = max(
            1,
            round(min(fsrs_result.interval_days, MAX_INTERVAL_DAYS) * self._overdue_penalty(overdue_days)) - overdue_days,
        )
        interval_days = self._cap_interval_for_exam(topic, review_day, interval_days)
        snapshot = ScheduleSnapshot(
            interval_days=interval_days,
            stability=round(fsrs_result.stability * self._overdue_penalty(overdue_days), 3),
            difficulty=round(fsrs_result.difficulty, 3),
            retrievability=round(fsrs_result.retrievability, 4),
            source="fsrs_review",
        )

        revision.status = "completed"
        revision.completed_at = finished_at
        revision.rating = rating.value
        revision.previous_interval_days = float(elapsed_days)
        revision.interval_days = float(snapshot.interval_days)
        revision.stability = snapshot.stability
        revision.difficulty_adjustment = snapshot.difficulty
        revision.overdue_days = float(overdue_days)
        revision.notes = f"{snapshot.source}; retrievability={snapshot.retrievability}"

        topic.review_count = int(topic.review_count or 0) + 1
        topic.last_reviewed_at = finished_at
        topic.mastery_score = self._next_mastery_score(topic.mastery_score, rating, overdue_days)

        next_revision = Revision(
            topic_id=topic.id,
            due_at=self._next_available_due_datetime(
                review_day + timedelta(days=snapshot.interval_days),
                self._difficulty_key(topic),
                exclude_revision_id=revision.id,
            ),
            status="open",
            scheduled_from_revision_id=revision.id,
            interval_days=float(snapshot.interval_days),
            previous_interval_days=float(elapsed_days),
            stability=snapshot.stability,
            difficulty_adjustment=snapshot.difficulty,
            overdue_days=0.0,
            notes=f"{snapshot.source}; retrievability={snapshot.retrievability}",
        )
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                logged_at=finished_at,
                source="fsrs_review",
                score=topic.mastery_score,
                confidence=snapshot.retrievability,
                outcome=rating.value,
                notes=f"elapsed_days={elapsed_days}; overdue_days={overdue_days}; next_interval={snapshot.interval_days}; difficulty={snapshot.difficulty}; stability={snapshot.stability}",
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
        elapsed_days = self._elapsed_days_for_revision(revision, overdue_days)
        baseline_difficulty = self._baseline_difficulty(topic)
        state = FSRSState(
            difficulty=revision.difficulty_adjustment or baseline_difficulty,
            stability=revision.stability or self._fsrs.initial_state(topic_difficulty=baseline_difficulty).stability,
        )
        fsrs_result = self._fsrs.review(
            state=state,
            rating=ConfidenceRating.AGAIN,
            elapsed_days=elapsed_days,
            baseline_difficulty=baseline_difficulty,
        )
        interval_days = self._cap_interval_for_exam(topic, current_day, min(fsrs_result.interval_days, MAX_INTERVAL_DAYS))

        revision.status = "missed"
        revision.completed_at = datetime.combine(current_day, time(8, 0))
        revision.rating = ConfidenceRating.AGAIN.value
        revision.previous_interval_days = float(elapsed_days)
        revision.interval_days = float(interval_days)
        revision.stability = round(fsrs_result.stability, 3)
        revision.difficulty_adjustment = round(fsrs_result.difficulty, 3)
        revision.overdue_days = float(overdue_days)
        revision.notes = f"fsrs_missed; retrievability={round(fsrs_result.retrievability, 4)}"

        replacement = Revision(
            topic_id=topic.id,
            due_at=self._next_available_due_datetime(
                current_day + timedelta(days=interval_days),
                self._difficulty_key(topic),
                exclude_revision_id=revision.id,
            ),
            status="open",
            scheduled_from_revision_id=revision.id,
            interval_days=float(interval_days),
            previous_interval_days=float(elapsed_days),
            stability=round(fsrs_result.stability, 3),
            difficulty_adjustment=round(fsrs_result.difficulty, 3),
            overdue_days=0.0,
            notes=f"fsrs_missed; retrievability={round(fsrs_result.retrievability, 4)}",
        )
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                logged_at=revision.completed_at,
                source="fsrs_missed",
                score=topic.mastery_score,
                confidence=round(fsrs_result.retrievability, 4),
                outcome="missed",
                notes=f"elapsed_days={elapsed_days}; overdue_days={overdue_days}; next_interval={interval_days}",
            )
        )
        self.session.add(replacement)
        self.session.flush()
        return replacement

    def _difficulty_key(self, topic: Topic) -> str:
        difficulty = topic.difficulty.value if hasattr(topic.difficulty, "value") else topic.difficulty
        return str(difficulty or "medium").lower()

    def _baseline_difficulty(self, topic: Topic) -> float:
        return {
            "easy": 4.2,
            "medium": 5.6,
            "hard": 7.2,
        }.get(self._difficulty_key(topic), 5.6)

    def _elapsed_days_for_revision(self, revision: Revision, overdue_days: int) -> float:
        scheduled_interval = max(float(revision.interval_days or 0.0), 0.0)
        return scheduled_interval + max(float(overdue_days), 0.0)

    def _cap_interval_for_exam(self, topic: Topic, review_day: date, candidate_interval: int) -> int:
        exam_distance = self._days_until_exam(topic, review_day)
        if exam_distance is None:
            return max(1, candidate_interval)
        if exam_distance <= 0:
            return 1
        if exam_distance <= 7:
            return max(1, min(candidate_interval, max(1, exam_distance // 2 or 1)))
        if exam_distance <= 21:
            return max(1, min(candidate_interval, max(1, exam_distance - 2)))
        return max(1, min(candidate_interval, exam_distance))

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
        stmt = select(Revision.due_at).where(Revision.status == "open", func.date(Revision.due_at) == due_day.isoformat())
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

    def _next_mastery_score(self, current_score: float | None, rating: ConfidenceRating, overdue_days: int) -> float:
        score = float(current_score or 0.0) + RATING_TO_MASTERY_DELTA[rating] - overdue_days * 1.5
        return round(max(0.0, min(100.0, score)), 1)

    def _overdue_penalty(self, overdue_days: int) -> float:
        if overdue_days <= 0:
            return 1.0
        return max(0.15, 1 / (1 + overdue_days * 0.8))

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
