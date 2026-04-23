from __future__ import annotations

from dataclasses import dataclass
from typing import Any

NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True)
class SyncConfig:
    enabled: bool = False
    device_id: str = "desktop-offline"
    last_sync_at: str = ""


@dataclass(frozen=True)
class SyncResult:
    status: str
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0
    message: str = "Sync is not implemented for this offline desktop app."
    synced_at: str = ""


class SyncService:
    """Explicitly disabled for the offline desktop build."""

    def __init__(self, config: SyncConfig | None = None) -> None:
        if isinstance(config, SyncConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = SyncConfig(
                enabled=bool(config.get("enabled", False)),
                device_id=str(config.get("device_id", "desktop-offline")),
                last_sync_at=str(config.get("last_sync_at", "")),
            )
        else:
            self.config = SyncConfig()

    def status(self, _state: dict[str, Any]) -> dict[str, Any]:
        return {
            "enabled": False,
            "configured": False,
            "deviceId": self.config.device_id,
            "lastSyncAt": self.config.last_sync_at,
            "pendingChanges": 0,
            "label": "Not implemented",
            "color": "#64748B",
        }

    def count_pending_changes(self, _state: dict[str, Any]) -> int:
        return 0

    def iter_sync_items(self, _state: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def mark_pending(self, _item: dict[str, Any]) -> None:
        return

    def sync(self, _state: dict[str, Any], _remote_state: dict[str, Any] | None = None) -> SyncResult:
        return SyncResult(status=NOT_IMPLEMENTED)
