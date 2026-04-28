from __future__ import annotations

import json
import logging
from datetime import timedelta

from studyflow_backend.service import StudyFlowBackend
from studyflow_backend.storage import load_state


def test_backend_logs_invalid_state_and_recovers(tmp_path, caplog) -> None:
    state_path = tmp_path / "broken_state.json"
    state_path.write_text(json.dumps({"notifications": 5}), encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        backend = StudyFlowBackend(state_path)

    assert backend.notifications


def test_load_state_handles_corrupt_json(tmp_path) -> None:
    state_path = tmp_path / "corrupt_state.json"
    state_path.write_text("{not-valid-json", encoding="utf-8")

    state = load_state(state_path)

    assert state["settings"]
    assert state["notifications"]


def test_backend_refreshes_today_after_midnight(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "rollover_state.json")
    previous_today = backend._today

    backend._selected_date = previous_today
    backend._calendar_view_date = previous_today
    backend._today_provider = lambda: previous_today + timedelta(days=1)

    assert backend._today == previous_today + timedelta(days=1)
    assert backend._selected_date == previous_today + timedelta(days=1)
    assert backend._calendar_view_date == previous_today + timedelta(days=1)
