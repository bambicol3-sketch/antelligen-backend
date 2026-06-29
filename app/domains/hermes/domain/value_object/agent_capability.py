from enum import Enum


class AgentCapability(str, Enum):
    """생성 에이전트가 보유할 수 있는 기능. capability 에 따라 패키지에 포함되는
    툴/권한이 달라진다. (순수 도메인 값 — 외부 의존 없음)"""

    DRM_FILE_READ = "drm_file_read"          # win32com 으로 DRM 문서를 로컬 판독
    OFFICE_AUTOMATION = "office_automation"  # MS Office(Word/Excel/PowerPoint) COM 자동화
    FILE_WRITE = "file_write"                # 로컬 파일 산출물 생성
    WEB_FETCH = "web_fetch"                  # 웹 페이지 조회
    EXECUTABLE_BUILD = "executable_build"    # PyInstaller 로 .exe 등 단독 실행파일 빌드
    UI_SCAFFOLD = "ui_scaffold"              # 간단한 HTML/CSS/JS UI/UX 산출물 생성

    @classmethod
    def from_value(cls, value: str) -> "AgentCapability | None":
        try:
            return cls(value)
        except ValueError:
            return None
