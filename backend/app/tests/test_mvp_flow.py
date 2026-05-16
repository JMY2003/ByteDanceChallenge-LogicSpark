import os
from pathlib import Path

os.environ["COMPETESCOPE_DATABASE_URL"] = "sqlite:///./test_competescope.db"

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
        assert "## SWOT 摘要" in body["markdown"]
        assert "## QA 与红队挑战" in body["markdown"]
        assert "ev_" in body["markdown"]
        assert body["html"]
        assert body["json_report"]["claims"]
        assert body["json_report"]["agent_outputs"]["quality_gate"]["payload"]["quality_score"]
        assert body["quality_score"]["total"] >= 70

        runs = client.get(f"/api/projects/{project_id}/agent-runs")
        assert runs.status_code == 200
        assert len(runs.json()) >= 24


def test_ecommerce_query_uses_domain_competitors_and_deep_report_sections() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/projects",
            json={
                "query": "请分析网购协作领域的竞品，包括 京东、阿里巴巴、拼多多、唯品会等平台并生成产品经理视角报告。",
                "mode": "deep",
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

        competitors = client.get(f"/api/projects/{project_id}/competitors").json()["competitors"]
        names = {competitor["name"] for competitor in competitors}
        assert {"京东", "阿里巴巴", "拼多多", "唯品会"}.issubset(names)
        assert all(competitor["source_coverage"] for competitor in competitors)

        report = client.get(f"/api/projects/{project_id}/report").json()
        assert "e-commerce" in report["json_report"]["agent_outputs"]["intent"]["industry"]
        assert "## 战略洞察与机会地图" in report["markdown"]
        assert "## QA 与红队挑战" in report["markdown"]


def test_prompt_variants_keep_requested_competitors_in_scope() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/projects",
            json={
                "query": "请比较 Linear、Jira、Asana、Monday.com 在项目管理 SaaS 里的产品定位、定价和用户口碑。",
                "mode": "deep",
                "language": "zh-CN",
                "output_formats": ["markdown", "html", "json"],
                "max_competitors": 8,
                "enable_deep_review": True,
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["project_id"]
        run = client.post(f"/api/projects/{project_id}/run")
        assert run.status_code == 200, run.text

        competitors = client.get(f"/api/projects/{project_id}/competitors").json()["competitors"]
        names = {competitor["name"] for competitor in competitors}
        assert names == {"Linear", "Jira", "Asana", "Monday.com"}
        assert all({"official", "pricing", "review"}.issubset(set(competitor["source_coverage"])) for competitor in competitors)

        report = client.get(f"/api/projects/{project_id}/report").json()
        gate = report["json_report"]["agent_outputs"]["quality_gate"]["payload"]["quality_gate"]
        assert gate["relevance"]["match_ratio"] == 1.0
        assert report["quality_score"]["total"] >= 75


def test_unknown_competitors_do_not_get_overconfident_quality_score() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/projects",
            json={
                "query": "请比较 AcmeFoo、BetaBar 在垂直 SaaS 市场里的竞争格局。",
                "mode": "deep",
                "language": "zh-CN",
                "output_formats": ["markdown", "html", "json"],
                "max_competitors": 4,
                "enable_deep_review": True,
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["project_id"]
        run = client.post(f"/api/projects/{project_id}/run")
        assert run.status_code == 200, run.text

        competitors = client.get(f"/api/projects/{project_id}/competitors").json()["competitors"]
        assert {competitor["name"] for competitor in competitors} == {"AcmeFoo", "BetaBar"}

        report = client.get(f"/api/projects/{project_id}/report").json()
        gate = report["json_report"]["agent_outputs"]["quality_gate"]["payload"]["quality_gate"]
        assert gate["status"] == "needs_revision"
        assert report["quality_score"]["total"] < 70
