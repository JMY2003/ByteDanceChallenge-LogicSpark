from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.mvp_agents import build_mvp_tasks


@dataclass(frozen=True)
class DAGNodeSpec:
    id: str
    agent_name: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 1
    max_retries: int = 2
    human_review_required: bool = False


def mvp_dag(default_retries: int = 2, enable_deep_review: bool = True) -> list[DAGNodeSpec]:
    return [
        DAGNodeSpec(
            id=item["id"],
            agent_name=item["agent"],
            depends_on=list(item.get("depends_on", [])),
            priority=int(item.get("priority", 1)),
            max_retries=default_retries,
        )
        for item in build_mvp_tasks(enable_deep_review)
    ]


def validate_dag(nodes: list[DAGNodeSpec]) -> None:
    node_ids = {node.id for node in nodes}
    for node in nodes:
        missing = [dependency for dependency in node.depends_on if dependency not in node_ids]
        if missing:
            raise ValueError(f"Node {node.id} depends on missing nodes: {missing}")
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {node.id: node for node in nodes}

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            raise ValueError(f"DAG cycle detected at {node_id}")
        visiting.add(node_id)
        for dependency in by_id[node_id].depends_on:
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)

    for node in nodes:
        visit(node.id)
