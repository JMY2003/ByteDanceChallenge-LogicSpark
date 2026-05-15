from pydantic import Field

from app.schemas.common import StrictBaseModel


class DAGNode(StrictBaseModel):
    id: str
    label: str
    agent_name: str
    depends_on: list[str] = Field(default_factory=list)
    status: str = "pending"
    retry_count: int = 0
    max_retries: int = 2
    human_review_required: bool = False


class DAGEdge(StrictBaseModel):
    id: str
    source: str
    target: str


class DAGResponse(StrictBaseModel):
    project_id: str
    nodes: list[DAGNode]
    edges: list[DAGEdge]


class AgentRunResponse(StrictBaseModel):
    id: str
    project_id: str
    task_id: str
    agent_name: str
    status: str
    input: dict
    output: dict
    tool_calls: list[dict]
    model: str
    token_usage: dict
    cost_estimate: float | None = None
    error: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: int

