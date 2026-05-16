from __future__ import annotations

import json
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id, stable_id
from app.core.time import utc_now
from app.db.models import AgentRun, Competitor, Evidence, Project, Report, Task
from app.db.session import get_db
from app.orchestrator.executor import DAGOrchestrator, ensure_project_tasks
from app.schemas.competitor import CompetitorListResponse
from app.schemas.evidence import EvidenceItem, EvidenceListResponse
from app.schemas.project import (
    ConfirmCompetitorsRequest,
    ProjectCreate,
    ProjectCreated,
    ProjectHistoryItem,
    ProjectHistoryResponse,
    ProjectStatusResponse,
)
from app.schemas.report import ExportRequest, ExportResponse, ReportEditRequest, ReportResponse
from app.schemas.task import AgentRunResponse, DAGEdge, DAGNode, DAGResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectCreated)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectCreated:
    project = Project(
        id=new_id("proj"),
        query=payload.query,
        mode=payload.mode,
        language=payload.language,
        status="created",
        output_formats=payload.output_formats,
        max_competitors=payload.max_competitors,
        enable_deep_review=payload.enable_deep_review,
        settings={},
    )
    db.add(project)
    db.commit()
    ensure_project_tasks(db, project)
    return ProjectCreated(project_id=project.id, status=project.status)


@router.get("/history", response_model=ProjectHistoryResponse)
def get_project_history(db: Session = Depends(get_db)) -> ProjectHistoryResponse:
    projects = db.scalars(
        select(Project)
        .where(Project.status == "completed")
        .order_by(Project.updated_at.desc())
        .limit(30)
    ).all()
    if not projects:
        return ProjectHistoryResponse(projects=[])

    project_ids = [project.id for project in projects]
    task_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for project_id, task_status in db.execute(
        select(Task.project_id, Task.status).where(Task.project_id.in_(project_ids))
    ):
        task_counts[project_id][task_status] += 1

    quality_scores: dict[str, dict | None] = {}
    reports = db.scalars(select(Report).where(Report.project_id.in_(project_ids), Report.format == "markdown")).all()
    for report in reports:
        quality_scores[report.project_id] = report.report_metadata.get("quality_score")

    completed = []
    for project in projects:
        counts = dict(task_counts[project.id])
        if not counts.get("success", 0) or counts.get("failed", 0) or counts.get("running", 0) or counts.get("pending", 0):
            continue
        completed.append(
            ProjectHistoryItem(
                project_id=project.id,
                status=project.status,
                query=project.query,
                mode=project.mode,
                language=project.language,
                created_at=project.created_at.isoformat(),
                completed_at=project.updated_at.isoformat(),
                task_counts=counts,
                quality_score=quality_scores.get(project.id),
            )
        )
    return ProjectHistoryResponse(projects=completed)


@router.post("/{project_id}/run", response_model=ProjectStatusResponse)
async def run_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        status = await DAGOrchestrator(db).run_project(project_id, resume=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return status


@router.get("/{project_id}/status", response_model=ProjectStatusResponse)
def get_project_status(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_tasks(db, project)
    return DAGOrchestrator(db).project_status(project_id)


@router.get("/{project_id}/dag", response_model=DAGResponse)
def get_project_dag(project_id: str, db: Session = Depends(get_db)) -> DAGResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = ensure_project_tasks(db, project)
    intent_task = next((task for task in tasks if task.node_id == "intent"), None)
    needs_competitor_confirmation = bool((intent_task.output or {}).get("needs_competitor_confirmation")) if intent_task else False
    nodes = [
        DAGNode(
            id=task.node_id,
            label=task.node_id.replace("_", " ").title(),
            agent_name=task.agent_name,
            depends_on=task.depends_on,
            status=task.status,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            human_review_required=task.node_id == "web_search" and needs_competitor_confirmation,
        )
        for task in sorted(tasks, key=lambda item: item.created_at)
    ]
    edges = [
        DAGEdge(id=f"{dependency}->{task.node_id}", source=dependency, target=task.node_id)
        for task in tasks
        for dependency in task.depends_on
    ]
    return DAGResponse(project_id=project_id, nodes=nodes, edges=edges)


@router.get("/{project_id}/agent-runs", response_model=list[AgentRunResponse])
def get_agent_runs(project_id: str, db: Session = Depends(get_db)) -> list[AgentRunResponse]:
    ensure_project_exists(db, project_id)
    runs = db.scalars(select(AgentRun).where(AgentRun.project_id == project_id).order_by(AgentRun.started_at.asc())).all()
    return [
        AgentRunResponse(
            id=run.id,
            project_id=run.project_id,
            task_id=run.task_id,
            agent_name=run.agent_name,
            status=run.status,
            input=run.input,
            output=run.output,
            tool_calls=run.tool_calls,
            model=run.model,
            token_usage=run.token_usage,
            cost_estimate=run.cost_estimate,
            error=run.error,
            started_at=run.started_at.isoformat() if run.started_at else None,
            ended_at=run.ended_at.isoformat() if run.ended_at else None,
            duration_ms=run.duration_ms,
        )
        for run in runs
    ]


@router.get("/{project_id}/competitors", response_model=CompetitorListResponse)
def get_competitors(project_id: str, db: Session = Depends(get_db)) -> CompetitorListResponse:
    ensure_project_exists(db, project_id)
    competitors = db.scalars(select(Competitor).where(Competitor.project_id == project_id).order_by(Competitor.name)).all()
    return CompetitorListResponse(competitors=[competitor.profile for competitor in competitors])


@router.get("/{project_id}/evidence", response_model=EvidenceListResponse)
def get_evidence(project_id: str, db: Session = Depends(get_db)) -> EvidenceListResponse:
    ensure_project_exists(db, project_id)
    evidence_items = db.scalars(select(Evidence).where(Evidence.project_id == project_id).order_by(Evidence.created_at)).all()
    return EvidenceListResponse(evidence=[evidence_schema(item) for item in evidence_items])


@router.get("/{project_id}/evidence/{evidence_id}", response_model=EvidenceItem)
def get_evidence_item(project_id: str, evidence_id: str, db: Session = Depends(get_db)) -> EvidenceItem:
    ensure_project_exists(db, project_id)
    item = db.get(Evidence, evidence_id)
    if not item or item.project_id != project_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence_schema(item)


@router.get("/{project_id}/report", response_model=ReportResponse)
def get_report(project_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    ensure_project_exists(db, project_id)
    reports = db.scalars(select(Report).where(Report.project_id == project_id)).all()
    by_format = {report.format: report for report in reports}
    json_report = None
    if "json" in by_format:
        json_report = json.loads(by_format["json"].content)
    quality_score = None
    if "markdown" in by_format:
        quality_score = by_format["markdown"].report_metadata.get("quality_score")
    return ReportResponse(
        project_id=project_id,
        markdown=by_format.get("markdown").content if "markdown" in by_format else None,
        html=by_format.get("html").content if "html" in by_format else None,
        json_report=json_report,
        quality_score=quality_score,
    )


@router.post("/{project_id}/export", response_model=ExportResponse)
def export_report(project_id: str, payload: ExportRequest, db: Session = Depends(get_db)) -> ExportResponse:
    ensure_project_exists(db, project_id)
    report = db.scalars(select(Report).where(Report.project_id == project_id, Report.format == payload.format)).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"{payload.format} report not found")
    content_type = {
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json",
        "ppt_outline": "text/markdown",
    }.get(payload.format, "text/plain")
    extension = {"markdown": "md", "ppt_outline": "ppt-outline.md"}.get(payload.format, payload.format)
    return ExportResponse(
        project_id=project_id,
        format=payload.format,
        filename=f"competescope-{project_id}.{extension}",
        content_type=content_type,
        content=report.content,
    )


@router.post("/{project_id}/human/confirm-competitors")
def confirm_competitors(project_id: str, payload: ConfirmCompetitorsRequest, db: Session = Depends(get_db)) -> dict:
    project = ensure_project_exists(db, project_id)
    project.settings = {**project.settings, "confirmed_competitors": payload.competitors}
    project.status = "created"
    project.updated_at = utc_now()
    intent_task = db.scalars(select(Task).where(Task.project_id == project_id, Task.node_id == "intent")).first()
    if intent_task and intent_task.output:
        intent_task.output = {**intent_task.output, "target_companies": payload.competitors, "needs_competitor_confirmation": False}
    db.commit()
    return {"project_id": project_id, "confirmed_competitors": payload.competitors}


@router.post("/{project_id}/tasks/{task_id}/rerun")
async def rerun_task(project_id: str, task_id: str, db: Session = Depends(get_db)) -> dict:
    ensure_project_exists(db, project_id)
    task = db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "pending"
    task.error = None
    task.retry_count = 0
    task.output = {}
    downstream = db.scalars(select(Task).where(Task.project_id == project_id)).all()
    changed = [task.node_id]
    for other in downstream:
        if task.node_id in other.depends_on:
            other.status = "pending"
            other.output = {}
            changed.append(other.node_id)
    db.commit()
    status = await DAGOrchestrator(db).run_project(project_id, resume=True)
    return {"rerun_from": task.node_id, "reset_nodes": changed, "status": status}


@router.patch("/{project_id}/report", response_model=ReportResponse)
def edit_report(project_id: str, payload: ReportEditRequest, db: Session = Depends(get_db)) -> ReportResponse:
    ensure_project_exists(db, project_id)
    report_id = stable_id("report", project_id, "markdown")
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Markdown report not found")
    report.content = payload.markdown
    report.report_metadata = {**report.report_metadata, "human_edited": True, "edited_at": utc_now().isoformat()}
    db.commit()
    return get_report(project_id, db)


def ensure_project_exists(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def evidence_schema(item: Evidence) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=item.id,
        source_url=item.source_url,
        source_title=item.source_title,
        source_type=item.source_type,
        publisher=item.publisher,
        published_at=item.published_at,
        retrieved_at=item.retrieved_at.isoformat() if hasattr(item.retrieved_at, "isoformat") else str(item.retrieved_at),
        doc_id=item.document_id,
        chunk_id=item.chunk_id,
        quote=item.quote,
        summary=item.summary,
        credibility_score=item.credibility_score,
        freshness_score=item.freshness_score,
        is_primary_source=item.is_primary_source,
        is_potentially_outdated=item.is_potentially_outdated,
        supports_claim_ids=item.supports_claim_ids,
        metadata=item.evidence_metadata,
    )
