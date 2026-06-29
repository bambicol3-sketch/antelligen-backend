# Antelligen 사내 에이전트 실행 스크립트 (Windows PowerShell)
# 사용: powershell -ExecutionPolicy Bypass -File setup\run.ps1 "수행할 작업 설명"
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot   # 패키지 루트
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "가상환경이 없습니다. 먼저 setup\install.ps1 을 실행하세요."
    exit 1
}

$task = $args -join " "
& $python "$root\agent_main.py" $task
