from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .defaults import build_default_notifications, default_alert_settings, default_settings, default_study_minutes

logger = logging.getLogger(__name__)


def merge_nested(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_nested(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_state(store_path: Path) -> dict[str, Any]:
    state = {
        "settings": default_settings(),
        "alert_settings": default_alert_settings(),
        "reminder_preferences": {
            "enabled": True,
            "notification_time": "08:00",
            "minimum_due_for_alert": 1,
            "desktop_notifications": False,
        },
        "assistant_messages": [],
        "suggestion_dismissed": False,
        "study_minutes": default_study_minutes(),
        "notifications": build_default_notifications(),
    }
    if not store_path.exists():
        return state

    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load persisted state from %s", store_path)
        return state
    if not isinstance(payload, dict):
        return state

    if isinstance(payload.get("settings"), dict):
        state["settings"] = merge_nested(state["settings"], payload["settings"])
    if isinstance(payload.get("alert_settings"), dict):
        state["alert_settings"].update(payload["alert_settings"])
    if isinstance(payload.get("reminder_preferences"), dict):
        state["reminder_preferences"].update(payload["reminder_preferences"])
    if isinstance(payload.get("assistant_messages"), list):
        state["assistant_messages"] = payload["assistant_messages"]
    state["suggestion_dismissed"] = bool(payload.get("suggestion_dismissed", False))
    if isinstance(payload.get("study_minutes"), list):
        state["study_minutes"] = payload["study_minutes"]
    if isinstance(payload.get("notifications"), list):
        state["notifications"] = [dict(notification) for notification in payload["notifications"] if isinstance(notification, dict)]
    return state


def save_state(store_path: Path, state: dict[str, Any]) -> None:
    payload = {
        "settings": state["settings"],
        "alert_settings": state["alert_settings"],
        "reminder_preferences": state["reminder_preferences"],
        "assistant_messages": state["assistant_messages"],
        "suggestion_dismissed": state["suggestion_dismissed"],
        "study_minutes": state["study_minutes"],
        "notifications": state["notifications"],
    }
    store_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = store_path.with_name(f"{store_path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(store_path)
