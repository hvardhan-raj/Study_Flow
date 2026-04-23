# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH)
qml_files = [
    "AIAssistantScreen.qml",
    "AppButton.qml",
    "CalendarScreen.qml",
    "CurriculumMapScreen.qml",
    "DashboardScreen.qml",
    "DashboardTaskCard.qml",
    "LearningIntelligenceScreen.qml",
    "Main.qml",
    "NotificationsScreen.qml",
    "PageHeader.qml",
    "qmldir",
    "RevisionScheduleScreen.qml",
    "SettingsRow.qml",
    "SettingsScreen.qml",
    "SettingsSection.qml",
    "Sidebar.qml",
    "SidebarItem.qml",
    "StatCard.qml",
    "TagPill.qml",
    "TaskInboxScreen.qml",
    "Theme.qml",
    "TopicTreeCard.qml",
]
datas = [(str(project_root / file_name), ".") for file_name in qml_files if (project_root / file_name).exists()]
if (project_root / "assets").exists():
    datas += Tree(str(project_root / "assets"), prefix="assets")
if (project_root / "nlp" / "data").exists():
    datas += Tree(str(project_root / "nlp" / "data"), prefix="nlp/data")

hiddenimports = []
for package_name in ("studyflow_backend", "services", "nlp", "llm", "ui", "config", "db", "models"):
    hiddenimports.extend(collect_submodules(package_name))


a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SmartStudyScheduleSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SmartStudyScheduleSystem",
)
