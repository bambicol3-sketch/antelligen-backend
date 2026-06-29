from dataclasses import dataclass, field

from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint
from app.domains.hermes.domain.value_object.agent_capability import AgentCapability


@dataclass(frozen=True)
class AgentToolModule:
    """capability 선택 시 패키지에 포함되는 '도구 모듈' 정의. (순수 도메인 메타데이터)

    tool_file 은 패키지 루트 기준 상대 경로, import_stmt/callable_name 은 agent_main 의
    도구 목록 조립에 쓰인다. triggers 중 하나라도 선택되면 이 모듈이 포함된다.
    guidance 는 system_prompt 에 덧붙는 도구별 행동 규칙(없으면 생략)."""

    tool_file: str
    import_stmt: str
    callable_name: str
    triggers: tuple[AgentCapability, ...]
    guidance: str = ""


# capability → 도구 모듈 매핑. 신규 도구 추가는 여기에 한 줄만 더하면 된다.
_TOOL_MODULES: tuple[AgentToolModule, ...] = (
    AgentToolModule(
        tool_file="tools/win32com_drm_reader.py",
        import_stmt="from tools.win32com_drm_reader import read_office_document",
        callable_name="read_office_document",
        triggers=(AgentCapability.DRM_FILE_READ, AgentCapability.OFFICE_AUTOMATION),
        guidance=(
            "- DRM 문서는 read_office_document 도구로 직원 PC 로컬에서만 판독합니다. "
            "원본 파일을 외부로 전송하지 않습니다."
        ),
    ),
    AgentToolModule(
        tool_file="tools/executable_builder.py",
        import_stmt="from tools.executable_builder import build_executable",
        callable_name="build_executable",
        triggers=(AgentCapability.EXECUTABLE_BUILD,),
        guidance=(
            "- 실행파일(.exe)은 build_executable 도구로 직원 PC 로컬에서 PyInstaller 로 빌드합니다. "
            "빌드 대상 스크립트 경로를 사용자에게 확인한 뒤 실행합니다."
        ),
    ),
    AgentToolModule(
        tool_file="tools/ui_scaffolder.py",
        import_stmt="from tools.ui_scaffolder import scaffold_ui",
        callable_name="scaffold_ui",
        triggers=(AgentCapability.UI_SCAFFOLD,),
        guidance=(
            "- 간단한 UI/UX 는 scaffold_ui 도구로 단일 HTML(인라인 CSS/JS) 파일을 생성합니다. "
            "산출 경로와 화면 구성을 사용자에게 확인한 뒤 생성합니다."
        ),
    ),
)


@dataclass
class AgentPackagePlan:
    """blueprint 로부터 계산된 '패키지 구성 계획'. 순수 데이터(파일 IO/zip/템플릿 엔진 없음).
    어떤 텍스트를 어디에 넣을지, 어떤 도구 파일을 포함할지를 결정한다."""

    package_name: str
    title: str
    model: str
    system_prompt: str
    workflow_markdown: str
    tool_imports: str          # agent_main 상단 import 블록
    tools_list: str            # agent_main 의 tools = [...] 리터럴
    included_tool_files: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)


class AgentPackagePlanner:
    """AgentBlueprint → AgentPackagePlan 순수 변환기.

    레이어 규칙(Domain): FastAPI / ORM / Jinja / 파일시스템 의존 금지. 순수 계산만 수행한다.
    실제 파일 조립·렌더링은 outbound 패키징 어댑터가 이 plan 을 소비해 수행한다.
    """

    @staticmethod
    def all_gated_tool_files() -> set[str]:
        """capability 로 게이트되는 모든 도구 파일 경로. 미선택 시 zip 에서 제외 대상."""
        return {m.tool_file for m in _TOOL_MODULES}

    @staticmethod
    def plan(blueprint: AgentBlueprint) -> AgentPackagePlan:
        modules = AgentPackagePlanner._included_modules(blueprint)
        workflow_md = AgentPackagePlanner._workflow_markdown(blueprint)
        return AgentPackagePlan(
            package_name=blueprint.package_name(),
            title=blueprint.title,
            model=blueprint.model,
            system_prompt=AgentPackagePlanner._system_prompt(blueprint, workflow_md, modules),
            workflow_markdown=workflow_md,
            tool_imports=AgentPackagePlanner._tool_imports(modules),
            tools_list=AgentPackagePlanner._tools_list(modules),
            included_tool_files=[m.tool_file for m in modules],
            capabilities=[c.value for c in blueprint.capabilities],
        )

    @staticmethod
    def _included_modules(blueprint: AgentBlueprint) -> list[AgentToolModule]:
        return [
            m for m in _TOOL_MODULES
            if any(blueprint.has_capability(c) for c in m.triggers)
        ]

    @staticmethod
    def _tool_imports(modules: list[AgentToolModule]) -> str:
        if not modules:
            return "# (도구 미포함 — capability 미선택)"
        return "\n".join(m.import_stmt for m in modules)

    @staticmethod
    def _tools_list(modules: list[AgentToolModule]) -> str:
        return "[" + ", ".join(m.callable_name for m in modules) + "]"

    @staticmethod
    def _workflow_markdown(blueprint: AgentBlueprint) -> str:
        if not blueprint.workflow_steps:
            return "_(등록된 워크플로우 단계가 없습니다.)_"
        lines: list[str] = []
        for step in sorted(blueprint.workflow_steps, key=lambda s: s.order):
            lines.append(f"{step.order}. {step.instruction}")
            if step.inputs:
                lines.append(f"   - 입력: {', '.join(step.inputs)}")
            if step.expected_output:
                lines.append(f"   - 기대 산출물: {step.expected_output}")
        return "\n".join(lines)

    @staticmethod
    def _system_prompt(
        blueprint: AgentBlueprint,
        workflow_md: str,
        modules: list[AgentToolModule],
    ) -> str:
        goal = blueprint.goal.strip() or "(목표 미지정)"
        rules = [m.guidance for m in modules if m.guidance]
        rules.extend(
            [
                "- 파괴적이거나 되돌리기 어려운 작업 전에는 사용자에게 확인을 요청합니다.",
                "- 불확실하면 추측하지 말고 사용자에게 질문합니다.",
                "- 결과는 한국어로 간결하게 보고합니다.",
            ]
        )
        rules_md = "\n".join(rules)
        return (
            f"당신은 '{blueprint.title}' 업무를 자동화하는 Antelligen 사내 업무 에이전트입니다.\n"
            f"목표(KPI): {goal}\n\n"
            "아래 워크플로우를 순서대로, 정확하고 안전하게 수행하세요.\n\n"
            f"{workflow_md}\n\n"
            "규칙:\n"
            f"{rules_md}"
        )
