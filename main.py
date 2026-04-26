from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine

from backend import StudyFlowBackend
from config.logging import configure_logging
from config.settings import settings
from services import ReminderScheduler
from ui import NavigationController


def resolve_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def resolve_store_path(runtime_dir: Path) -> Path:
    override = os.getenv("STUDYFLOW_STORE_PATH")
    if override:
        return Path(override)

    app_data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if app_data_dir:
        return Path(app_data_dir) / "studyflow_data.json"
    return runtime_dir / "studyflow_data.json"


def main() -> int:
    logger = configure_logging()
    settings.ensure_directories()

    # Use a non-native controls style so the app's custom QML backgrounds are supported.
    QQuickStyle.setStyle("Fusion")
    QGuiApplication.setOrganizationName("SmartStudy")
    QGuiApplication.setApplicationName(settings.app_name)
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    runtime_dir = resolve_runtime_dir()
    store_path = resolve_store_path(runtime_dir)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    backend = StudyFlowBackend(store_path)
    navigation = NavigationController()
    reminder_scheduler = ReminderScheduler(preferences_provider=backend._reminder_preferences_model)
    reminder_scheduler.jobRequested.connect(backend.runReminderCheck, Qt.ConnectionType.QueuedConnection)
    reminder_scheduler.start()
    app.aboutToQuit.connect(reminder_scheduler.stop)
    app.aboutToQuit.connect(backend.shutdown)
    # Keep Python-owned QObjects strongly referenced for the full Qt app lifetime.
    app._backend = backend
    app._navigation = navigation
    app._reminder_scheduler = reminder_scheduler
    engine._backend = backend
    engine._navigation = navigation
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("navigation", navigation)
    engine.addImportPath(str(runtime_dir))
    engine.load(str(runtime_dir / "Main.qml"))
    logger.info("Application startup completed")

    if not engine.rootObjects():
        logger.error("No QML root objects were loaded")
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
