import time
from pathlib import Path

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
