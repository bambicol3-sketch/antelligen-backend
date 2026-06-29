from pydantic import BaseModel


class AgentPackageResponse(BaseModel):
    """다운로드 패키지 메타데이터(실제 바이너리는 별도 다운로드 엔드포인트가 반환)."""

    blueprint_id: str
    package_name: str
    filename: str
    size_bytes: int
    capabilities: list[str]
