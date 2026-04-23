# Release Checklist

## Pre-release

1. Activate the project virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run `ruff check .`.
4. Run `python -m pytest`.
5. Run the offscreen startup smoke test: `python -m scripts.profile_startup --smoke-only`.
6. Review the latest QML warnings and confirm no new startup regressions were introduced.

## Build

1. Run `.\scripts\build_release.ps1`.
2. Confirm the packaged app is created under `dist\SmartStudyScheduleSystem\`.
3. Launch the packaged executable once on a clean machine or profile.
4. Confirm that `studyflow_data.json` is created in the user app-data directory instead of beside the executable.

## Manual Verification

1. Open the dashboard and confirm due, overdue, and upcoming tasks render.
2. Add and edit a topic from the topic manager.
3. Complete a revision from the dashboard.
4. Open analytics, notifications, settings, and AI assistant screens.
5. Export an `.ics` calendar file from notifications.
6. Confirm sync settings can be edited and saved.

## Release Artifacts

- `dist\SmartStudyScheduleSystem\SmartStudyScheduleSystem.exe`
- bundled QML and runtime assets
- source tag or release note summary

## Known Follow-up

- `RevisionScheduleScreen.qml` still emits existing undefined-string warnings during headless startup smoke tests. Treat new warnings as regressions, but this known warning does not currently block packaging.
