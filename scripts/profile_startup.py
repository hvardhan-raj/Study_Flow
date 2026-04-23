from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from backend import StudyFlowBackend
from main import resolve_runtime_dir
from ui import NavigationController


def run_smoke_test() -> tuple[bool, float, float]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    temp_dir = Path(tempfile.mkdtemp(prefix="studyflow-smoke-"))
    store_path = temp_dir / "studyflow_data.json"
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()

    backend_start = time.perf_counter()
    backend = StudyFlowBackend(store_path)
    navigation = NavigationController()
    backend_seconds = time.perf_counter() - backend_start

    qml_start = time.perf_counter()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("navigation", navigation)
    runtime_dir = resolve_runtime_dir()
    engine.addImportPath(str(runtime_dir))
    engine.load(str(runtime_dir / "Main.qml"))
    qml_seconds = time.perf_counter() - qml_start

    ok = bool(engine.rootObjects())
    app.quit()
    return ok, backend_seconds, qml_seconds


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile or smoke-test desktop startup.")
    parser.add_argument("--smoke-only", action="store_true", help="Print pass/fail only.")
    args = parser.parse_args()

    ok, backend_seconds, qml_seconds = run_smoke_test()
    if args.smoke_only:
        print("QML_OK" if ok else "QML_FAIL")
    else:
        print(f"backend_init_seconds={backend_seconds:.4f}")
        print(f"qml_load_seconds={qml_seconds:.4f}")
        print("QML_OK" if ok else "QML_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
