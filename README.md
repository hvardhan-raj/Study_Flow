# Smart Study Schedule System

Smart Study Schedule System is an offline-first desktop study planner built with `PySide6`, `QML`, and a local Python backend. It combines revision scheduling, topic management, analytics, reminders, an optional local AI assistant, and a sync-ready architecture in a single desktop app.

## Features

- Revision dashboard with due, overdue, and upcoming work
- Subject and topic management with nested syllabus trees
- FSRS-style scheduling with a personalized forgetting-curve layer
- Learning analytics, notifications, reminders, and calendar export
- Local AI assistant with Ollama integration and offline fallback
- Offline-first sync foundation with optional cloud configuration

## Requirements

- Windows or Linux
- Python `3.13`
- A virtual environment is strongly recommended

## Quick Start

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Development Checks

```powershell
.\.venv\Scripts\ruff check .
.\.venv\Scripts\python -m pytest
```

For a headless startup smoke test:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m scripts.profile_startup --smoke-only
```

## Build A Windows Executable

The project includes a PyInstaller spec and a helper script for repeatable release builds.

```powershell
.\scripts\build_release.ps1
```

The build script runs linting, tests, and an offscreen startup smoke test before packaging. Output is written to `dist\SmartStudyScheduleSystem\`.

## Data And Logs

- App state is stored in the user-writable application data directory as `studyflow_data.json`
- SQL/database artifacts are written under the configured `data/` directory
- Logs are written to `logs/app.log`

You can override the JSON state location with `STUDYFLOW_STORE_PATH`.

## Release Notes

The release checklist and packaging workflow live in [docs/RELEASE_CHECKLIST.md](/D:/Projects/Major_Project/Smart_Study_Schedule_System/docs/RELEASE_CHECKLIST.md).
