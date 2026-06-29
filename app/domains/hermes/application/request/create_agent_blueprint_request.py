from pydantic import BaseModel, Field


class WorkflowStepInput(BaseModel):
    instruction: str
    inputs: list[str] = Field(default_factory=list)
    expected_output: str = ""


class CreateAgentBlueprintRequest(BaseModel):
    """직원이 입력하는 '워크플로우' 요청. PUT(전체 교체)에서도 동일 스키마를 재사용한다."""

    owner: str
    title: str
    goal: str = ""
    workflow_steps: list[WorkflowStepInput] = Field(default_factory=list)
    # AgentCapability 값들 (예: ["drm_file_read", "office_automation", "executable_build",
    # "ui_scaffold"]). 알 수 없는 값은 무시.
    capabilities: list[str] = Field(default_factory=list)
    # None 이면 DEFAULT_AGENT_MODEL 적용
    model: str | None = None
