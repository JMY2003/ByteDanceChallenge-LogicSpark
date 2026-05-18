from pydantic import Field

from app.schemas.common import QualityScore, StrictBaseModel


class IntentOutput(StrictBaseModel):
    analysis_topic: str
    target_companies: list[str]
    industry: str
    analysis_depth: str
    report_type: str
    required_dimensions: list[str]
    output_formats: list[str]
    needs_source_citation: bool
    needs_competitor_confirmation: bool = False


class PlannerTaskSpec(StrictBaseModel):
    id: str
    agent: str
    depends_on: list[str] = Field(default_factory=list)
    priority: int
    max_retries: int = 2
    human_review_required: bool = False


class PlannerOutput(StrictBaseModel):
    dag: dict
    tasks: list[PlannerTaskSpec]
    research_plan: dict = Field(default_factory=dict)


class SearchResult(StrictBaseModel):
    url: str
    title: str
    snippet: str
    source_type: str
    rank: int
    query: str
    competitor: str
    retrieved_at: str


class SearchResultsOutput(StrictBaseModel):
    search_results: list[SearchResult]


class CrawledDocument(StrictBaseModel):
    doc_id: str
    url: str
    title: str
    content: str
    content_hash: str
    source_type: str
    competitor: str
    retrieved_at: str
    metadata: dict = Field(default_factory=dict)


class DocumentsOutput(StrictBaseModel):
    documents: list[CrawledDocument]


class ChunkOutput(StrictBaseModel):
    chunk_id: str
    doc_id: str
    text: str
    section_title: str | None = None
    start_char: int
    end_char: int
    source_url: str
    competitor: str


class ExtractionOutput(StrictBaseModel):
    competitor_profiles: list[dict]
    chunks: list[ChunkOutput]


class EvidenceBuilderOutput(StrictBaseModel):
    evidence: list[dict]


class AnalysisOutput(StrictBaseModel):
    claims: list[dict]
    feature_matrix: dict
    strategic_insights: list[dict]
    comparison_dimensions: list[dict] = Field(default_factory=list)
    pricing_table: list[dict] = Field(default_factory=list)
    competitor_cards: list[dict] = Field(default_factory=list)
    evidence_gaps: list[dict] = Field(default_factory=list)
    source_mix: dict = Field(default_factory=dict)


class ReportWriterOutput(StrictBaseModel):
    report_id: str
    markdown: str
    html: str
    json_report: dict
    quality_score: QualityScore


class GenericAgentOutput(StrictBaseModel):
    agent: str
    status: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    payload: dict = Field(default_factory=dict)
