from app.schemas.common import QualityScore, StrictBaseModel


class ReportResponse(StrictBaseModel):
    project_id: str
    markdown: str | None = None
    html: str | None = None
    json_report: dict | None = None
    quality_score: QualityScore | None = None


class ExportRequest(StrictBaseModel):
    format: str = "markdown"


class ExportResponse(StrictBaseModel):
    project_id: str
    format: str
    filename: str
    content_type: str
    content: str


class ReportEditRequest(StrictBaseModel):
    markdown: str

