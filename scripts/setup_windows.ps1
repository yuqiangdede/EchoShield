param(
    [switch]$InstallFFmpeg
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ 未安装或不在 PATH。"
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if ($InstallFFmpeg -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        Write-Host "FFmpeg 已安装。请重新打开 PowerShell 后运行 .venv\Scripts\echoshield-doctor.exe"
        exit 0
    }
    Write-Warning "未找到 FFmpeg。可重新执行：.\scripts\setup_windows.ps1 -InstallFFmpeg"
}

& .\.venv\Scripts\echoshield-doctor.exe
Write-Host "\n下一步：.\.venv\Scripts\echoshield-demo.exe"
