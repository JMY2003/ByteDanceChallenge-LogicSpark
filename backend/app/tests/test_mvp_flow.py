import os
from pathlib import Path

os.environ["COMPETESCOPE_DATABASE_URL"] = "sqlite:///./test_competescope.db"
os.environ["COMPETESCOPE_OFFLINE_MODE"] = "true"

from app.config import get_settings

get_settings.cache_clear()

TEST_DB = Path("test_competescope.db")
if TEST_DB.exists():
    TEST_DB.unlink()

from fastapi.testclient import TestClient

from app.main import app


def test_mvp_query_to_markdown_report_flow() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        created = client.post(
            "/api/projects",
            json={
                "query": "请分析 AI 办公协作领域的竞品，包括 Notion AI、ClickUp AI、Coda AI，并生成产品经理视角报告。",
                "mode": "quick",
                "language": "zh-CN",
                "output_formats": ["markdown", "html", "json"],
                "max_competitors": 6,
                "enable_deep_review": True,
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["project_id"]

        run = client.post(f"/api/projects/{project_id}/run")
        assert run.status_code == 200, run.text
        assert run.json()["status"] == "completed"

        dag = client.get(f"/api/projects/{project_id}/dag")
        assert dag.status_code == 200
        assert {node["status"] for node in dag.json()["nodes"]} == {"success"}

        competitors = client.get(f"/api/projects/{project_id}/competitors")
        assert competitors.status_code == 200
        assert len(competitors.json()["competitors"]) == 3

        evidence = client.get(f"/api/projects/{project_id}/evidence")
        assert evidence.status_code == 200
        evidence_items = evidence.json()["evidence"]
        assert len(evidence_items) >= 6
        first = evidence_items[0]
        for key in ["source_url", "quote", "summary", "retrieved_at", "credibility_score", "freshness_score"]:
            assert key in first

        report = client.get(f"/api/projects/{project_id}/report")
        assert report.status_code == 200
        body = report.json()
        assert body["markdown"]
        assert "## 事实结论" in body["markdown"]
        assert "ev_" in body["markdown"]
        assert body["html"]
        assert body["json_report"]["claims"]
        assert body["quality_score"]["total"] >= 70

        runs = client.get(f"/api/projects/{project_id}/agent-runs")
        assert runs.status_code == 200
        assert len(runs.json()) == 8

