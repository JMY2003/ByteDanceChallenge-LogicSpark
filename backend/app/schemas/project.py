from pydantic import Field

from app.schemas.common import StrictBaseModel


class ProjectCreate(StrictBaseModel):
    query: str = Field(min_length=2)
    mode: str = "quick"
    language: str = "zh-CN"
    output_formats: list[str] = Field(default_factory=lambda: ["markdown", "html", "json"])
    max_competitors: int = Field(default=6, ge=1, le=20)
    enable_deep_review: bool = True


class ProjectCreated(StrictBaseModel):
    project_id: str
    status: str


class ProjectStatusResponse(StrictBaseModel):
    project_id: str
    status: str
    query: str
    mode: str
    language: str
    task_counts: dict[str, int]
    current_nodes: list[str]
    quality_score: dict | None = None


class ProjectHistoryItem(StrictBaseModel):
    project_id: str
    status: str
    query: str
    mode: str
    language: str
    created_at: str
    completed_at: str
    task_counts: dict[str, int]
    quality_score: dict | None = None


class ProjectHistoryResponse(StrictBaseModel):
    projects: list[ProjectHistoryItem]


class ConfirmCompetitorsRequest(StrictBaseModel):
    competitors: list[str]
