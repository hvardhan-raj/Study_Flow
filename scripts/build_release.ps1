param(
    [switch]$SkipChecks,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pyinstaller = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"
$specFile = Join-Path $projectRoot "SmartStudyScheduleSystem.spec"

if (-not (Test-Path $python)) {
    throw "Virtual environment not found at .venv. Create it and install requirements first."
}

if (-not (Test-Path $pyinstaller)) {
    throw "PyInstaller is not installed in .venv. Run 'pip install -r requirements.txt' first."
}

Push-Location $projectRoot
try {
    if ($Clean) {
        Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    }

    if (-not $SkipChecks) {
        & $python -m ruff check .
        & $python -m pytest
        $env:QT_QPA_PLATFORM = "offscreen"
        & $python -m scripts.profile_startup --smoke-only
    }

    & $pyinstaller --noconfirm $specFile
}
finally {
    Pop-Location
}
