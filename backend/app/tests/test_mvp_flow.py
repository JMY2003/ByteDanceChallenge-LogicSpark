import os
from pathlib import Path

os.environ["COMPETESCOPE_DATABASE_URL"] = "sqlite:///./test_competescope.db"

import app.config as app_config
from app.config import get_settings

app_config.SIMULATIVE = True
get_settings.cache_clear()

TEST_DB = Path("test_competescope.db")
if TEST_DB.exists():
    TEST_DB.unlink()

from fastapi.testclient import TestClient

from app.main import app
from app.agents.specialized_agents import (
    competitor_discovery_prompt,
    extract_price_segment_hint,
    has_unreleased_or_unverified_currentness_signal,
    market_discovery_query,
    should_include_context_benchmark,
    should_refine_for_currentness,
)


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
        assert "## 竞品对比表" in body["markdown"]
        assert "## 证据质量与风险" in body["markdown"]
        assert "ev_" in body["markdown"]
        assert body["html"]
        assert body["json_report"]["claims"]
        assert body["json_report"]["agent_outputs"]["quality_gate"]["payload"]["quality_score"]
        assert body["quality_score"]["total"] >= 70

        runs = client.get(f"/api/projects/{project_id}/agent-runs")
        assert runs.status_code == 200
        agent_names = {run["agent_name"] for run in runs.json()}
        assert len(runs.json()) >= 11
        assert "DocumentCleanerAgent" not in agent_names
        assert "EvidenceBuilderAgent" in agent_names


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
        assert "## 关键结论" in report["markdown"]
        assert "## 下一步验证清单" in report["markdown"]


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


def test_auto_discovery_prompt_requires_current_products() -> None:
    project = {
        "query": "任务模式：AI发现竞品。品类：6000元价位档手机。竞品数量：5。其他说明：关注影像、续航、性能。",
        "max_competitors": 5,
    }
    intent = {"industry": "smartphone / consumer electronics", "target_companies": []}
    prompt = competitor_discovery_prompt(
        project,
        intent,
        5,
        [{"title": "2026 手机选购", "snippet": "6000元价位最新旗舰手机对比", "url": "https://example.com"}],
    )

    assert "Current date" in prompt
    assert "currently sold" in prompt
    assert "Do not select stale models" in prompt
    assert "Do not select rumored" in prompt
    assert "Live market/search context" in prompt
    assert should_refine_for_currentness(project, intent, ["华为 Mate 60 Pro", "小米 14 Pro"])
    discovery_query = market_discovery_query(project, intent)
    assert "2026年" in discovery_query
    assert "5000-6000元" in discovery_query
    assert "最新在售" in discovery_query
    assert extract_price_segment_hint(project["query"]) == "5000-6000元 6000元价位"
    assert has_unreleased_or_unverified_currentness_signal(
        [{"name": "Example X", "reason": "expected current generation, launch imminent"}]
    )
    assert should_include_context_benchmark(
        project,
        intent,
        [{"title": "5000-6000元手机推荐", "snippet": "小米17 Pro Max、OPPO Find X9 Pro、Apple iPhone 17 等"}],
        ["小米17 Pro Max", "OPPO Find X9 Pro", "vivo X300 Pro", "荣耀Magic8 Pro", "华为Mate70"],
    )


def test_historical_product_tasks_do_not_force_currentness() -> None:
    project = {
        "query": "请复盘 2023 年旗舰手机竞争格局，包括当年的代表机型。",
        "max_competitors": 5,
    }
    intent = {"industry": "smartphone / consumer electronics", "target_companies": []}

    assert not should_refine_for_currentness(project, intent, ["华为 Mate 60 Pro", "小米 14 Pro"])
