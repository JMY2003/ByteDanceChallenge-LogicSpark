from __future__ import annotations

import asyncio
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import AgentContext, compact_for_storage
from app.agents.registry import build_agent_registry
from app.config import get_settings
from app.core.ids import stable_id
from app.core.time import utc_now
from app.db.models import AgentRun, Project, Report, Task
from app.orchestrator.dag import DAGNodeSpec, mvp_dag, validate_dag
from app.services.llm_service import LLMService
from app.tools.registry import build_tool_registry


def task_id_for(project_id: str, node_id: str) -> str:
    return stable_id("task", project_id, node_id)


def ensure_project_tasks(db: Session, project: Project) -> list[Task]:
    settings = get_settings()
    nodes = mvp_dag(settings.task_default_retries)
    validate_dag(nodes)
    existing = {task.node_id: task for task in db.scalars(select(Task).where(Task.project_id == project.id)).all()}
    tasks = []
    for node in nodes:
        task = existing.get(node.id)
        if not task:
            task = Task(
                id=task_id_for(project.id, node.id),
                project_id=project.id,
                node_id=node.id,
                agent_name=node.agent_name,
                status="pending",
                depends_on=node.depends_on,
                max_retries=node.max_retries,
            )
            db.add(task)
        tasks.append(task)
    db.commit()
    return tasks


class DAGOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.config = get_settings()
        self.agent_registry = build_agent_registry()
        self.tools = build_tool_registry()

    async def run_project(self, project_id: str, resume: bool = True) -> dict:
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError(f"Project not found: {project_id}")

        ensure_project_tasks(self.db, project)
        interrupted = self.db.scalars(
            select(Task).where(Task.project_id == project_id, Task.status == "running")
        ).all()
        for task in interrupted:
            task.status = "pending"
            task.error = "Recovered from interrupted backend process."
            task.ended_at = utc_now()
            running_runs = self.db.scalars(
                select(AgentRun).where(
                    AgentRun.project_id == project_id,
                    AgentRun.task_id == task.id,
                    AgentRun.status == "running",
                )
            ).all()
            for run in running_runs:
                run.status = "failed"
                run.error = "Recovered from interrupted backend process."
                run.ended_at = utc_now()
        project.status = "running"
        project.updated_at = utc_now()
        self.db.commit()

        tasks = self.db.scalars(select(Task).where(Task.project_id == project_id)).all()
        task_by_node = {task.node_id: task for task in tasks}
        memory: dict[str, dict] = {
            task.node_id: task.output
            for task in tasks
            if task.status == "success" and task.output
        }

        while True:
            fresh_tasks = self.db.scalars(select(Task).where(Task.project_id == project_id)).all()
            pending = [task for task in fresh_tasks if task.status in {"pending", "failed"} and not (resume and task.status == "success")]
            unfinished = [task for task in fresh_tasks if task.status not in {"success", "skipped"}]
            if not unfinished:
                project.status = "completed"
                project.updated_at = utc_now()
                self.db.commit()
                break

            ready = []
            for task in pending:
                deps_done = all(task_by_node[dep].status == "success" for dep in task.depends_on)
                can_retry = task.status == "pending" or task.retry_count <= task.max_retries
                if deps_done and can_retry:
                    ready.append(task)

            if not ready:
                failed = [task for task in fresh_tasks if task.status == "failed"]
                project.status = "failed" if failed else "running"
                project.updated_at = utc_now()
                self.db.commit()
                break

            await asyncio.gather(*(self._run_task(project, task, memory) for task in ready))
            task_by_node = {task.node_id: task for task in self.db.scalars(select(Task).where(Task.project_id == project_id)).all()}
            if any(task.status == "failed" and task.retry_count > task.max_retries for task in task_by_node.values()):
                project.status = "failed"
                project.updated_at = utc_now()
                self.db.commit()
                break

        return self.project_status(project_id)

    async def _run_task(self, project: Project, task: Task, memory: dict[str, dict]) -> None:
        agent = self.agent_registry[task.agent_name]
        task.status = "running"
        task.started_at = utc_now()
        task.ended_at = None
        task.error = None
        project_payload = {
            "project_id": project.id,
            "query": project.query,
            "mode": project.mode,
            "language": project.language,
            "output_formats": project.output_formats,
            "max_competitors": project.max_competitors,
            "enable_deep_review": project.enable_deep_review,
        }
        dependency_outputs = {
            dependency: self.db.scalars(
                select(Task).where(Task.project_id == project.id, Task.node_id == dependency)
            ).one().output
            for dependency in task.depends_on
        }
        input_data = {
            "project": project_payload,
            "task": {"id": task.id, "node_id": task.node_id, "agent_name": task.agent_name},
            "dependency_outputs": dependency_outputs,
            "memory": memory,
        }
        task.input = compact_for_storage(input_data)
        self.db.commit()

        context = AgentContext(
            project_id=project.id,
            task_id=task.id,
            db=self.db,
            tools=self.tools,
            config=self.config,
            llm=LLMService(self.config),
            memory=memory,
        )
        try:
            output = await agent.execute(input_data, context)
            task.output = output
            task.status = "success"
            task.ended_at = utc_now()
            memory[task.node_id] = output
            self.db.commit()
        except Exception as exc:
            task.retry_count += 1
            task.status = "pending" if task.retry_count <= task.max_retries else "failed"
            task.error = str(exc)
            task.ended_at = utc_now()
            self.db.commit()

    def project_status(self, project_id: str) -> dict:
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError(f"Project not found: {project_id}")
        tasks = self.db.scalars(select(Task).where(Task.project_id == project_id)).all()
        counts = Counter(task.status for task in tasks)
        report = self.db.scalars(
            select(Report).where(Report.project_id == project_id, Report.format == "markdown")
        ).first()
        return {
            "project_id": project_id,
            "status": project.status,
            "query": project.query,
            "mode": project.mode,
            "language": project.language,
            "task_counts": dict(counts),
            "current_nodes": [task.node_id for task in tasks if task.status == "running"],
            "quality_score": report.report_metadata.get("quality_score") if report else None,
        }
