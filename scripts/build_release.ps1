param(
    [switch]$SkipChecks,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specFile = Join-Path $projectRoot "SmartStudyScheduleSystem.spec"

if (-not (Test-Path $python)) {
    throw "Virtual environment not found at .venv. Create it and install requirements first."
}

& $python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if ($LASTEXITCODE -ne 0) {
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

    & $python -m PyInstaller --noconfirm $specFile
}
finally {
    Pop-Location
}
