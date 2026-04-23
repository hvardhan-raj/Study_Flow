from studyflow_backend.service import StudyFlowBackend


def test_selected_day_sessions_include_rich_schedule_fields(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "revision_state.json")
    backend.selectToday()

    sessions = backend.selectedDaySessions

    assert sessions
    first = sessions[0]
    assert {"id", "topic", "name", "subject", "duration", "time", "durationText", "color", "status", "completed"} <= set(first)


def test_revision_week_summary_matches_week_rows(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "revision_state.json")

    week_rows = backend.weekCompletion
    summary = backend.revisionWeekSummary

    assert len(week_rows) == 7
    assert summary["completed"] == sum(row["completed"] for row in week_rows)
    assert summary["scheduled"] == sum(row["scheduled"] for row in week_rows)
    assert summary["remaining"] == sum(row["remaining"] for row in week_rows)
    assert 0 <= summary["score"] <= 100


def test_selected_day_total_text_sums_session_minutes(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "revision_state.json")
    backend.selectToday()

    total_minutes = sum(session["duration"] for session in backend.selectedDaySessions)

    assert backend.selectedDayTotalText == f"{total_minutes} min"
