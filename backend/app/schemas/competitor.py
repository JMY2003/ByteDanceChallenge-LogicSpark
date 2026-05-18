from pydantic import Field

from app.schemas.common import StrictBaseModel


class EvidenceBoundText(StrictBaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class FeatureItem(StrictBaseModel):
    feature_id: str
    name: str
    category: str = "unknown"
    description: str
    support_status: str = "unknown"
    maturity: str = "unknown"
    evidence_ids: list[str] = Field(default_factory=list)


class PricingItem(StrictBaseModel):
    plan_name: str = "unknown"
    price: str = "unknown"
    currency: str | None = None
    billing_cycle: str = "unknown"
    target_segment: str = "unknown"
    included_features: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class CompetitorProfile(StrictBaseModel):
    competitor_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    company_name: str = "unknown"
    website: str | None = None
    founded_year: int | None = None
    headquarters: str | None = None
    company_stage: str = "unknown"
    product_category: str = "unknown"
    target_users: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    business_model: list[str] = Field(default_factory=list)
    positioning: dict = Field(default_factory=dict)
    features: list[FeatureItem] = Field(default_factory=list)
    pricing: list[PricingItem] = Field(default_factory=list)
    integrations: list[dict] = Field(default_factory=list)
    security_compliance: list[dict] = Field(default_factory=list)
    user_feedback: dict = Field(default_factory=lambda: {"pros": [], "cons": []})
    market_signals: list[dict] = Field(default_factory=list)
    technical_signals: list[dict] = Field(default_factory=list)
    swot: dict = Field(default_factory=lambda: {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []})
    source_assessment: dict = Field(default_factory=dict)
    llm_extraction: dict = Field(default_factory=dict)
    source_coverage: list[str] = Field(default_factory=list)
    last_updated: str


class CompetitorListResponse(StrictBaseModel):
    competitors: list[CompetitorProfile]
