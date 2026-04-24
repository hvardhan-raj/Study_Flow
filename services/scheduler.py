from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import AppSetting, ConfidenceRating, PerformanceLog, Revision, Topic

BUFFER_MINUTES = 5
DEFAULT_DAILY_TIME_MINUTES = 120
DEFAULT_PREFERRED_TIME = "18:00"
DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
DURATION_BY_DIFFICULTY: dict[str, int] = {
    "easy": 15,
    "medium": 30,
    "hard": 45,
}
QUALITY_BY_RATING: dict[ConfidenceRating, int] = {
    ConfidenceRating.AGAIN: 1,
    ConfidenceRating.HARD: 3,
    ConfidenceRating.GOOD: 4,
    ConfidenceRating.EASY: 5,
}
RATING_TO_MASTERY_DELTA: dict[ConfidenceRating, float] = {
    ConfidenceRating.AGAIN: -10.0,
    ConfidenceRating.HARD: 2.0,
    ConfidenceRating.GOOD: 6.0,
    ConfidenceRating.EASY: 9.0,
}


class SchedulerService:
    """Single-user SM-2 scheduler persisted entirely in the existing schema."""

    def __init__(
        self,
        session: Session,
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        self.session = session
        self._today_provider = today_provider or date.today

    def _today(self) -> date:
        return self._today_provider()

    def create_first_revision(self, topic_id: int | str, *, scheduled_for: date | None = None) -> Revision:
        topic = self._require_topic(topic_id)
        self._ensure_single_active_revision(topic.id)

        due_day = scheduled_for or self._today()
        preferred_time = self._preferred_time()
        revision = Revision(
            topic_id=topic.id,
            due_at=datetime.combine(due_day, preferred_time),
            status="open",
            interval_days=0.0,
            previous_interval_days=0.0,
            stability=1.0,
            difficulty_adjustment=DEFAULT_EASE_FACTOR,
            overdue_days=0.0,
            notes="sm2_initial",
        )
        self.session.add(revision)
        self.session.flush()
        self.rebalance_schedule(start_date=due_day)
        return revision

    def process_review(
        self,
        revision_id: int | str,
        rating: ConfidenceRating,
        *,
        completed_at: datetime | None = None,
    ) -> Revision:
        revision = self._require_revision(revision_id)
        if revision.status != "open":
            raise ValueError(f"Revision {revision_id} is not open")

        topic = revision.topic
        finished_at = completed_at or datetime.combine(self._today(), self._preferred_time())
        quality = QUALITY_BY_RATING[rating]
        repetition = max(0, int(topic.review_count or 0))
        previous_interval = max(float(revision.interval_days or 0.0), 0.0)
        ease_factor = max(float(revision.difficulty_adjustment or DEFAULT_EASE_FACTOR), MIN_EASE_FACTOR)
        overdue_days = max((finished_at.date() - revision.due_at.date()).days, 0)

        if quality < 3:
            next_repetition = 0
            next_interval = 1
        else:
            if repetition == 0:
                next_interval = 1
            elif repetition == 1:
                next_interval = 3
            else:
                next_interval = max(1, round(max(previous_interval, 1.0) * ease_factor))
            next_repetition = repetition + 1

        next_ease_factor = max(
            MIN_EASE_FACTOR,
            ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )

        revision.status = "completed"
        revision.completed_at = finished_at
        revision.rating = rating.value
        revision.previous_interval_days = previous_interval
        revision.interval_days = float(next_interval)
        revision.stability = float(next_repetition + 1)
        revision.difficulty_adjustment = round(next_ease_factor, 3)
        revision.overdue_days = float(overdue_days)
        revision.notes = f"sm2_review;q={quality};rep={next_repetition}"

        topic.review_count = next_repetition
        topic.last_reviewed_at = finished_at
        topic.mastery_score = self._next_mastery_score(topic.mastery_score, rating, overdue_days)

        next_revision = Revision(
            topic_id=topic.id,
            due_at=datetime.combine(finished_at.date() + timedelta(days=next_interval), self._preferred_time()),
            status="open",
            scheduled_from_revision_id=revision.id,
            interval_days=float(next_interval),
            previous_interval_days=previous_interval,
            stability=float(next_repetition + 1),
            difficulty_adjustment=round(next_ease_factor, 3),
            overdue_days=0.0,
            notes=f"sm2_scheduled;q={quality};rep={next_repetition}",
        )
        self.session.add(next_revision)
        self.session.add(
            PerformanceLog(
                topic_id=topic.id,
                logged_at=finished_at,
                source="sm2_review",
                score=topic.mastery_score,
                confidence=quality / 5.0,
                outcome=rating.value,
                notes=f"previous_interval={previous_interval};next_interval={next_interval};ease_factor={round(next_ease_factor, 3)};overdue_days={overdue_days}",
            )
        )
        self.session.flush()
        self.rebalance_schedule(start_date=finished_at.date())
        return next_revision

    def get_tasks_for_date(self, target_date: date) -> list[Revision]:
        self.rebalance_schedule(start_date=target_date)
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.status == "open", func.date(Revision.due_at) == target_date.isoformat())
            .order_by(Revision.due_at, Revision.created_at, Revision.id)
        )
        return list(self.session.scalars(stmt))

    def push_overflow_to_next_day(self, revision: Revision) -> Revision:
        next_day = revision.due_at.date() + timedelta(days=1)
        revision.due_at = datetime.combine(next_day, self._preferred_time())
        self.session.flush()
        return revision

    def schedule_new_topic(self, topic_id: int | str, *, scheduled_for: date | None = None) -> Revision:
        return self.create_first_revision(topic_id, scheduled_for=scheduled_for)

    def record_revision(
        self,
        revision_id: int | str,
        *,
        rating: ConfidenceRating,
        completed_at: datetime | None = None,
    ) -> Revision:
        return self.process_review(revision_id, rating, completed_at=completed_at)

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
        return self.process_review(revision.id, rating, completed_at=completed_at)

    def reschedule_after_miss(self, revision_id: int | str, *, reschedule_from: date | None = None) -> Revision:
        revision = self._require_revision(revision_id)
        if revision.status != "open":
            raise ValueError(f"Revision {revision_id} is not open")
        next_day = reschedule_from or (revision.due_at.date() + timedelta(days=1))
        revision.overdue_days = float(max((next_day - revision.due_at.date()).days, 0))
        revision.due_at = datetime.combine(next_day, self._preferred_time())
        revision.notes = "sm2_rescheduled;manual_pin"
        self.session.flush()
        self.rebalance_schedule(start_date=next_day)
        return revision

    def rebalance_schedule(self, *, start_date: date | None = None) -> None:
        revisions = list(
            self.session.scalars(
                select(Revision)
                .options(joinedload(Revision.topic).joinedload(Topic.subject))
                .where(Revision.status == "open")
                .order_by(Revision.due_at, Revision.created_at, Revision.id)
            )
        )
        if not revisions:
            return

        grouped: dict[date, list[Revision]] = {}
        for revision in revisions:
            grouped.setdefault(revision.due_at.date(), []).append(revision)

        preferred_time = self._preferred_time()
        daily_limit = self._daily_time_minutes()
        if start_date is not None:
            grouped = {day: items for day, items in grouped.items() if day >= start_date}
            if not grouped:
                return
            current_day = start_date
        else:
            current_day = min(revision.due_at.date() for revision in revisions)

        while grouped:
            if current_day not in grouped:
                future_days = [day for day in grouped if day >= current_day]
                current_day = min(future_days) if future_days else min(grouped)
            day_revisions = grouped.pop(current_day)
            scheduled, overflow = self._select_revisions_for_day(day_revisions, daily_limit)

            cursor = datetime.combine(current_day, preferred_time)

            for revision in scheduled:
                duration = self._task_duration_minutes(revision.topic)
                revision.due_at = cursor
                cursor += timedelta(minutes=duration + BUFFER_MINUTES)

            if overflow:
                next_day = current_day + timedelta(days=1)
                for revision in overflow:
                    revision.due_at = datetime.combine(next_day, preferred_time)
                grouped.setdefault(next_day, []).extend(overflow)

            if grouped:
                current_day = min(grouped)

        self.session.flush()

    def _select_revisions_for_day(
        self,
        day_revisions: list[Revision],
        daily_limit: int,
    ) -> tuple[list[Revision], list[Revision]]:
        ordered = sorted(day_revisions, key=self._revision_sort_key)
        if not ordered:
            return [], []

        candidate_subjects = self._candidate_subjects_for_day(ordered)
        selected = [revision for revision in ordered if self._is_manual_pin(revision)]
        selected_ids = {revision.id for revision in selected}
        used_minutes = sum(self._task_duration_minutes(revision.topic) for revision in selected)

        if len(candidate_subjects) <= 1:
            for revision in ordered:
                if revision.id in selected_ids:
                    continue
                duration = self._task_duration_minutes(revision.topic)
                if selected and used_minutes + duration > daily_limit:
                    break
                selected.append(revision)
                selected_ids.add(revision.id)
                used_minutes += duration
            if not selected:
                return [ordered[0]], ordered[1:]
            overflow = [revision for revision in ordered if revision.id not in selected_ids]
            return selected, overflow

        queues: dict[str, list[Revision]] = {
            subject: [
                revision
                for revision in ordered
                if revision.topic.subject.name == subject and revision.id not in selected_ids
            ]
            for subject in candidate_subjects
        }
        subject_counts = {subject: 0 for subject in candidate_subjects}
        for revision in selected:
            subject = revision.topic.subject.name
            if subject in subject_counts:
                subject_counts[subject] += 1

        while True:
            added = False
            for subject in candidate_subjects:
                queue = queues[subject]
                if not queue:
                    continue

                revision = queue[0]
                duration = self._task_duration_minutes(revision.topic)
                if used_minutes + duration > daily_limit:
                    continue

                proposed_counts = dict(subject_counts)
                proposed_counts[subject] += 1
                if max(proposed_counts.values()) - min(proposed_counts.values()) > 1:
                    continue

                queue.pop(0)
                selected.append(revision)
                selected_ids.add(revision.id)
                subject_counts[subject] += 1
                used_minutes += duration
                added = True

            if not added:
                break

        if not selected:
            return [ordered[0]], ordered[1:]
        overflow = [revision for revision in ordered if revision.id not in selected_ids]
        return selected, overflow

    def _candidate_subjects_for_day(self, ordered: list[Revision]) -> list[str]:
        subjects: list[str] = []
        seen: set[str] = set()

        for revision in ordered:
            subject = revision.topic.subject.name
            if subject in seen:
                continue
            seen.add(subject)
            subjects.append(subject)
            if len(subjects) == 3:
                break

        return subjects

    def _revision_sort_key(self, revision: Revision) -> tuple[date, datetime, int]:
        created_at = revision.created_at or revision.due_at
        return (revision.due_at.date(), created_at, revision.id)

    def _is_manual_pin(self, revision: Revision) -> bool:
        return "manual_pin" in str(revision.notes or "")

    def get_due_today(self, *, for_date: date | None = None) -> list[Revision]:
        return self.get_tasks_for_date(for_date or self._today())

    def get_overdue(self, *, for_date: date | None = None) -> list[Revision]:
        current_date = for_date or self._today()
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.status == "open", func.date(Revision.due_at) < current_date.isoformat())
            .order_by(Revision.due_at, Revision.created_at, Revision.id)
        )
        return list(self.session.scalars(stmt))

    def get_upcoming(self, *, from_date: date | None = None) -> list[Revision]:
        current_date = from_date or self._today()
        self.rebalance_schedule(start_date=current_date)
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.status == "open", func.date(Revision.due_at) > current_date.isoformat())
            .order_by(Revision.due_at, Revision.created_at, Revision.id)
        )
        return list(self.session.scalars(stmt))

    def _task_duration_minutes(self, topic: Topic) -> int:
        if topic.estimated_minutes is not None:
            return max(int(topic.estimated_minutes), 1)
        return DURATION_BY_DIFFICULTY.get(self._difficulty_key(topic), 30)

    def _preferred_time(self) -> time:
        raw = self._setting_value("preferred_time", DEFAULT_PREFERRED_TIME)
        try:
            return time.fromisoformat(raw)
        except ValueError:
            return time.fromisoformat(DEFAULT_PREFERRED_TIME)

    def _daily_time_minutes(self) -> int:
        raw = self._setting_value("daily_time_minutes", str(DEFAULT_DAILY_TIME_MINUTES))
        try:
            return max(15, int(raw))
        except ValueError:
            return DEFAULT_DAILY_TIME_MINUTES

    def _setting_value(self, key: str, default: str) -> str:
        setting = self.session.get(AppSetting, key)
        if setting is None:
            setting = AppSetting(key=key, value=default)
            self.session.add(setting)
            self.session.flush()
            return default
        if setting.value in (None, ""):
            setting.value = default
            self.session.flush()
            return default
        return str(setting.value)

    def _difficulty_key(self, topic: Topic) -> str:
        difficulty = topic.difficulty.value if hasattr(topic.difficulty, "value") else topic.difficulty
        return str(difficulty or "medium").lower()

    def _next_mastery_score(self, current_score: float | None, rating: ConfidenceRating, overdue_days: int) -> float:
        score = float(current_score or 0.0) + RATING_TO_MASTERY_DELTA[rating] - overdue_days * 1.5
        return round(max(0.0, min(100.0, score)), 1)

    def _active_revision_for_topic(self, topic_id: int | str) -> Revision | None:
        stmt = (
            select(Revision)
            .options(joinedload(Revision.topic).joinedload(Topic.subject))
            .where(Revision.topic_id == int(topic_id), Revision.status == "open")
            .order_by(Revision.due_at, Revision.created_at, Revision.id)
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
