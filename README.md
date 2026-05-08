# StudyFlow

StudyFlow is an offline-first desktop study planner built with `PySide6`, `QML`, and a local Python backend. It combines revision scheduling, topic management, learning analytics, reminders, and an optional local AI assistant in a single desktop app.

## What It Does

- Plans due, overdue, and upcoming revision work
- Organizes subjects and topics with nested curriculum support
- Tracks confidence, progress, and study history
- Surfaces learning intelligence signals such as weak topics and retention risk
- Sends reminders and exports revision sessions to calendar format
- Offers a local AI assistant with Ollama support and offline fallback guidance

## Tech Stack

- UI: `PySide6`, `Qt Quick / QML`
- Backend: Python `3.13`
- Storage: local JSON state plus SQLite-backed application data
- Tooling: `pytest`, `ruff`, `PyInstaller`

## Requirements

- Windows or Linux
- Python `3.13`
- A virtual environment is recommended

For Linux desktop or CI environments, Qt may require system packages such as `libegl1` and `libglib2.0-0`.

## Quick Start

### Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

### Linux

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Local AI Assistant

The AI assistant works without cloud dependencies. If Ollama is available locally, StudyFlow can use it for richer responses; otherwise it falls back to offline guidance.

Default Ollama settings:

- Base URL: `http://localhost:11434`
- Preferred model env var: `STUDYFLOW_OLLAMA_MODEL`
- Base URL env var: `STUDYFLOW_OLLAMA_BASE_URL`

Example setup:

```powershell
ollama pull llama3.2:3b
ollama serve
```

If the configured model is not installed but Ollama is running with another local model, StudyFlow will fall back to an available installed model.

## Development

### Run Checks

```powershell
.\.venv\Scripts\ruff check .
.\.venv\Scripts\python -m pytest
```

### QML Startup Smoke Test

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m scripts.profile_startup --smoke-only
```

### CI Notes

Linux CI runners need Qt runtime packages before test execution. The workflow in [.github/workflows/ci.yml](/D:/Projects/Major_Project/4S/Study_Flow/.github/workflows/ci.yml) installs the required dependencies before Python packages.

## Build A Windows Executable

The repository includes a PyInstaller spec and a helper script:

```powershell
.\scripts\build_release.ps1
```

The release build runs linting, tests, and an offscreen startup smoke test before packaging. Output is written under `dist\SmartStudyScheduleSystem\`.

## Project Structure

Key directories and files:

- [main.py](/D:/Projects/Major_Project/4S/Study_Flow/main.py): application entry point
- [studyflow_backend](/D:/Projects/Major_Project/4S/Study_Flow/studyflow_backend): backend services, projections, storage, analytics
- [services](/D:/Projects/Major_Project/4S/Study_Flow/services): reminders, scheduling, topic management
- [llm](/D:/Projects/Major_Project/4S/Study_Flow/llm): local AI assistant integration
- [ui](/D:/Projects/Major_Project/4S/Study_Flow/ui): navigation and UI-side helpers
- [tests](/D:/Projects/Major_Project/4S/Study_Flow/tests): automated test suite
- [scripts](/D:/Projects/Major_Project/4S/Study_Flow/scripts): development and release helpers
- QML screens in the repo root such as [DashboardScreen.qml](/D:/Projects/Major_Project/4S/Study_Flow/DashboardScreen.qml), [LearningIntelligenceScreen.qml](/D:/Projects/Major_Project/4S/Study_Flow/LearningIntelligenceScreen.qml), and [AIAssistantScreen.qml](/D:/Projects/Major_Project/4S/Study_Flow/AIAssistantScreen.qml)

## Data, Models, And Logs

- App state is stored as `studyflow_data.json` in the user-writable application data directory by default
- SQLite data is stored under `data/`
- Trained analytics models are stored under `models/`
- Logs are written to `logs/app.log`

You can override the JSON state location with:

- `STUDYFLOW_STORE_PATH`

## Release And Packaging

Release notes and packaging guidance live in [docs/RELEASE_CHECKLIST.md](/D:/Projects/Major_Project/4S/Study_Flow/docs/RELEASE_CHECKLIST.md).
