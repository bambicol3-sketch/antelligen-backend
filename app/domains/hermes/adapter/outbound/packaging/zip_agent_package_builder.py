# blueprint → 자립 실행 에이전트 패키지(zip) 조립.
# 템플릿(infrastructure/templates/agent/*)을 읽어 토큰 치환 후 zip 으로 묶는다.
# 의존성 무변경 원칙: Jinja 등 외부 템플릿 엔진을 쓰지 않고 단순 {{TOKEN}} 치환만 한다.
# ⚠️ win32com 툴 파일은 '텍스트 자산'으로 복사만 한다 — 백엔드는 절대 import 하지 않는다.

import io
import logging
import zipfile
from pathlib import Path

from app.domains.hermes.application.port.agent_package_builder_port import (
    AgentPackageBuilderPort,
    BuiltAgentPackage,
)
from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint
from app.domains.hermes.domain.service.agent_package_planner import (
    AgentPackagePlan,
    AgentPackagePlanner,
)

logger = logging.getLogger(__name__)

# .../adapter/outbound/packaging/zip_agent_package_builder.py → parents[3] = hermes 도메인 루트
_HERMES_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE_DIR = _HERMES_ROOT / "infrastructure" / "templates" / "agent"


class ZipAgentPackageBuilder(AgentPackageBuilderPort):
    def build(self, blueprint: AgentBlueprint) -> BuiltAgentPackage:
        plan = AgentPackagePlanner.plan(blueprint)
        tokens = self._tokens(plan)
        # 선택되지 않은 capability 의 도구 파일은 zip 에서 제외한다.
        excluded_tool_files = (
            AgentPackagePlanner.all_gated_tool_files() - set(plan.included_tool_files)
        )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for src in sorted(_TEMPLATE_DIR.rglob("*")):
                if not src.is_file():
                    continue
                # 의도치 않은 산출물(파이썬 캐시 등) 제외
                if "__pycache__" in src.parts or src.suffix == ".pyc":
                    continue
                rel = src.relative_to(_TEMPLATE_DIR).as_posix()
                is_template = rel.endswith(".tmpl")
                out_rel = rel[:-5] if is_template else rel

                if out_rel in excluded_tool_files:
                    continue

                raw = src.read_text(encoding="utf-8")
                content = self._render(raw, tokens) if is_template else raw
                zf.writestr(f"{plan.package_name}/{out_rel}", content)

            # 시스템 프롬프트는 런타임에 파일로 읽는다(파이썬 문자열 이스케이프 회피).
            zf.writestr(f"{plan.package_name}/system_prompt.txt", plan.system_prompt)

        logger.info(
            "agent package built: %s (tools=%s, caps=%s)",
            plan.package_name,
            plan.included_tool_files,
            plan.capabilities,
        )
        return BuiltAgentPackage(
            filename=f"{plan.package_name}.zip",
            content=buffer.getvalue(),
            package_name=plan.package_name,
            capabilities=plan.capabilities,
        )

    @staticmethod
    def _tokens(plan: AgentPackagePlan) -> dict[str, str]:
        return {
            "PACKAGE_NAME": plan.package_name,
            "TITLE": plan.title,
            "MODEL": plan.model,
            "WORKFLOW_MARKDOWN": plan.workflow_markdown,
            "TOOL_IMPORTS": plan.tool_imports,
            "TOOLS_LIST": plan.tools_list,
            "CAPABILITIES": ", ".join(plan.capabilities) or "(없음)",
        }

    @staticmethod
    def _render(raw: str, tokens: dict[str, str]) -> str:
        for key, value in tokens.items():
            raw = raw.replace("{{" + key + "}}", value)
        return raw
