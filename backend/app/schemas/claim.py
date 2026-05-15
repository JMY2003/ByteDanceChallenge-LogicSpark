from pydantic import Field

from app.schemas.common import StrictBaseModel


class ClaimItem(StrictBaseModel):
    claim_id: str
    claim_text: str
    claim_type: str
    subject: str
    confidence: float = Field(ge=0, le=1)
    risk_level: str = "medium"
    evidence_ids: list[str] = Field(default_factory=list)
    created_by_agent: str
    review_status: str = "pending"
    review_comments: list[str] = Field(default_factory=list)

