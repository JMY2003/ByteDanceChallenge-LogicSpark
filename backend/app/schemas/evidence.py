from pydantic import Field

from app.schemas.common import StrictBaseModel


class EvidenceItem(StrictBaseModel):
    evidence_id: str
    source_url: str
    source_title: str = ""
    source_type: str = "unknown"
    publisher: str | None = None
    published_at: str | None = None
    retrieved_at: str
    doc_id: str | None = None
    chunk_id: str | None = None
    quote: str
    summary: str
    credibility_score: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    is_primary_source: bool
    is_potentially_outdated: bool
    supports_claim_ids: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class EvidenceListResponse(StrictBaseModel):
    evidence: list[EvidenceItem]

