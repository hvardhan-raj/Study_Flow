import time
from pathlib import Path

from models import ConfidenceRating, Revision, Topic
from studyflow_backend.ml_engine import TopicFeatures
from studyflow_backend.service_db import StudyFlowBackend


def _wait_for_dashboard(backend: StudyFlowBackend, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        dashboard = backend.getIntelligenceDashboard()
        if dashboard.get("last_updated"):
            return dashboard
        time.sleep(0.05)
    return backend.getIntelligenceDashboard()


def test_learning_intelligence_dashboard_uses_cached_snapshot(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")
    try:
        dashboard = _wait_for_dashboard(backend)

        assert {"model_ready", "engine_mode", "last_updated", "retention_score", "high_risk_topics", "recommended_topics", "weak_topics", "topic_predictions"} <= set(dashboard)
        assert isinstance(dashboard["high_risk_topics"], list)
        assert isinstance(dashboard["recommended_topics"], list)
        assert isinstance(dashboard["weak_topics"], list)
    finally:
        backend.shutdown()


def test_completed_revisions_trigger_cached_prediction_refresh(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")
    try:
        first_snapshot = _wait_for_dashboard(backend)
        target_task = next(task for task in backend._tasks if not backend._is_task_completed(task))

        backend.completeRevision(target_task["id"], 4)
        refreshed = _wait_for_dashboard(backend)

        assert refreshed["last_updated"]
        assert refreshed["last_updated"] >= first_snapshot["last_updated"]
    finally:
        backend.shutdown()


def test_learning_report_export_writes_report_and_notification(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")
    try:
        before_notifications = len(backend.notifications)
        report_path = Path(backend.exportLearningReport())

        assert report_path.exists()
        assert "StudyFlow Learning Report" in report_path.read_text(encoding="utf-8")
        assert len(backend.notifications) == before_notifications + 1
    finally:
        backend.shutdown()


def test_topic_features_vector_includes_stability() -> None:
    features = TopicFeatures(
        topic_id=1,
        topic_name="Calculus",
        subject_name="Mathematics",
        days_since_last_review=2.0,
        interval_days=3.0,
        previous_interval_days=1.0,
        overdue_days=0.0,
        difficulty_encoded=2.0,
        review_count=4.0,
        average_past_rating=0.5,
        success_rate=0.75,
        estimated_minutes=30.0,
        stability=5.0,
    )

    vector = features.as_vector()

    assert len(vector) == 10
    assert vector[-1] == 5.0


def test_complete_revision_updates_mastery_once(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")
    try:
        with backend._db() as db:
            revision = db.query(Revision).filter(Revision.status == "open").order_by(Revision.id).first()
            assert revision is not None
            topic = db.get(Topic, revision.topic_id)
            assert topic is not None
            before_score = float(topic.mastery_score or 0.0)
            due_at = revision.due_at
            expected_score = backend._scheduler(db)._next_mastery_score(before_score, ConfidenceRating.EASY, 0)

        backend.completeRevision(str(revision.id), 4)

        with backend._db() as db:
            updated_topic = db.get(Topic, revision.topic_id)
            assert updated_topic is not None
            assert updated_topic.mastery_score == expected_score
            completed_revision = db.get(Revision, revision.id)
            assert completed_revision is not None
            assert completed_revision.completed_at is not None
            assert completed_revision.completed_at.date() >= due_at.date()
    finally:
        backend.shutdown()
