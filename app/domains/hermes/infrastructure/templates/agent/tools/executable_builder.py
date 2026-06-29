"""
executable_builder — 파이썬 스크립트를 직원 PC 로컬에서 단독 실행파일(.exe 등)로 빌드.

- 이 파일은 '생성 에이전트 패키지 전용 자산'입니다. 백엔드(Agent Factory)는 절대 import 하지 않습니다.
- 동작 환경: PyInstaller 설치된 로컬 PC. Windows 에서 실행하면 .exe 가 생성됩니다.
- 빌드는 직원 PC 로컬에서만 수행되며, 산출물(실행파일)도 로컬 dist/ 에만 생성됩니다.
"""

from __future__ import annotations

import os
import subprocess
import sys

from anthropic import beta_tool


@beta_tool
def build_executable(
    script_path: str,
    name: str = "",
    onefile: bool = True,
    windowed: bool = False,
) -> str:
    """Build a standalone executable (.exe on Windows) from a Python script using PyInstaller.

    Runs locally on this PC. The script and its build output never leave the machine.

    Args:
        script_path: Absolute path to the entrypoint .py file to package.
        name: Output executable name (without extension). Defaults to the script's filename.
        onefile: If true, bundle everything into a single executable file.
        windowed: If true, build a GUI app without a console window (Windows/macOS).
    """
    if not os.path.isfile(script_path):
        return f"스크립트를 찾을 수 없습니다: {script_path}"
    if not script_path.lower().endswith(".py"):
        return f"파이썬(.py) 스크립트만 빌드할 수 있습니다: {script_path}"

    try:
        import PyInstaller  # type: ignore  # noqa: F401
    except ImportError:
        return (
            "PyInstaller 가 설치되지 않았습니다. 이 도구는 로컬 PC 전용입니다. "
            "`pip install pyinstaller` 후 다시 시도하세요. (ENVIRONMENT_SETUP.md 참조)"
        )

    work_dir = os.path.dirname(os.path.abspath(script_path))
    exe_name = name or os.path.splitext(os.path.basename(script_path))[0]

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--name", exe_name]
    if onefile:
        cmd.append("--onefile")
    if windowed:
        cmd.append("--windowed")
    cmd.append(script_path)

    try:
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return "빌드 시간 초과(10분). 스크립트 의존성을 줄이거나 수동으로 빌드하세요."
    except Exception as e:  # PyInstaller 실행 오류를 모델에 전달해 대처하도록 함
        return f"빌드 실행 실패: {e}"

    ext = ".exe" if sys.platform == "win32" else ""
    out_path = os.path.join(work_dir, "dist", f"{exe_name}{ext}")
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-1500:]
        return f"빌드 실패(코드 {result.returncode}):\n{tail}"
    if not os.path.isfile(out_path):
        return f"빌드는 종료됐으나 산출물을 찾지 못했습니다. dist/ 폴더를 확인하세요: {work_dir}"
    return f"빌드 성공: {out_path}"
