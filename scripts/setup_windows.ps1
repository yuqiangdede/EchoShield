param(
    [switch]$InstallFFmpeg
)

$ErrorActionPreference = "Stop"

Write-Host "EchoShield Windows setup"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ is required and must be available in PATH."
}

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python: $pythonVersion"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment: .venv"
    & python -m venv .venv
}

$venvPython = ".\.venv\Scripts\python.exe"
$doctor = ".\.venv\Scripts\echoshield-doctor.exe"
$demo = ".\.venv\Scripts\echoshield-demo.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment creation failed: $venvPython not found."
}

Write-Host "Installing EchoShield..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e ".[dev]"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if ($InstallFFmpeg) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            throw "winget was not found. Install FFmpeg manually and make sure ffmpeg/ffprobe are in PATH."
        }

        Write-Host "Installing FFmpeg with winget..."
        & winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        Write-Host "FFmpeg installation command completed."
        Write-Host "Open a NEW PowerShell window, return to this project, and run:"
        Write-Host "  $doctor"
        exit 0
    }

    Write-Warning "FFmpeg was not found in PATH."
    Write-Host "Install it with:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -InstallFFmpeg"
    Write-Host "Or install FFmpeg manually, then run:"
    Write-Host "  $doctor"
    exit 0
}

Write-Host "Running environment check..."
& $doctor

Write-Host ""
Write-Host "Setup completed. Run the built-in demo with:"
Write-Host "  $demo"
Write-Host ""
Write-Host "Test your own MP4 with:"
Write-Host "  .\.venv\Scripts\echoshield.exe input.mp4 -o output.mp4 --profile codec --fast --keep-workdir"
