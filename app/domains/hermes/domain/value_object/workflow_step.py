from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """워크플로우 1단계. 직원이 입력한 반복 업무 절차의 한 스텝."""

    order: int
    instruction: str
    inputs: list[str] = field(default_factory=list)
    expected_output: str = ""
