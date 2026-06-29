"""
win32com_drm_reader — DRM 보호된 MS Office 문서를 직원 Windows PC 로컬에서 COM 자동화로 판독.

- 이 파일은 '생성 에이전트 패키지 전용 자산'입니다. 백엔드(Agent Factory)는 절대 import 하지 않습니다.
- 동작 환경: Windows + pywin32(win32com) + MS Office(Word/Excel/PowerPoint) 설치 + 본인 열람 권한.
- 보안: DRM 원본 파일은 PC 를 떠나지 않습니다. 추출된 텍스트만 에이전트(LLM)로 전달됩니다.
"""

from __future__ import annotations

import os

from anthropic import beta_tool


@beta_tool
def read_office_document(path: str, max_chars: int = 20000) -> str:
    """Read a DRM-protected Microsoft Office document on this Windows PC and return its text.

    Opens Word/Excel/PowerPoint via COM automation under the current user's permissions so a
    DRM-protected file can be read locally without sending the original file anywhere.

    Args:
        path: Absolute path to a .docx/.doc/.xlsx/.xls/.pptx/.ppt file on this PC.
        max_chars: Maximum number of characters to return.
    """
    if not os.path.isfile(path):
        return f"파일을 찾을 수 없습니다: {path}"

    try:
        import pythoncom  # type: ignore
        import win32com.client as win32  # type: ignore
    except ImportError:
        return (
            "win32com(pywin32)이 설치되지 않았습니다. 이 도구는 Windows 사내 PC 전용입니다. "
            "ENVIRONMENT_SETUP.md 의 pywin32 설치 절차를 확인하세요."
        )

    ext = os.path.splitext(path)[1].lower()
    pythoncom.CoInitialize()
    try:
        if ext in (".docx", ".doc", ".rtf"):
            text = _read_word(win32, path)
        elif ext in (".xlsx", ".xls", ".xlsm"):
            text = _read_excel(win32, path)
        elif ext in (".pptx", ".ppt"):
            text = _read_powerpoint(win32, path)
        else:
            return f"지원하지 않는 확장자입니다: {ext} (Word/Excel/PowerPoint 만 지원)"
    except Exception as e:  # COM/DRM 오류를 모델에 그대로 전달해 대처하도록 함
        return f"문서 판독 실패: {e}"
    finally:
        pythoncom.CoUninitialize()

    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(이하 생략)"
    return text or "(문서에서 추출된 텍스트가 없습니다.)"


def _read_word(win32, path: str) -> str:
    app = win32.DispatchEx("Word.Application")
    app.Visible = False
    app.DisplayAlerts = False
    doc = None
    try:
        doc = app.Documents.Open(path, ReadOnly=True)
        return doc.Content.Text or ""
    finally:
        if doc is not None:
            doc.Close(SaveChanges=False)
        app.Quit()


def _read_excel(win32, path: str) -> str:
    app = win32.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    wb = None
    try:
        wb = app.Workbooks.Open(path, ReadOnly=True)
        parts: list[str] = []
        for sheet in wb.Worksheets:
            parts.append(f"# 시트: {sheet.Name}")
            values = sheet.UsedRange.Value
            if values is None:
                continue
            rows = values if isinstance(values, tuple) else (values,)
            for row in rows:
                cells = row if isinstance(row, tuple) else (row,)
                parts.append("\t".join("" if c is None else str(c) for c in cells))
        return "\n".join(parts)
    finally:
        if wb is not None:
            wb.Close(SaveChanges=False)
        app.Quit()


def _read_powerpoint(win32, path: str) -> str:
    app = win32.DispatchEx("PowerPoint.Application")
    pres = None
    try:
        pres = app.Presentations.Open(path, ReadOnly=True, WithWindow=False)
        parts: list[str] = []
        for idx, slide in enumerate(pres.Slides, 1):
            parts.append(f"# 슬라이드 {idx}")
            for shape in slide.Shapes:
                if shape.HasTextFrame and shape.TextFrame.HasText:
                    parts.append(shape.TextFrame.TextRange.Text)
        return "\n".join(parts)
    finally:
        if pres is not None:
            pres.Close()
        app.Quit()
