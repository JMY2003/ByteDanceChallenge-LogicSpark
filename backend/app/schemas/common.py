from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectStatus(str, Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    needs_human_review = "needs_human_review"


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"
    waiting_human = "waiting_human"


class QualityScore(StrictBaseModel):
    total: int = Field(ge=0, le=100)
    coverage: int = Field(ge=0, le=20)
    evidence_strength: int = Field(ge=0, le=20)
    citation_accuracy: int = Field(ge=0, le=15)
    analysis_depth: int = Field(ge=0, le=15)
    structure: int = Field(ge=0, le=10)
    consistency: int = Field(ge=0, le=10)
    readability: int = Field(ge=0, le=5)
    novelty: int = Field(ge=0, le=5)


class ToolCallLog(StrictBaseModel):
    tool_name: str
    input: dict
    output_summary: str
    started_at: str
    ended_at: str
    status: str
    error: str | None = None

