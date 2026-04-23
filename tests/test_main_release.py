from __future__ import annotations

from pathlib import Path

import main


def test_resolve_runtime_dir_uses_meipass_when_frozen(monkeypatch) -> None:
    monkeypatch.setattr(main.sys, "frozen", True, raising=False)
    monkeypatch.setattr(main.sys, "_MEIPASS", str(Path("C:/bundle")), raising=False)

    assert main.resolve_runtime_dir() == Path("C:/bundle")


def test_resolve_store_path_prefers_env_override(monkeypatch, tmp_path) -> None:
    override_path = tmp_path / "custom-store.json"
    monkeypatch.setenv("STUDYFLOW_STORE_PATH", str(override_path))

    resolved = main.resolve_store_path(tmp_path)

    assert resolved == override_path


def test_resolve_store_path_uses_appdata_location(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("STUDYFLOW_STORE_PATH", raising=False)
    monkeypatch.setattr(main.QStandardPaths, "writableLocation", lambda *_args: str(tmp_path))

    resolved = main.resolve_store_path(Path("C:/runtime"))

    assert resolved == tmp_path / "studyflow_data.json"
