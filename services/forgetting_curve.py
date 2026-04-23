from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config.settings import settings
from models import PerformanceLog, Revision, Subject, Topic

MIN_RECORDS_TO_PERSONALIZE = 20
RETRAIN_EVERY_NEW_RECORDS = 10
K_NEAREST_EXAMPLES = 5
MAX_PERSONAL_INTERVAL_DAYS = 365


@dataclass(frozen=True)
class PersonalFeatures:
    days_since_review: int
    num_past_reviews: int
    avg_confidence: float
    topic_difficulty_score: float
    num_missed_revisions: int
    time_of_day: int


@dataclass(frozen=True)
class PersonalExample:
    features: PersonalFeatures
    target_recall: float
    fsrs_interval: int
    actual_interval: int


@dataclass
class PersonalModelArtifact:
    trained_on_records: int
    examples: list[PersonalExample]
    average_target_recall: float
    average_interval_ratio: float


class ForgettingCurveModel:
    def __init__(self, session: Session, model_dir: Path | None = None) -> None:
        self.session = session
        self.model_dir = model_dir or settings.local_model_path.parent

    def predict_interval(
        self,
        *,
        user_id: str,
        fsrs_interval: int,
        features: PersonalFeatures,
    ) -> int | None:
        artifact = self.load(user_id)
        if artifact is None:
            return None

        ranked_examples = sorted(
            artifact.examples,
            key=lambda example: self._distance(features, example.features),
        )[:K_NEAREST_EXAMPLES]
        if not ranked_examples:
            return None

        weighted_ratio_sum = 0.0
        weighted_recall_sum = 0.0
        total_weight = 0.0
        for example in ranked_examples:
            distance = self._distance(features, example.features)
            weight = 1 / (1 + distance)
            weighted_ratio_sum += weight * (example.actual_interval / max(example.fsrs_interval, 1))
            weighted_recall_sum += weight * example.target_recall
            total_weight += weight

        learned_ratio = weighted_ratio_sum / total_weight if total_weight else artifact.average_interval_ratio
        learned_recall = weighted_recall_sum / total_weight if total_weight else artifact.average_target_recall
        recall_multiplier = 0.85 + ((learned_recall - 1) / 3) * 0.45
        personalized_interval = max(
            1,
            min(MAX_PERSONAL_INTERVAL_DAYS, round(fsrs_interval * learned_ratio * recall_multiplier)),
        )
        return personalized_interval

    def train_if_needed(self, user_id: str) -> PersonalModelArtifact | None:
        record_count = self._performance_record_count(user_id)
        if record_count < MIN_RECORDS_TO_PERSONALIZE:
            return None

        existing = self.load(user_id)
        if existing is not None and record_count - existing.trained_on_records < RETRAIN_EVERY_NEW_RECORDS:
            return existing

        examples = self._build_examples(user_id)
        if len(examples) < MIN_RECORDS_TO_PERSONALIZE:
            return None

        artifact = PersonalModelArtifact(
            trained_on_records=record_count,
            examples=examples,
            average_target_recall=sum(example.target_recall for example in examples) / len(examples),
            average_interval_ratio=sum(example.actual_interval / max(example.fsrs_interval, 1) for example in examples)
            / len(examples),
        )
        self.save(user_id, artifact)
        return artifact

    def build_features_for_topic(
        self,
        *,
        topic: Topic,
        days_since_review: int,
        time_of_day: int,
    ) -> PersonalFeatures:
        avg_confidence = self._average_confidence_for_topic(topic.id)
        missed_count = self._missed_revision_count(topic.id)
        return PersonalFeatures(
            days_since_review=days_since_review,
            num_past_reviews=topic.fsrs_review_count,
            avg_confidence=avg_confidence,
            topic_difficulty_score=topic.difficulty_score,
            num_missed_revisions=missed_count,
            time_of_day=time_of_day,
        )

    def load(self, user_id: str) -> PersonalModelArtifact | None:
        model_path = self.model_dir / f"user_{user_id}.pkl"
        if not model_path.exists():
            return None
        with model_path.open("rb") as file_handle:
            return pickle.load(file_handle)

    def save(self, user_id: str, artifact: PersonalModelArtifact) -> Path:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.model_dir / f"user_{user_id}.pkl"
        with model_path.open("wb") as file_handle:
            pickle.dump(artifact, file_handle)
        return model_path

    def _build_examples(self, user_id: str) -> list[PersonalExample]:
        stmt = (
            select(PerformanceLog, Revision)
            .join(Revision, PerformanceLog.revision_id == Revision.id)
            .join(Topic, PerformanceLog.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.user_id == user_id, Revision.is_completed.is_(True), Revision.interval_days_after.is_not(None))
            .order_by(PerformanceLog.created_at)
        )
        rows = self.session.execute(stmt).all()
        examples: list[PersonalExample] = []
        for performance_log, revision in rows:
            actual_interval = revision.personalized_interval_days or revision.interval_days_after
            fsrs_interval = revision.fsrs_interval_days or revision.interval_days_after
            if actual_interval is None or fsrs_interval is None:
                continue
            examples.append(
                PersonalExample(
                    features=PersonalFeatures(
                        days_since_review=performance_log.days_since_last_review or 0,
                        num_past_reviews=performance_log.review_count_at_time,
                        avg_confidence=performance_log.predicted_confidence or 0.5,
                        topic_difficulty_score=performance_log.difficulty_score_at_time,
                        num_missed_revisions=max(performance_log.scheduled_days_overdue, 0),
                        time_of_day=performance_log.hour_of_day or 0,
                    ),
                    target_recall=float(performance_log.confidence_rating.value),
                    fsrs_interval=fsrs_interval,
                    actual_interval=actual_interval,
                )
            )
        return examples

    def _performance_record_count(self, user_id: str) -> int:
        stmt = (
            select(func.count(PerformanceLog.id))
            .join(Topic, PerformanceLog.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.user_id == user_id)
        )
        return int(self.session.scalar(stmt) or 0)

    def _average_confidence_for_topic(self, topic_id: str) -> float:
        stmt = select(PerformanceLog.confidence_rating).where(PerformanceLog.topic_id == topic_id)
        ratings = list(self.session.scalars(stmt))
        if not ratings:
            return 0.5
        numeric_scores = [float(rating.value) for rating in ratings]
        return min(max((sum(numeric_scores) / len(numeric_scores)) / 4, 0.25), 1.0)

    def _missed_revision_count(self, topic_id: str) -> int:
        stmt = select(func.count(Revision.id)).where(Revision.topic_id == topic_id, Revision.is_missed.is_(True))
        return int(self.session.scalar(stmt) or 0)

    def _distance(self, left: PersonalFeatures, right: PersonalFeatures) -> float:
        return (
            abs(left.days_since_review - right.days_since_review) / 14
            + abs(left.num_past_reviews - right.num_past_reviews) / 10
            + abs(left.avg_confidence - right.avg_confidence)
            + abs(left.topic_difficulty_score - right.topic_difficulty_score)
            + abs(left.num_missed_revisions - right.num_missed_revisions) / 5
            + abs(left.time_of_day - right.time_of_day) / 24
        )
