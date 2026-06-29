"""
ui_scaffolder — 간단한 UI/UX 화면을 단일 HTML(인라인 CSS/JS) 파일로 생성.

- 이 파일은 '생성 에이전트 패키지 전용 자산'입니다. 백엔드(Agent Factory)는 절대 import 하지 않습니다.
- 외부 빌드 도구/프레임워크 없이 표준 라이브러리만으로 즉시 브라우저로 열 수 있는 HTML 을 만듭니다.
- 산출물은 직원 PC 로컬 경로에만 기록됩니다.
"""

from __future__ import annotations

import html
import os

from anthropic import beta_tool

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --fg: #e2e8f0; --accent: #38bdf8; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--fg); }}
  header {{ padding: 24px 32px; border-bottom: 1px solid #334155; }}
  h1 {{ margin: 0; font-size: 20px; }}
  main {{ max-width: 880px; margin: 0 auto; padding: 32px; display: grid; gap: 20px; }}
  section {{ background: var(--card); border-radius: 12px; padding: 20px 24px; }}
  section h2 {{ margin: 0 0 8px; font-size: 16px; color: var(--accent); }}
  button {{ background: var(--accent); color: #0f172a; border: 0; border-radius: 8px;
            padding: 10px 16px; font-weight: 600; cursor: pointer; }}
  footer {{ text-align: center; padding: 24px; color: #64748b; font-size: 12px; }}
</style>
</head>
<body>
<header><h1>{title}</h1></header>
<main>
{sections}
</main>
<footer>Antelligen Agent Factory 가 생성한 UI 스캐폴드</footer>
<script>
  // 데모 상호작용: 버튼 클릭 시 안내 메시지 표시
  document.querySelectorAll("button[data-action]").forEach(function (btn) {{
    btn.addEventListener("click", function () {{
      console.log("action:", btn.dataset.action);
      btn.textContent = "✓ " + btn.dataset.action;
    }});
  }});
</script>
</body>
</html>
"""


@beta_tool
def scaffold_ui(output_path: str, title: str = "Antelligen UI", sections: list[str] | None = None) -> str:
    """Generate a simple, self-contained UI/UX screen as a single HTML file (inline CSS/JS).

    Produces a responsive dark-themed page openable directly in any browser — no build step
    or framework required. Writes the file to a local path on this PC.

    Args:
        output_path: Absolute path of the .html file to create.
        title: Page title shown in the header and browser tab.
        sections: Section headings to render as cards. Each becomes a titled panel with a
            sample action button. Defaults to a single "시작하기" section when omitted.
    """
    if not output_path.lower().endswith((".html", ".htm")):
        return f"HTML(.html/.htm) 파일 경로만 생성할 수 있습니다: {output_path}"

    items = sections or ["시작하기"]
    blocks: list[str] = []
    for heading in items:
        safe = html.escape(str(heading))
        blocks.append(
            f'  <section>\n'
            f'    <h2>{safe}</h2>\n'
            f'    <button data-action="{safe}">{safe} 실행</button>\n'
            f'  </section>'
        )

    page = _PAGE_TEMPLATE.format(title=html.escape(title), sections="\n".join(blocks))

    directory = os.path.dirname(os.path.abspath(output_path))
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(page)
    except OSError as e:
        return f"파일 생성 실패: {e}"

    return f"UI 생성 성공: {output_path} (섹션 {len(items)}개). 브라우저로 열어 확인하세요."
