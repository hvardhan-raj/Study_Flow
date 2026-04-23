from datetime import datetime, timedelta

from services import SyncConfig, SyncService


def test_sync_status_reports_offline_and_pending_changes() -> None:
    service = SyncService(SyncConfig(enabled=False, device_id="device-a"))
    state = {"topics": [{"id": "topic-1", "sync_status": "pending"}], "tasks": [], "notifications": []}

    status = service.status(state)

    assert status["enabled"] is False
    assert status["pendingChanges"] == 1
    assert status["label"] == "Offline only"


def test_sync_requires_configuration_before_cloud_push() -> None:
    service = SyncService(SyncConfig(enabled=True, device_id="device-a"))

    result = service.sync({"topics": [], "tasks": [], "notifications": []})

    assert result.status == "local_only"
    assert "Supabase" in result.message


def test_sync_marks_pending_local_items_synced_when_configured() -> None:
    service = SyncService(
        SyncConfig(enabled=True, supabase_url="https://example.supabase.co", supabase_anon_key="anon", device_id="device-a")
    )
    state = {
        "topics": [{"id": "topic-1", "name": "Biology", "sync_status": "pending", "updated_at": datetime.now().isoformat()}],
        "tasks": [],
        "notifications": [],
    }

    result = service.sync(state)

    assert result.status == "synced"
    assert result.pushed == 1
    assert state["topics"][0]["sync_status"] == "synced"


def test_sync_uses_remote_newer_record_for_last_write_wins() -> None:
    now = datetime.now()
    service = SyncService(
        SyncConfig(enabled=True, supabase_url="https://example.supabase.co", supabase_anon_key="anon", device_id="device-a")
    )
    state = {
        "topics": [{"id": "topic-1", "name": "Old", "sync_status": "pending", "updated_at": now.isoformat()}],
        "tasks": [],
        "notifications": [],
    }
    remote = {
        "topics": [{"id": "topic-1", "name": "New", "sync_status": "synced", "updated_at": (now + timedelta(minutes=5)).isoformat()}]
    }

    result = service.sync(state, remote)

    assert result.pulled == 1
    assert state["topics"][0]["name"] == "New"
