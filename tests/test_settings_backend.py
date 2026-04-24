from studyflow_backend.service import StudyFlowBackend


def test_schedule_settings_persist_in_app_settings(tmp_path) -> None:
    store_path = tmp_path / "settings_state.json"

    backend = StudyFlowBackend(store_path)
    assert backend.scheduleSettings["daily_time_minutes"] == 120
    assert backend.scheduleSettings["preferred_time"] == "18:00"

    backend.updateScheduleSetting("daily_time_minutes", "150")
    backend.updateScheduleSetting("preferred_time", "19:30")

    reloaded = StudyFlowBackend(store_path)
    assert reloaded.scheduleSettings["daily_time_minutes"] == 150
    assert reloaded.scheduleSettings["preferred_time"] == "19:30"
