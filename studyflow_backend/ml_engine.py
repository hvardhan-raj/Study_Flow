from __future__ import annotations

import logging
import pickle
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from models import PerformanceLog, Revision, Topic

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier
except Exception:  # pragma: no cover - optional dependency fallback
    RandomForestClassifier = None


RATING_TO_CLASS = {
    "again": 3,
    "hard": 2,
    "good": 1,
    "easy": 0,
}
RATING_TO_RISK = {
    "again": 1.0,
    "hard": 0.7,
    "good": 0.3,
    "easy": 0.0,
}
CLASS_TO_RISK = {
    3: 1.0,
    2: 0.7,
    1: 0.3,
    0: 0.0,
}
DIFFICULTY_ENCODING = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
}
DEFAULT_ESTIMATED_MINUTES = {
    "easy": 15,
    "medium": 30,
    "hard": 45,
}


@dataclass(frozen=True)
class TopicFeatures:
    topic_id: int
    topic_name: str
    subject_name: str
    days_since_last_review: float
    interval_days: float
    previous_interval_days: float
    overdue_days: float
    difficulty_encoded: float
    review_count: float
    average_past_rating: float
    success_rate: float
    estimated_minutes: float
    stability: float

    def as_vector(self) -> list[float]:
        return [
            float(self.days_since_last_review),
            float(self.interval_days),
            float(self.previous_interval_days),
            float(self.overdue_days),
            float(self.difficulty_encoded),
            float(self.review_count),
            float(self.average_past_rating),
            float(self.success_rate),
            float(self.estimated_minutes),
        ]


class CacheManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._payload: dict[str, Any] = {
            "model_ready": False,
            "engine_mode": "heuristic",
            "last_updated": "",
            "retention_score": 0.0,
            "high_risk_topics": [],
            "recommended_topics": [],
            "weak_topics": [],
            "topic_predictions": {},
        }

    def update(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._payload = payload

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._payload)


class LearningMLEngine:
    def __init__(
        self,
        *,
        session_factory: sessionmaker,
        today_provider: Callable[[], date],
        model_path: Path,
        on_update: Callable[[], None] | None = None,
        retrain_threshold: int = 20,
        refresh_interval_seconds: int = 120,
    ) -> None:
        self._session_factory = session_factory
        self._today_provider = today_provider
        self._model_path = model_path
        self._on_update = on_update
        self._retrain_threshold = retrain_threshold
        self._refresh_interval_seconds = max(120, refresh_interval_seconds)
        self._cache = CacheManager()
        self._model: Any | None = None
        self._model_ready = False
        self._pending_completed_revisions = 0
        self._train_requested = True
        self._refresh_requested = True
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._load_model()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, name="learning-ml-engine", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def request_refresh(self, *, train: bool = False) -> None:
        if train:
            self._train_requested = True
        self._refresh_requested = True
        self._wake_event.set()

    def mark_revision_completed(self) -> None:
        self._pending_completed_revisions += 1
        self._refresh_requested = True
        if self._pending_completed_revisions >= self._retrain_threshold:
            self._train_requested = True
            self._pending_completed_revisions = 0
        self._wake_event.set()

    def get_intelligence_dashboard(self) -> dict[str, Any]:
        return self._cache.snapshot()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._train_requested or not self._model_ready:
                    self.train_model()
                if self._refresh_requested or not self.get_intelligence_dashboard()["last_updated"]:
                    self.compute_all_topic_predictions()
            except Exception:
                logger.exception("Background learning intelligence refresh failed")
            self._train_requested = False
            self._refresh_requested = False
            self._wake_event.wait(self._refresh_interval_seconds)
            self._wake_event.clear()

    def _notify(self) -> None:
        if self._on_update is None:
            return
        try:
            self._on_update()
        except Exception:
            logger.exception("Failed to notify intelligence update")

    def _load_model(self) -> None:
        if not self._model_path.exists():
            return
        try:
            self._model = pickle.loads(self._model_path.read_bytes())
            self._model_ready = self._model is not None
        except Exception:
            logger.exception("Failed to load learning model from %s", self._model_path)
            self._model = None
            self._model_ready = False

    def train_model(self) -> bool:
        rows, targets = self._build_training_dataset()
        if RandomForestClassifier is None:
            logger.warning("scikit-learn unavailable; learning intelligence will use heuristic mode")
            self._model = None
            self._model_ready = False
            return False
        if len(rows) < 4 or len(set(targets)) < 2:
            logger.info("Not enough revision history to train learning model")
            self._model = None
            self._model_ready = False
            return False

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
        )
        model.fit(rows, targets)
        self._model = model
        self._model_ready = True
        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        self._model_path.write_bytes(pickle.dumps(model))
        return True

    def compute_all_topic_predictions(self) -> dict[str, Any]:
        features = self._build_topic_feature_rows()
        topic_predictions: dict[int, dict[str, Any]] = {}
        for feature in features:
            forgetting_risk = self._predict_forgetting_risk(feature)
            retention_score = round(max(0.0, min(1.0, 1.0 - forgetting_risk)) * 100.0, 1)
            priority_score = round(
                feature.overdue_days + feature.difficulty_encoded,
                3,
            ) if not self._model_ready else round(
                (forgetting_risk * 0.6)
                + (feature.difficulty_encoded * 0.2)
                + (feature.overdue_days * 0.2),
                3,
            )
            topic_predictions[feature.topic_id] = {
                "topic_id": feature.topic_id,
                "topic": feature.topic_name,
                "subject": feature.subject_name,
                "forgetting_risk": round(forgetting_risk, 3),
                "retention_score": retention_score,
                "priority_score": priority_score,
                "overdue_days": round(feature.overdue_days, 2),
                "difficulty": int(feature.difficulty_encoded),
                "stability": round(feature.stability, 2),
                "engine_mode": "ml" if self._model_ready else "heuristic",
            }

        ordered_by_risk = sorted(
            topic_predictions.values(),
            key=lambda row: (-row["forgetting_risk"], -row["priority_score"], row["topic"].lower()),
        )
        ordered_by_priority = sorted(
            topic_predictions.values(),
            key=lambda row: (-row["priority_score"], -row["forgetting_risk"], row["topic"].lower()),
        )
        ordered_by_weakness = sorted(
            topic_predictions.values(),
            key=lambda row: (row["stability"], row["retention_score"], -row["forgetting_risk"], row["topic"].lower()),
        )
        retention_score = round(
            sum(row["retention_score"] for row in topic_predictions.values()) / len(topic_predictions),
            1,
        ) if topic_predictions else 0.0

        dashboard = {
            "model_ready": self._model_ready,
            "engine_mode": "ml" if self._model_ready else "heuristic",
            "last_updated": datetime.now().isoformat(timespec="seconds"),
            "retention_score": retention_score,
            "high_risk_topics": ordered_by_risk[:5],
            "recommended_topics": ordered_by_priority[:5],
            "weak_topics": ordered_by_weakness[:5],
            "topic_predictions": topic_predictions,
        }
        self._cache.update(dashboard)
        self._notify()
        return dashboard

    def _predict_forgetting_risk(self, feature: TopicFeatures) -> float:
        if self._model is not None and hasattr(self._model, "predict_proba"):
            probabilities = self._model.predict_proba([feature.as_vector()])[0]
            classes = getattr(self._model, "classes_", [])
            expected_target = sum(
                CLASS_TO_RISK.get(int(label), 0.5) * float(probability)
                for label, probability in zip(classes, probabilities)
            )
            return max(0.0, min(1.0, float(expected_target)))
        return self._heuristic_forgetting_risk(feature)

    def _heuristic_forgetting_risk(self, feature: TopicFeatures) -> float:
        days_component = min(feature.days_since_last_review / max(feature.interval_days, 1.0), 2.0) * 0.35
        overdue_component = min(feature.overdue_days / 7.0, 1.0) * 0.25
        difficulty_component = (feature.difficulty_encoded / 3.0) * 0.15
        history_component = max(0.0, 1.0 - feature.success_rate) * 0.15
        rating_component = min(feature.average_past_rating, 1.0) * 0.10
        return round(max(0.0, min(1.0, days_component + overdue_component + difficulty_component + history_component + rating_component)), 3)

    def _build_training_dataset(self) -> tuple[list[list[float]], list[int]]:
        rows: list[list[float]] = []
        targets: list[int] = []
        with self._session_factory() as session:
            completed_revisions = list(
                session.scalars(
                    select(Revision)
                    .options(joinedload(Revision.topic).joinedload(Topic.subject))
                    .where(Revision.status == "completed", Revision.rating.is_not(None))
                    .order_by(Revision.topic_id, Revision.completed_at, Revision.id)
                )
            )
            logs_by_topic = self._logs_by_topic(session)

        revision_history: dict[int, list[Revision]] = defaultdict(list)
        for revision in completed_revisions:
            topic = revision.topic
            topic_id = int(topic.id)
            prior_revisions = revision_history[topic_id]
            past_targets = [RATING_TO_RISK.get(str(item.rating or "").lower(), 0.5) for item in prior_revisions if item.rating]
            past_logs = [
                log for log in logs_by_topic.get(topic_id, [])
                if log.logged_at is not None and revision.completed_at is not None and log.logged_at < revision.completed_at
            ]
            average_past_rating = sum(past_targets) / len(past_targets) if past_targets else 0.5
            success_rate = (
                sum(1 for log in past_logs if str(log.outcome or "").lower() in {"good", "easy"}) / len(past_logs)
                if past_logs else 0.0
            )
            previous_review = prior_revisions[-1] if prior_revisions else None
            days_since_last_review = (
                max((revision.completed_at.date() - previous_review.completed_at.date()).days, 0)
                if previous_review is not None and previous_review.completed_at is not None and revision.completed_at is not None
                else 0.0
            )
            difficulty_key = str(topic.difficulty or "medium").lower()
            features = TopicFeatures(
                topic_id=int(topic.id),
                topic_name=topic.name,
                subject_name=topic.subject.name,
                days_since_last_review=float(days_since_last_review),
                interval_days=float(revision.interval_days or 0.0),
                previous_interval_days=float(revision.previous_interval_days or 0.0),
                overdue_days=float(revision.overdue_days or 0.0),
                difficulty_encoded=float(DIFFICULTY_ENCODING.get(difficulty_key, 2)),
                review_count=float(len(prior_revisions)),
                average_past_rating=float(average_past_rating),
                success_rate=float(success_rate),
                estimated_minutes=float(topic.estimated_minutes or DEFAULT_ESTIMATED_MINUTES.get(difficulty_key, 30)),
                stability=float(revision.stability or 0.0),
            )
            target = RATING_TO_CLASS.get(str(revision.rating or "").lower())
            if target is not None:
                rows.append(features.as_vector())
                targets.append(target)
            revision_history[topic_id].append(revision)
        return rows, targets

    def _build_topic_feature_rows(self) -> list[TopicFeatures]:
        with self._session_factory() as session:
            topics = list(
                session.execute(
                    select(Topic)
                    .options(
                        joinedload(Topic.subject),
                        joinedload(Topic.revisions),
                        joinedload(Topic.performance_logs),
                    )
                    .where(Topic.status != "archived")
                    .order_by(Topic.name)
                ).unique().scalars()
            )

        current_day = self._today_provider()
        rows: list[TopicFeatures] = []
        for topic in topics:
            difficulty_key = str(topic.difficulty or "medium").lower()
            open_revisions = [revision for revision in topic.revisions if revision.status == "open"]
            completed_revisions = [
                revision for revision in topic.revisions
                if revision.status == "completed" and revision.completed_at is not None
            ]
            open_revision = min(open_revisions, key=lambda item: (item.due_at, item.id)) if open_revisions else None
            latest_completed = max(completed_revisions, key=lambda item: (item.completed_at, item.id)) if completed_revisions else None
            logs = sorted(
                [log for log in topic.performance_logs if log.logged_at is not None],
                key=lambda item: (item.logged_at, item.id),
            )
            past_targets = [RATING_TO_RISK.get(str(log.outcome or "").lower(), 0.5) for log in logs if log.outcome]
            average_past_rating = sum(past_targets) / len(past_targets) if past_targets else 0.5
            success_rate = sum(1 for log in logs if str(log.outcome or "").lower() in {"good", "easy"}) / len(logs) if logs else 0.0
            last_reviewed_at = latest_completed.completed_at if latest_completed is not None else topic.last_reviewed_at
            days_since_last_review = (
                max((current_day - last_reviewed_at.date()).days, 0)
                if last_reviewed_at is not None else float(max(topic.review_count or 0, 1))
            )
            due_at = open_revision.due_at if open_revision is not None else None
            overdue_days = max((current_day - due_at.date()).days, 0) if due_at is not None else 0.0
            interval_days = (
                float(open_revision.interval_days)
                if open_revision is not None and open_revision.interval_days is not None
                else float(latest_completed.interval_days if latest_completed is not None and latest_completed.interval_days is not None else 0.0)
            )
            previous_interval_days = (
                float(open_revision.previous_interval_days)
                if open_revision is not None and open_revision.previous_interval_days is not None
                else float(latest_completed.previous_interval_days if latest_completed is not None and latest_completed.previous_interval_days is not None else 0.0)
            )
            stability = float(
                open_revision.stability
                if open_revision is not None and open_revision.stability is not None
                else latest_completed.stability if latest_completed is not None and latest_completed.stability is not None
                else 0.0
            )
            rows.append(
                TopicFeatures(
                    topic_id=int(topic.id),
                    topic_name=topic.name,
                    subject_name=topic.subject.name,
                    days_since_last_review=float(days_since_last_review),
                    interval_days=interval_days,
                    previous_interval_days=previous_interval_days,
                    overdue_days=float(overdue_days),
                    difficulty_encoded=float(DIFFICULTY_ENCODING.get(difficulty_key, 2)),
                    review_count=float(topic.review_count or 0),
                    average_past_rating=float(average_past_rating),
                    success_rate=float(success_rate),
                    estimated_minutes=float(topic.estimated_minutes or DEFAULT_ESTIMATED_MINUTES.get(difficulty_key, 30)),
                    stability=stability,
                )
            )
        return rows

    def _logs_by_topic(self, session: Session) -> dict[int, list[PerformanceLog]]:
        logs = list(session.scalars(select(PerformanceLog).order_by(PerformanceLog.topic_id, PerformanceLog.logged_at, PerformanceLog.id)))
        grouped: dict[int, list[PerformanceLog]] = defaultdict(list)
        for log in logs:
            grouped[int(log.topic_id)].append(log)
        return grouped
