from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


def resolve_app_data_dir() -> Path:
    override = os.getenv("STUDYFLOW_APP_DATA_DIR")
    if override:
        return Path(override)
    try:
        from PySide6.QtCore import QCoreApplication, QStandardPaths

        if not QCoreApplication.applicationName():
            QCoreApplication.setApplicationName("SmartStudy")
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if location:
            return Path(location)
    except Exception:
        pass
    return BASE_DIR / "data"


APP_DATA_DIR = resolve_app_data_dir()
DATA_DIR = Path(os.getenv("STUDYFLOW_DATA_DIR", APP_DATA_DIR / "data"))
LOG_DIR = Path(os.getenv("STUDYFLOW_LOG_DIR", APP_DATA_DIR / "logs"))
MODELS_DIR = Path(os.getenv("STUDYFLOW_MODELS_DIR", APP_DATA_DIR / "models"))
SEED_MODELS_DIR = BASE_DIR / "models"


@dataclass(frozen=True)
class AppSettings:
    """Central application settings loaded from environment variables."""

    app_name: str = "Smart Study Schedule System"
    app_env: str = os.getenv("APP_ENV", "development")
    app_data_dir: Path = APP_DATA_DIR
    base_dir: Path = BASE_DIR
    seed_models_dir: Path = SEED_MODELS_DIR
    database_path: Path = Path(os.getenv("DATABASE_PATH", DATA_DIR / "smart_study.sqlite3"))
    sync_url: str = os.getenv("SYNC_URL", "")
    local_model_path: Path = Path(os.getenv("LOCAL_MODEL_PATH", MODELS_DIR / "difficulty"))
    learning_model_path: Path = Path(
        os.getenv("LEARNING_MODEL_PATH", MODELS_DIR / "learning_model.joblib")
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Path = Path(os.getenv("LOG_FILE", LOG_DIR / "app.log"))

    def ensure_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_model_path.mkdir(parents=True, exist_ok=True)
        self.local_model_path.parent.mkdir(parents=True, exist_ok=True)
        self.learning_model_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


settings = AppSettings()
