# Antelligen 사내 에이전트 설치 스크립트 (Windows PowerShell)
# 사용: powershell -ExecutionPolicy Bypass -File setup\install.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot   # 패키지 루트

Write-Host "[1/3] 가상환경 생성..."
python -m venv "$root\.venv"

Write-Host "[2/3] pip 업그레이드..."
& "$root\.venv\Scripts\python.exe" -m pip install --upgrade pip

Write-Host "[3/3] 의존성 설치..."
$wheels = Join-Path $root "wheels"
if (Test-Path $wheels) {
    Write-Host "  (오프라인 wheelhouse 감지 → --no-index 설치)"
    & "$root\.venv\Scripts\pip.exe" install --no-index --find-links "$wheels" -r "$root\requirements.txt"
} else {
    & "$root\.venv\Scripts\pip.exe" install -r "$root\requirements.txt"
}

Write-Host ""
Write-Host "설치 완료."
Write-Host "다음 단계: .env.example 을 .env 로 복사 후 값을 채우고, setup\run.ps1 로 실행하세요."
