from models import NlpFeedback, NotificationLog, PerformanceLog, UserBadge, UserPreference
from studyflow_backend.service import StudyFlowBackend


def test_remaining_orm_tables_have_sync_metadata() -> None:
    for model in (UserPreference, PerformanceLog, NlpFeedback, UserBadge, NotificationLog):
        assert "sync_status" in model.__table__.columns
        assert "device_id" in model.__table__.columns
        assert "last_synced_at" in model.__table__.columns


def test_backend_sync_status_and_settings_contract(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "sync_state.json")

    assert backend.syncStatus["label"] == "Offline only"
    assert backend.syncSettings["enabled"] is False
    assert backend.syncSettings["deviceId"].startswith("device-")


def test_backend_force_sync_records_local_only_history_without_credentials(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "sync_state.json")

    backend.toggleCloudSync()
    result = backend.forceFullSync()

    assert result["status"] == "local_only"
    assert backend.syncHistory[0]["status"] == "local_only"
    assert backend.syncStatus["configured"] is False


def test_backend_force_sync_marks_changes_synced_when_configured(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "sync_state.json")

    backend.toggleCloudSync()
    backend.updateSyncSetting("supabase_url", "https://example.supabase.co")
    backend.updateSyncSetting("supabase_anon_key", "anon")
    result = backend.forceFullSync()

    assert result["status"] == "synced"
    assert backend.syncStatus["pendingChanges"] == 0
    assert backend.syncSettings["anonKeyConfigured"] is True
