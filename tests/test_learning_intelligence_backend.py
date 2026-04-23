from pathlib import Path

from studyflow_backend.service import StudyFlowBackend


def test_learning_intelligence_stats_match_card_contract(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")

    stats = backend.intelligenceStats

    assert len(stats) == 4
    assert all({"title", "value", "subtitle", "trend", "trendUp", "accentColor", "valueColor"} <= set(item) for item in stats)


def test_learning_intelligence_chart_and_subject_data_are_available(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")

    assert len(backend.studyTrend) == 14
    assert len(backend.studyTrendLabels) == 14
    assert len(backend.activityHeatmap) == 56
    assert len(backend.subjectConfidence) >= 1
    assert all({"subject", "pct", "progress", "topicCount", "color"} <= set(row) for row in backend.subjectConfidence)
    assert all({"risk", "nextAction"} <= set(row) for row in backend.analyticsSubjectRows)


def test_learning_report_export_writes_report_and_notification(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "analytics_state.json")
    before_notifications = len(backend.notifications)

    report_path = Path(backend.exportLearningReport())

    assert report_path.exists()
    assert "StudyFlow Learning Report" in report_path.read_text(encoding="utf-8")
    assert len(backend.notifications) == before_notifications + 1
