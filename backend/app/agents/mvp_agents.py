from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import defaultdict

from sqlalchemy import delete, select

from app.agents.base import AgentContext, BaseAgent, compact_for_storage
from app.config import should_simulate
from app.core.ids import stable_id
from app.core.time import iso_now, utc_now
from app.db.models import Chunk, Claim, Competitor, Document, Evidence, Report
from app.schemas.agent_io import (
    AnalysisOutput,
    DocumentsOutput,
    EvidenceBuilderOutput,
    ExtractionOutput,
    IntentOutput,
    PlannerOutput,
    ReportWriterOutput,
    SearchResultsOutput,
)


KNOWN_COMPETITORS = [
    "Notion AI",
    "ClickUp AI",
    "Coda AI",
    "飞书",
    "钉钉",
    "LangChain",
    "LlamaIndex",
    "Dify",
    "Flowise",
    "CrewAI",
    "AutoGen",
    "Cursor",
    "Windsurf",
    "GitHub Copilot",
    "Codeium",
    "Tabnine",
    "Mem",
    "Reflect",
    "Tana",
    "Obsidian",
    "京东",
    "阿里巴巴",
    "淘宝",
    "天猫",
    "拼多多",
    "唯品会",
    "Linear",
    "Jira",
    "Asana",
    "Monday.com",
    "Trello",
    "Basecamp",
    "Runway",
    "Pika",
    "Kling",
    "可灵",
    "Luma",
    "Synthesia",
    "HeyGen",
    "Perplexity",
    "秘塔 AI 搜索",
    "秘塔",
    "Kimi",
    "ChatGPT Search",
    "Gemini",
    "Claude",
    "联想",
    "ThinkBook",
    "小新",
    "华硕",
    "惠普",
    "戴尔",
    "荣耀",
    "机械革命",
    "宏碁",
    "小米",
    "HubSpot",
    "Salesforce",
    "Zoho CRM",
    "Pipedrive",
    "Intercom",
    "Zendesk",
    "Glean",
    "Guru",
    "Confluence",
    "SharePoint",
]

MVP_TASKS = [
    {"id": "intent", "agent": "IntentAgent", "depends_on": [], "priority": 1},
    {"id": "planner", "agent": "PlannerAgent", "depends_on": ["intent"], "priority": 2},
    {"id": "competitor_discovery", "agent": "CompetitorDiscoveryAgent", "depends_on": ["planner"], "priority": 3},
    {"id": "source_planning", "agent": "SourcePlanningAgent", "depends_on": ["competitor_discovery"], "priority": 4},
    {"id": "web_search", "agent": "WebSearchAgent", "depends_on": ["source_planning"], "priority": 5},
    {"id": "web_crawler", "agent": "WebCrawlerAgent", "depends_on": ["web_search"], "priority": 6},
    {"id": "document_cleaner", "agent": "DocumentCleanerAgent", "depends_on": ["web_crawler"], "priority": 7},
    {"id": "schema_extraction", "agent": "SchemaExtractionAgent", "depends_on": ["document_cleaner"], "priority": 8},
    {"id": "evidence_builder", "agent": "EvidenceBuilderAgent", "depends_on": ["schema_extraction"], "priority": 9},
    {"id": "product_positioning", "agent": "ProductPositioningAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "feature_matrix", "agent": "FeatureMatrixAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "pricing_analysis", "agent": "PricingAnalysisAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "user_voice", "agent": "UserVoiceAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "technology_intelligence", "agent": "TechnologyIntelligenceAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "gtm", "agent": "GTMAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "swot", "agent": "SWOTAgent", "depends_on": ["product_positioning", "feature_matrix", "pricing_analysis", "user_voice", "technology_intelligence", "gtm"], "priority": 11},
    {"id": "strategic_insight", "agent": "StrategicInsightAgent", "depends_on": ["swot"], "priority": 12},
    {"id": "analysis", "agent": "AnalysisAgent", "depends_on": ["strategic_insight"], "priority": 13},
    {"id": "fact_check", "agent": "FactCheckAgent", "depends_on": ["analysis"], "priority": 14},
    {"id": "citation_check", "agent": "CitationCheckAgent", "depends_on": ["analysis"], "priority": 14},
    {"id": "consistency_check", "agent": "ConsistencyCheckAgent", "depends_on": ["analysis"], "priority": 14},
    {"id": "bias_detection", "agent": "BiasDetectionAgent", "depends_on": ["analysis"], "priority": 14},
    {"id": "red_team", "agent": "RedTeamAgent", "depends_on": ["analysis"], "priority": 14},
    {"id": "quality_gate", "agent": "QualityGateAgent", "depends_on": ["fact_check", "citation_check", "consistency_check", "bias_detection", "red_team"], "priority": 15},
    {"id": "report_writer", "agent": "ReportWriterAgent", "depends_on": ["quality_gate"], "priority": 16},
]

REQUIRED_DIMENSIONS = [
    "product_positioning",
    "features",
    "pricing",
    "user_feedback",
    "market_strategy",
    "technical_capability",
    "risk",
    "opportunity",
]


class IntentAgent(BaseAgent):
    name = "IntentAgent"
    description = "Parse user query into a structured competitive-analysis intent."
    output_model = IntentOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        project = input_data["project"]
        query = project["query"]
        if not should_simulate(context.config):
            try:
                return await context.complete_json(
                    intent_llm_prompt(project, query),
                    self.output_schema,
                )
            except Exception:
                pass
        companies = extract_companies(query)
        if project.get("max_competitors"):
            companies = companies[: int(project["max_competitors"])]
        industry = infer_industry(query)
        topic = infer_topic(query, industry, companies)
        return {
            "analysis_topic": topic,
            "target_companies": companies,
            "industry": industry,
            "analysis_depth": project.get("mode", "quick"),
            "report_type": "competitive_analysis",
            "required_dimensions": REQUIRED_DIMENSIONS,
            "output_formats": project.get("output_formats") or ["markdown", "html", "json"],
            "needs_source_citation": True,
            "needs_competitor_confirmation": not bool(companies),
        }


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    description = "Plan the full research DAG and retry policy."
    output_model = PlannerOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        tasks = [
            {
                **task,
                "max_retries": context.config.task_default_retries,
                "human_review_required": task["id"] == "web_search"
                and input_data["dependency_outputs"].get("intent", {}).get("needs_competitor_confirmation", False),
            }
            for task in MVP_TASKS
        ]
        return {
            "dag": {
                "nodes": tasks,
                "edges": [
                    {"source": dependency, "target": task["id"]}
                    for task in tasks
                    for dependency in task["depends_on"]
                ],
                "notes": "Deep path: collection, schema extraction, parallel analysis agents, QA review and final report.",
            },
            "tasks": tasks,
        }


class WebSearchAgent(BaseAgent):
    name = "WebSearchAgent"
    description = "Collect candidate public sources for each target competitor."
    output_model = SearchResultsOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        all_outputs = collect_outputs(input_data)
        intent = all_outputs.get("intent", {})
        discovery = all_outputs.get("competitor_discovery", {}).get("payload", {})
        source_plan = all_outputs.get("source_planning", {}).get("payload", {}).get("source_plan", [])
        competitors = discovery.get("competitors") or intent.get("target_companies") or []
        if not competitors:
            competitors = [intent.get("analysis_topic") or input_data["project"]["query"]]

        all_results: list[dict] = []
        seen_urls: set[str] = set()
        plans = source_plan or [
            {"competitor": competitor, "query": f"{competitor} official product features pricing reviews", "source_type": "mixed"}
            for competitor in competitors
        ]
        for plan in plans:
            competitor = plan.get("competitor", "unknown")
            queries = [plan.get("query") or f"{competitor} official product features pricing reviews"]
            if not should_simulate(context.config):
                queries.append(f"{competitor} user reviews security integrations recent updates")
            for query in queries:
                result = await context.call_tool(
                    "web_search",
                    {
                        "query": query,
                        "competitor": competitor,
                        "source_type": plan.get("source_type", "mixed"),
                        "max_results": context.config.max_search_results_per_competitor,
                    },
                )
                for item in result.get("search_results", []):
                    if item["url"] in seen_urls:
                        continue
                    seen_urls.add(item["url"])
                    all_results.append(item)
        return {"search_results": all_results}


class WebCrawlerAgent(BaseAgent):
    name = "WebCrawlerAgent"
    description = "Fetch candidate sources and persist normalized documents."
    output_model = DocumentsOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        search_output = input_data["dependency_outputs"].get("web_search", {})
        results = select_balanced_results(search_output.get("search_results", []), context.config.max_crawl_documents)
        semaphore = asyncio.Semaphore(max(1, context.config.crawler_concurrency))

        async def crawl_result(result: dict) -> tuple[dict, dict]:
            async with semaphore:
                try:
                    crawled = await context.call_tool(
                        "web_crawler",
                        {
                            "url": result["url"],
                            "competitor": result.get("competitor", "unknown"),
                            "source_type": result.get("source_type", "unknown"),
                        },
                    )
                    return result, crawled["document"]
                except Exception as exc:
                    return result, fallback_document_from_failed_crawl(result, exc)

        crawled_documents = await asyncio.gather(*(crawl_result(result) for result in results))
        documents: list[dict] = []
        for result, document in crawled_documents:
            doc_id = stable_id("doc", context.project_id, document["url"])
            persisted = Document(
                id=doc_id,
                project_id=context.project_id,
                url=document["url"],
                title=document.get("title", ""),
                source_type=document.get("source_type", "unknown"),
                content_hash=document["content_hash"],
                content=document.get("content", ""),
                retrieved_at=utc_now(),
                doc_metadata={
                    **document.get("metadata", {}),
                    "competitor": document.get("competitor", result.get("competitor", "unknown")),
                    "search_query": result.get("query"),
                    "rank": result.get("rank"),
                },
            )
            existing = context.db.get(Document, doc_id)
            if existing:
                existing.title = persisted.title
                existing.source_type = persisted.source_type
                existing.content_hash = persisted.content_hash
                existing.content = persisted.content
                existing.retrieved_at = persisted.retrieved_at
                existing.doc_metadata = persisted.doc_metadata
            else:
                context.db.add(persisted)
            documents.append(
                {
                    "doc_id": doc_id,
                    "url": persisted.url,
                    "title": persisted.title,
                    "content": persisted.content,
                    "content_hash": persisted.content_hash,
                    "source_type": persisted.source_type,
                    "competitor": persisted.doc_metadata["competitor"],
                    "retrieved_at": iso_now(),
                    "metadata": persisted.doc_metadata,
                }
            )
        context.db.commit()
        return {"documents": documents}


class SchemaExtractionAgent(BaseAgent):
    name = "SchemaExtractionAgent"
    description = "Extract competitor schema candidates from crawled documents."
    output_model = ExtractionOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        all_outputs = collect_outputs(input_data)
        cleaned_output = all_outputs.get("document_cleaner", {}).get("payload", {})
        docs_output = all_outputs.get("web_crawler", {})
        documents = cleaned_output.get("cleaned_documents") or docs_output.get("documents", [])
        grouped: dict[str, list[dict]] = defaultdict(list)
        chunks: list[dict] = []
        for document in documents:
            grouped[document.get("competitor", "unknown")].append(document)
            for index, (start, end, text) in enumerate(chunk_text(document["content"])):
                chunk_id = stable_id("chunk", context.project_id, document["doc_id"], index)
                chunk = Chunk(
                    id=chunk_id,
                    document_id=document["doc_id"],
                    project_id=context.project_id,
                    text=text,
                    section_title=document.get("title"),
                    start_char=start,
                    end_char=end,
                    chunk_metadata={
                        "source_url": document["url"],
                        "source_type": document.get("source_type", "unknown"),
                        "competitor": document.get("competitor", "unknown"),
                    },
                )
                existing = context.db.get(Chunk, chunk_id)
                if existing:
                    existing.text = chunk.text
                    existing.section_title = chunk.section_title
                    existing.start_char = chunk.start_char
                    existing.end_char = chunk.end_char
                    existing.chunk_metadata = chunk.chunk_metadata
                else:
                    context.db.add(chunk)
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "doc_id": document["doc_id"],
                        "text": text,
                        "section_title": document.get("title"),
                        "start_char": start,
                        "end_char": end,
                        "source_url": document["url"],
                        "competitor": document.get("competitor", "unknown"),
                    }
                )

        profiles = []
        for competitor, docs in grouped.items():
            profile = build_profile(context.project_id, competitor, docs)
            competitor_id = profile["competitor_id"]
            existing_competitor = context.db.get(Competitor, competitor_id)
            if existing_competitor:
                existing_competitor.website = profile.get("website")
                existing_competitor.profile = profile
            else:
                context.db.add(
                    Competitor(
                        id=competitor_id,
                        project_id=context.project_id,
                        name=competitor,
                        website=profile.get("website"),
                        profile=profile,
                    )
                )
            profiles.append(profile)
        context.db.commit()
        return {"competitor_profiles": profiles, "chunks": chunks}


class EvidenceBuilderAgent(BaseAgent):
    name = "EvidenceBuilderAgent"
    description = "Build evidence objects from document chunks."
    output_model = EvidenceBuilderOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        context.db.execute(delete(Evidence).where(Evidence.project_id == context.project_id))
        context.db.commit()

        chunks = context.db.scalars(select(Chunk).where(Chunk.project_id == context.project_id)).all()
        documents = {
            document.id: document
            for document in context.db.scalars(select(Document).where(Document.project_id == context.project_id)).all()
        }
        evidence_items: list[dict] = []
        evidence_by_competitor: dict[str, list[str]] = defaultdict(list)
        for chunk in chunks:
            document = documents.get(chunk.document_id)
            if not document:
                continue
            source_type = chunk.chunk_metadata.get("source_type", document.source_type)
            competitor = chunk.chunk_metadata.get("competitor", "unknown")
            evidence_id = stable_id("ev", context.project_id, chunk.id)
            quote = compact_quote(chunk.text)
            evidence = Evidence(
                id=evidence_id,
                project_id=context.project_id,
                document_id=document.id,
                chunk_id=chunk.id,
                source_url=document.url,
                source_title=document.title,
                source_type=source_type,
                publisher=publisher_from_url(document.url),
                published_at=None,
                quote=quote,
                summary=summarize_text(chunk.text),
                credibility_score=credibility_score(source_type),
                freshness_score=0.25 if source_type in {"unverified", "crawl_failed"} else 0.95,
                is_primary_source=source_type in {"official", "pricing", "docs", "changelog"},
                is_potentially_outdated=document.url.startswith("offline://") or source_type in {"unverified", "crawl_failed"},
                supports_claim_ids=[],
                evidence_metadata={"competitor": competitor},
                retrieved_at=utc_now(),
            )
            context.db.add(evidence)
            evidence_by_competitor[competitor].append(evidence_id)
            evidence_items.append(evidence_to_dict(evidence))

        competitors = context.db.scalars(select(Competitor).where(Competitor.project_id == context.project_id)).all()
        for competitor in competitors:
            profile = dict(competitor.profile)
            ids = evidence_by_competitor.get(competitor.name, [])
            profile.setdefault("positioning", {})
            profile["positioning"]["evidence_ids"] = ids[:2]
            for feature in profile.get("features", []):
                feature["evidence_ids"] = ids[:2]
            for pricing in profile.get("pricing", []):
                pricing["evidence_ids"] = ids[:1]
            profile["last_updated"] = iso_now()
            competitor.profile = profile

        context.db.commit()
        return {"evidence": evidence_items}


class AnalysisAgent(BaseAgent):
    name = "AnalysisAgent"
    description = "Generate evidence-bound facts, inferences and recommendations."
    output_model = AnalysisOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        context.db.execute(delete(Claim).where(Claim.project_id == context.project_id))
        context.db.commit()

        competitors = context.db.scalars(select(Competitor).where(Competitor.project_id == context.project_id)).all()
        evidence = context.db.scalars(select(Evidence).where(Evidence.project_id == context.project_id)).all()
        all_outputs = collect_outputs(input_data)
        evidence_by_competitor: dict[str, list[str]] = defaultdict(list)
        for item in evidence:
            competitor = item.evidence_metadata.get("competitor", "unknown")
            evidence_by_competitor[competitor].append(item.id)

        claims: list[dict] = []
        feature_matrix: dict[str, dict[str, dict]] = {}
        feature_agent_matrix = all_outputs.get("feature_matrix", {}).get("payload", {}).get("feature_matrix", {})
        all_features = sorted(feature_agent_matrix.keys() or {feature["name"] for c in competitors for feature in c.profile.get("features", [])})
        for feature in all_features:
            feature_matrix[feature] = {}

        for competitor in competitors:
            profile = competitor.profile
            ev_ids = evidence_by_competitor.get(competitor.name, [])
            if ev_ids:
                fact_text = (
                    f"{competitor.name} 的当前资料显示，其公开定位与能力信号包括："
                    f"{profile.get('positioning', {}).get('short_summary', 'unknown')}"
                )
                confidence = min(0.9, 0.55 + 0.1 * len(ev_ids))
            else:
                fact_text = f"{competitor.name} 的公开资料不足，核心定位应标记为 unknown。"
                confidence = 0.1
            claims.append(
                create_claim(
                    context.project_id,
                    claim_text=fact_text,
                    claim_type="fact" if ev_ids else "unknown",
                    subject=competitor.name,
                    confidence=confidence,
                    evidence_ids=ev_ids[:3],
                    created_by=self.name,
                )
            )

            for feature in all_features:
                if feature_agent_matrix:
                    feature_matrix[feature][competitor.name] = feature_agent_matrix.get(feature, {}).get(
                        competitor.name,
                        {"support": False, "maturity": "unknown", "evidence_ids": []},
                    )
                else:
                    matched = next((item for item in profile.get("features", []) if item["name"] == feature), None)
                    feature_matrix[feature][competitor.name] = {
                        "support": bool(matched),
                        "maturity": matched.get("maturity", "unknown") if matched else "unknown",
                        "evidence_ids": matched.get("evidence_ids", []) if matched else [],
                    }

        for node_id in [
            "product_positioning",
            "pricing_analysis",
            "user_voice",
            "technology_intelligence",
            "gtm",
            "swot",
            "strategic_insight",
        ]:
            for finding in all_outputs.get(node_id, {}).get("payload", {}).get("findings", []):
                evidence_ids = finding.get("evidence_ids", [])
                claim_type = finding.get("claim_type", "inference")
                claims.append(
                    create_claim(
                        context.project_id,
                        claim_text=finding.get("claim", "unknown"),
                        claim_type=claim_type if evidence_ids else "unknown",
                        subject=finding.get("subject", "overall"),
                        confidence=finding.get("confidence", 0.5 if evidence_ids else 0.1),
                        evidence_ids=evidence_ids,
                        created_by=finding.get("created_by_agent", node_id),
                        risk_level=finding.get("risk_level", "medium"),
                    )
                )

        if evidence:
            all_ev_ids = [item.id for item in evidence[:5]]
            claims.append(
                create_claim(
                    context.project_id,
                    claim_text="基于当前证据，报告中的战略建议只能作为方向性推断，价格、认证和实时市场数据需要上线后再次刷新。",
                    claim_type="inference",
                    subject="overall",
                    confidence=0.68,
                    evidence_ids=all_ev_ids,
                    created_by=self.name,
                    risk_level="medium",
                )
            )
            claims.append(
                create_claim(
                    context.project_id,
                    claim_text="建议在进入最终商业决策前补充三类证据：实时价格页、第三方用户评价、最近三个月产品更新。",
                    claim_type="recommendation",
                    subject="research_plan",
                    confidence=0.72,
                    evidence_ids=all_ev_ids,
                    created_by=self.name,
                    risk_level="low",
                )
            )

        persisted_claims = []
        for claim in claims:
            model = Claim(
                id=claim["claim_id"],
                project_id=context.project_id,
                claim_text=claim["claim_text"],
                claim_type=claim["claim_type"],
                subject=claim["subject"],
                confidence=claim["confidence"],
                risk_level=claim["risk_level"],
                evidence_ids=claim["evidence_ids"],
                created_by_agent=claim["created_by_agent"],
                review_status=claim["review_status"],
                review_comments=claim["review_comments"],
                claim_metadata={},
            )
            context.db.add(model)
            persisted_claims.append(claim)

        for item in evidence:
            supported = [claim["claim_id"] for claim in persisted_claims if item.id in claim["evidence_ids"]]
            item.supports_claim_ids = supported

        context.db.commit()
        strategic_insights = [
            {
                "type": claim["claim_type"],
                "claim": claim["claim_text"],
                "basis": "Derived only from collected evidence; unsupported details are kept unknown.",
                "evidence_ids": claim["evidence_ids"],
                "confidence": claim["confidence"],
                "risk_level": claim["risk_level"],
            }
            for claim in persisted_claims
            if claim["claim_type"] in {"inference", "recommendation", "opportunity"}
        ]
        return {"claims": persisted_claims, "feature_matrix": feature_matrix, "strategic_insights": strategic_insights}


class ReportWriterAgent(BaseAgent):
    name = "ReportWriterAgent"
    description = "Write Markdown/HTML/JSON report with evidence appendix and quality score."
    output_model = ReportWriterOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        project = input_data["project"]
        competitors = context.db.scalars(select(Competitor).where(Competitor.project_id == context.project_id)).all()
        evidence = context.db.scalars(select(Evidence).where(Evidence.project_id == context.project_id)).all()
        claims = context.db.scalars(select(Claim).where(Claim.project_id == context.project_id)).all()
        all_outputs = collect_outputs(input_data)
        analysis = all_outputs.get("analysis", {})
        quality = all_outputs.get("quality_gate", {}).get("payload", {}).get("quality_score") or compute_quality_score(competitors, evidence, claims)
        markdown = render_markdown(project, competitors, evidence, claims, analysis, quality, all_outputs)
        llm_rewrite = {"used": False, "error": None}
        if not should_simulate(context.config):
            try:
                llm_report = await context.complete_json(
                    report_llm_prompt(project, competitors, evidence, claims, quality, markdown),
                    {
                        "type": "object",
                        "properties": {
                            "markdown": {
                                "type": "string",
                                "description": "Final evidence-bound Markdown report.",
                            }
                        },
                        "required": ["markdown"],
                        "additionalProperties": False,
                    },
                )
                markdown = validate_llm_markdown(llm_report.get("markdown"))
                llm_rewrite["used"] = True
            except Exception as exc:
                llm_rewrite["error"] = str(exc)[:500] or exc.__class__.__name__
        json_report = {
            "project_id": context.project_id,
            "summary": "Evidence-bound deep competitive intelligence report.",
            "competitors": [competitor.profile for competitor in competitors],
            "feature_matrix": analysis.get("feature_matrix", {}),
            "strategic_insights": analysis.get("strategic_insights", []),
            "agent_outputs": compact_for_storage({key: value for key, value in all_outputs.items() if key not in {"report_writer"}}),
            "claims": [claim_to_dict(claim) for claim in claims],
            "evidence": [evidence_to_dict(item) for item in evidence],
            "quality_score": quality,
            "llm_rewrite": llm_rewrite,
        }
        rendered = await context.call_tool("report_renderer", {"markdown": markdown, "json_report": json_report})

        report_id = stable_id("report", context.project_id, "markdown")
        upsert_report(context, report_id, "markdown", rendered["markdown"], {"quality_score": quality})
        upsert_report(context, stable_id("report", context.project_id, "html"), "html", rendered["html"], {"quality_score": quality})
        upsert_report(context, stable_id("report", context.project_id, "json"), "json", rendered["json"], {"quality_score": quality})
        upsert_report(
            context,
            stable_id("report", context.project_id, "ppt_outline"),
            "ppt_outline",
            render_ppt_outline(project, competitors, claims, quality),
            {"quality_score": quality},
        )
        context.db.commit()
        return {
            "report_id": report_id,
            "markdown": rendered["markdown"],
            "html": rendered["html"],
            "json_report": json_report,
            "quality_score": quality,
        }


def intent_llm_prompt(project: dict, query: str) -> str:
    return f"""
Parse the user's competitive-intelligence request into structured JSON.

User query:
{query}

Project settings:
{json.dumps(project, ensure_ascii=False)}

Rules:
- Keep explicitly requested competitors in original user order.
- Respect max_competitors.
- Use report_type="competitive_analysis".
- Use output_formats from project settings, or ["markdown", "html", "json"].
- required_dimensions must include: {json.dumps(REQUIRED_DIMENSIONS, ensure_ascii=False)}.
- needs_source_citation must be true.
- needs_competitor_confirmation is true only when no target companies can be identified.
"""


def report_llm_prompt(project: dict, competitors: list[Competitor], evidence: list[Evidence], claims: list[Claim], quality: dict, markdown: str) -> str:
    competitor_payload = [
        {
            "name": competitor.name,
            "positioning": competitor.profile.get("positioning", {}),
            "features": competitor.profile.get("features", [])[:6],
            "pricing": competitor.profile.get("pricing", [])[:3],
            "source_coverage": competitor.profile.get("source_coverage", []),
        }
        for competitor in competitors
    ]
    claim_payload = [claim_to_dict(claim) for claim in claims[:18]]
    evidence_payload = [
        {
            "evidence_id": item.id,
            "source_url": item.source_url,
            "source_type": item.source_type,
            "quote": item.quote[:240],
            "summary": item.summary[:160],
            "competitor": item.evidence_metadata.get("competitor", "unknown"),
        }
        for item in evidence[:20]
    ]
    return f"""
Rewrite the existing Markdown report into a polished product-manager-facing competitive intelligence report.

Hard constraints:
- Return JSON with a single key: markdown.
- Use the project language: {project.get("language", "zh-CN")}.
- Preserve evidence traceability. Use only evidence_ids that appear below; never invent evidence IDs, URLs, claims, prices, certifications, or dates.
- Keep unsupported or volatile facts cautious and mark them as needing live verification.
- Keep these report sections where applicable: 执行摘要, 事实结论, 功能矩阵, SWOT 摘要, 战略洞察与机会地图, QA 与红队挑战, 证据附录.
- Do not include Markdown code fences around the report.

Project:
{json.dumps(project, ensure_ascii=False)}

Competitors:
{json.dumps(competitor_payload, ensure_ascii=False)}

Claims:
{json.dumps(claim_payload, ensure_ascii=False)}

Evidence:
{json.dumps(evidence_payload, ensure_ascii=False)}

Quality score:
{json.dumps(quality, ensure_ascii=False)}

Current deterministic draft:
{markdown[:8000]}
"""


def validate_llm_markdown(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("LLM report response must contain a non-empty markdown string.")
    return value.strip()


def extract_companies(query: str) -> list[str]:
    known = ordered_known_competitor_matches(query)
    parsed = parse_delimited_competitors(query)
    return dedupe_companies([*known, *parsed])[:20]


def ordered_known_competitor_matches(query: str) -> list[str]:
    matches: list[tuple[int, int, str]] = []
    lower_query = query.lower()
    for name in KNOWN_COMPETITORS:
        lower_name = name.lower()
        start = lower_query.find(lower_name)
        if start >= 0:
            matches.append((start, start + len(name), name))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    accepted: list[tuple[int, int, str]] = []
    for start, end, name in matches:
        if any(max(start, used_start) < min(end, used_end) for used_start, used_end, _ in accepted):
            continue
        accepted.append((start, end, name))
    return [name for _, _, name in sorted(accepted, key=lambda item: item[0])]


def parse_delimited_competitors(query: str) -> list[str]:
    segments = []
    patterns = [
        r"(?:包括|包含|涵盖|对比|比较|监控)\s*([^。；\n]+)",
        r"(?:分析|研究|调研|评估)\s+([^。；\n]+?)(?:\s+在|在\s*|于\s*|的竞争|竞争格局|领域|市场|赛道|并|，并|, and|。|；|\n|$)",
    ]
    for pattern in patterns:
        segments.extend(match.group(1) for match in re.finditer(pattern, query, flags=re.I))
    if not segments and re.search(r"[、,/，]", query[:100]):
        segments.append(query[:120])

    candidates: list[str] = []
    for segment in segments:
        segment = re.split(r"(?:\s+在|在\s*|于\s*|的竞争|竞争格局|领域|市场|赛道|重点|并生成|生成|给我|。|；)", segment, maxsplit=1)[0]
        if not re.search(r"[、,，/]|(?:\s+和\s+)|(?:\s+与\s+)|(?:\s+and\s+)", segment, flags=re.I):
            continue
        tokens = re.split(r"[、,，/]|(?:\s+和\s+)|(?:\s+与\s+)|(?:\s+and\s+)", segment, flags=re.I)
        for token in tokens:
            cleaned = clean_company_token(token)
            if cleaned and is_plausible_company_name(cleaned):
                candidates.append(cleaned)
    return candidates


def clean_company_token(token: str) -> str:
    value = token.strip(" \t\n\r:：；;，,。")
    value = re.sub(r"^(?:请|帮我|请帮我|我想|想|分析|比较|对比|研究|调研|评估|监控)\s*", "", value)
    value = re.sub(r"(?:等平台|等产品|等工具|等竞品|等公司|等项目|等|平台|产品|工具|竞品)$", "", value).strip()
    contextual = re.search(r"(?:产品|工具|平台|公司|竞品|玩家)\s+([A-Za-z][A-Za-z0-9 .+_-]{1,48})$", value)
    if contextual:
        value = contextual.group(1).strip()
    value = re.sub(r"^(?:国内外|全球|主要|核心|头部|海外|国内|开源|商业化|AI|人工智能)\s+", "", value, flags=re.I)
    return value.strip(" \t\n\r:：；;，,。")


def is_plausible_company_name(value: str) -> bool:
    if not (1 < len(value) <= 48):
        return False
    bad_terms = ["领域", "市场", "赛道", "视角", "报告", "格局", "不指定", "竞品分析", "价格", "用户口碑"]
    if any(term in value for term in bad_terms):
        return False
    if re.fullmatch(r"(AI|SaaS|CRM|Agent|产品经理|投资人|技术)", value, flags=re.I):
        return False
    return bool(re.search(r"[A-Za-z0-9\u4e00-\u9fff]", value))


def dedupe_companies(names: list[str]) -> list[str]:
    normalized_aliases = {"可灵": "Kling", "秘塔": "秘塔 AI 搜索"}
    result: list[str] = []
    seen: set[str] = set()
    for name in names:
        value = normalized_aliases.get(name, name).strip()
        key = re.sub(r"\s+", " ", value.lower())
        if not key or key in seen:
            continue
        if any(key in existing or existing in key for existing in seen if len(key) > 2):
            continue
        seen.add(key)
        result.append(value)
    return result


def infer_industry(query: str) -> str:
    lower = query.lower()
    if any(keyword in query for keyword in ["笔记本", "电脑", "轻薄本", "游戏本", "全能本"]) or any(keyword in lower for keyword in ["laptop", "notebook"]):
        return "laptop computer / consumer electronics"
    if "Agent" in query or "agent" in query:
        return "AI Agent infrastructure / development platform"
    if "视频" in query or "video" in lower or "生成工具" in query:
        return "AI video generation / creative tools"
    if "搜索" in query or "search" in lower:
        return "AI search / answer engine"
    if "项目管理" in query or "project management" in lower:
        return "project management / work management SaaS"
    if "CRM" in query.upper() or "客户关系" in query or "销售" in query:
        return "CRM / customer engagement software"
    if "网购" in query or "电商" in query or "零售" in query or "e-commerce" in lower:
        return "e-commerce / online retail platform"
    if "办公" in query or "协作" in query or "productivity" in lower:
        return "AI productivity / collaboration software"
    if "知识库" in query:
        return "AI knowledge base / knowledge management"
    if "代码" in query or "coding" in lower:
        return "AI coding assistant"
    return "unknown"


def infer_topic(query: str, industry: str, companies: list[str]) -> str:
    if companies:
        return f"{industry} 竞品分析：{', '.join(companies)}"
    return f"{industry} 竞品分析"


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 80) -> list[tuple[int, int, str]]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append((start, end, text[start:end].strip()))
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def select_balanced_results(results: list[dict], max_documents: int) -> list[dict]:
    if len(results) <= max_documents:
        return results
    grouped: dict[str, list[dict]] = defaultdict(list)
    for result in results:
        grouped[result.get("competitor", "unknown")].append(result)
    competitor_count = max(1, len(grouped))
    per_competitor = max(3, max_documents // competitor_count)
    selected: list[dict] = []
    for competitor in sorted(grouped):
        selected.extend(grouped[competitor][:per_competitor])
    if len(selected) < max_documents:
        selected_urls = {item["url"] for item in selected}
        for result in results:
            if result["url"] not in selected_urls:
                selected.append(result)
            if len(selected) >= max_documents:
                break
    return selected[:max_documents]


def fallback_document_from_failed_crawl(result: dict, exc: Exception) -> dict:
    competitor = result.get("competitor", "unknown")
    url = result.get("url", "unknown")
    content = (
        f"Crawl failed for {url}. The source was discovered for {competitor}, but its content could not be fetched "
        f"during this run. Error: {exc}. Treat any claim that depends on this source as unverified and request "
        "a retry or alternative source."
    )
    return {
        "url": url,
        "title": result.get("title") or f"{competitor} crawl failed",
        "content": content,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "source_type": "crawl_failed",
        "competitor": competitor,
        "retrieved_at": iso_now(),
        "metadata": {"crawl_error": str(exc), "search_query": result.get("query"), "rank": result.get("rank")},
    }


def build_profile(project_id: str, competitor: str, docs: list[dict]) -> dict:
    combined = "\n".join(doc["content"] for doc in docs)
    source_urls = [doc["url"] for doc in docs]
    source_types = {doc.get("source_type", "unknown") for doc in docs}
    features = extract_features(project_id, competitor, combined)
    pricing = extract_pricing(project_id, combined, bool(source_types & {"pricing"}))
    return {
        "competitor_id": stable_id("comp", project_id, competitor),
        "name": competitor,
        "aliases": [],
        "company_name": competitor.replace(" AI", ""),
        "website": next((url for url in source_urls if not url.startswith("offline://")), source_urls[0] if source_urls else None),
        "founded_year": None,
        "headquarters": None,
        "company_stage": "unknown",
        "product_category": infer_product_category(combined),
        "target_users": infer_target_users(combined),
        "target_industries": [],
        "regions": [],
        "business_model": infer_business_model(combined),
        "positioning": {
            "short_summary": summarize_text(combined),
            "long_summary": summarize_text(combined, max_len=520),
            "evidence_ids": [],
        },
        "features": features,
        "pricing": pricing,
        "integrations": extract_integrations(combined),
        "security_compliance": extract_security(combined),
        "user_feedback": extract_user_feedback(combined),
        "market_signals": extract_market_signals(combined),
        "technical_signals": extract_technical_signals(combined),
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
        "source_coverage": sorted(source_types),
        "last_updated": iso_now(),
    }


def extract_features(project_id: str, competitor: str, text: str) -> list[dict]:
    lowered = text.lower()
    candidates = [
        ("AI writing", "ai", ["writing", "生成", "assistant", "summarization", "summarizing"]),
        ("Knowledge base", "collaboration", ["knowledge", "wiki", "知识库", "workspace"]),
        ("Database / tables", "core", ["database", "tables", "数据库", "表格"]),
        ("Workflow automation", "automation", ["automation", "workflow", "流程", "automations"]),
        ("API / extensibility", "platform", ["api", "sdk", "packs", "open platform", "开放平台"]),
        ("Enterprise controls", "security", ["sso", "permission", "security", "enterprise", "权限", "管理后台"]),
        ("Project management", "collaboration", ["tasks", "project", "项目"]),
        ("RAG / retrieval", "ai", ["rag", "retrieval", "问答"]),
        ("Agent workflows", "ai", ["agent", "agents"]),
        ("Self-operated retail", "commerce", ["自营", "零售差价", "综合电商"]),
        ("Marketplace merchants", "commerce", ["商家", "开放平台", "招商", "佣金", "店铺"]),
        ("Logistics fulfillment", "operations", ["物流", "履约", "仓配", "配送"]),
        ("Traffic and advertising", "growth", ["广告", "营销", "流量", "直播"]),
        ("Subsidy / low-price engine", "pricing", ["低价", "补贴", "百亿补贴", "性价比", "团购"]),
        ("Brand discount retail", "commerce", ["品牌特卖", "折扣", "限时特卖"]),
        ("Membership / retention", "growth", ["会员", "复购", "用户心智"]),
        ("Timeline / task planning", "project_management", ["project management", "任务", "issue", "sprint", "roadmap", "timeline", "kanban"]),
        ("AI video generation", "creative_ai", ["video", "视频", "text-to-video", "生成视频", "motion"]),
        ("AI search answers", "search", ["search", "搜索", "answer engine", "citation", "答案"]),
        ("Sales pipeline", "crm", ["crm", "pipeline", "sales", "销售线索", "客户"]),
        ("Customer support automation", "customer_engagement", ["support", "客服", "工单", "ticket", "conversation"]),
    ]
    features = []
    for name, category, keywords in candidates:
        if any(keyword.lower() in lowered for keyword in keywords):
            features.append(
                {
                    "feature_id": stable_id("feat", project_id, competitor, name),
                    "name": name,
                    "category": category,
                    "description": f"Evidence text contains public signals for {name}.",
                    "support_status": "yes",
                    "maturity": "medium",
                    "evidence_ids": [],
                }
            )
    return features or [
        {
            "feature_id": stable_id("feat", project_id, competitor, "unknown"),
            "name": "unknown",
            "category": "unknown",
            "description": "No feature signal extracted from current evidence.",
            "support_status": "unknown",
            "maturity": "unknown",
            "evidence_ids": [],
        }
    ]


def extract_pricing(project_id: str, text: str, has_pricing_source: bool) -> list[dict]:
    if not has_pricing_source and not re.search(r"price|pricing|价格|paid|free|enterprise|佣金|广告|会员|差价|费用", text, re.I):
        return []
    price = "unknown"
    if re.search(r"佣金|广告|物流|差价|会员", text):
        price = "multi-revenue: commission / ads / logistics / membership signals"
    return [
        {
            "plan_name": "public pricing signal",
            "price": price,
            "currency": None,
            "billing_cycle": "unknown",
            "target_segment": "unknown",
            "included_features": [],
            "limitations": ["Exact live price must be verified from current pricing source."],
            "evidence_ids": [],
        }
    ]


def infer_target_users(text: str) -> list[str]:
    lowered = text.lower()
    users = []
    if "teams" in lowered or "team" in lowered or "团队" in text:
        users.append("teams")
    if "enterprise" in lowered or "企业" in text:
        users.append("enterprise")
    if "developer" in lowered or "开发" in text:
        users.append("developers")
    if "商家" in text:
        users.append("merchants")
    if "消费者" in text or "用户" in text or "消费" in text:
        users.append("consumers")
    if "品牌" in text:
        users.append("brands")
    return users or ["unknown"]


def infer_business_model(text: str) -> list[str]:
    lowered = text.lower()
    models = []
    if "free" in lowered or "免费" in text:
        models.append("freemium")
    if "paid" in lowered or "pricing" in lowered or "价格" in text:
        models.append("subscription")
    if "enterprise" in lowered or "企业" in text:
        models.append("enterprise")
    if "open-source" in lowered or "github" in lowered:
        models.append("open_source")
    if "佣金" in text:
        models.append("marketplace")
    if "广告" in text or "营销" in text:
        models.append("advertising")
    if "物流" in text:
        models.append("logistics_service")
    if "会员" in text:
        models.append("membership")
    if "自营" in text or "差价" in text:
        models.append("first_party_retail")
    return models or ["unknown"]


def extract_integrations(text: str) -> list[dict]:
    lowered = text.lower()
    integrations = []
    if "api" in lowered:
        integrations.append({"name": "API", "type": "api", "evidence_ids": []})
    if "packs" in lowered or "plugin" in lowered or "插件" in text:
        integrations.append({"name": "Plugin / pack ecosystem", "type": "plugin", "evidence_ids": []})
    return integrations


def extract_security(text: str) -> list[dict]:
    lowered = text.lower()
    items = []
    if "sso" in lowered:
        items.append({"item": "SSO", "status": "yes", "evidence_ids": []})
    if "permission" in lowered or "权限" in text:
        items.append({"item": "permission_controls", "status": "yes", "evidence_ids": []})
    if "security" in lowered or "安全" in text:
        items.append({"item": "security", "status": "partial", "evidence_ids": []})
    return items


def extract_user_feedback(text: str) -> dict:
    if "review" not in text.lower() and "用户" not in text and "negative" not in text.lower() and "反馈" not in text:
        return {"pros": [], "cons": []}
    return {
        "pros": [
            {"theme": "positive demand signal", "summary": "Positive review or user-mindshare signal found.", "frequency": None, "sentiment": "positive", "evidence_ids": []}
        ],
        "cons": [
            {"theme": "experience or verification risk", "summary": "Negative or cautionary review signal found.", "frequency": None, "sentiment": "negative", "evidence_ids": []}
        ],
    }


def extract_technical_signals(text: str) -> list[dict]:
    lowered = text.lower()
    signals = []
    for signal_type, keyword in [("api", "api"), ("agent", "agent"), ("rag", "rag"), ("workflow", "workflow"), ("open_source", "github")]:
        if keyword in lowered:
            signals.append(
                {
                    "signal_type": signal_type,
                    "description": f"Current evidence contains a {signal_type} signal.",
                    "confidence": 0.6,
                    "evidence_ids": [],
                }
            )
    return signals


def infer_product_category(text: str) -> str:
    if re.search(r"video|视频|text-to-video|生成视频|creative", text, re.I):
        return "AI video generation / creative tools"
    if re.search(r"search|搜索|answer engine|答案|citation", text, re.I):
        return "AI search / answer engine"
    if re.search(r"project management|roadmap|issue|sprint|kanban|项目管理", text, re.I):
        return "project management / work management SaaS"
    if re.search(r"crm|sales|pipeline|客户|销售", text, re.I):
        return "CRM / customer engagement software"
    if re.search(r"电商|零售|商家|物流|特卖|补贴|平台佣金", text):
        return "e-commerce / retail platform"
    if re.search(r"docs|workspace|知识库|协同办公|documents|project", text, re.I):
        return "AI productivity / collaboration software"
    if re.search(r"LLM|agent|RAG|GitHub|workflow", text, re.I):
        return "AI application infrastructure"
    return "unknown"


def extract_market_signals(text: str) -> list[dict]:
    signals = []
    for signal_type, keyword, description in [
        ("customer_case", "企业", "Enterprise/customer signal appears in evidence."),
        ("community_growth", "商家生态", "Merchant ecosystem signal appears in evidence."),
        ("launch", "即时零售", "New retail or scenario expansion signal appears in evidence."),
        ("media_coverage", "用户心智", "User mindshare signal appears in evidence."),
        ("partnership", "品牌", "Brand partnership or brand-retail signal appears in evidence."),
    ]:
        if keyword in text:
            signals.append({"signal_type": signal_type, "description": description, "date": None, "evidence_ids": []})
    return signals


def collect_outputs(input_data: dict) -> dict:
    outputs = dict(input_data.get("memory", {}))
    outputs.update(input_data.get("dependency_outputs", {}))
    return outputs


def credibility_score(source_type: str) -> float:
    return {
        "official": 0.9,
        "pricing": 0.88,
        "docs": 0.86,
        "github": 0.82,
        "review": 0.7,
        "news": 0.72,
        "changelog": 0.8,
        "third_party": 0.65,
        "unverified": 0.25,
        "crawl_failed": 0.15,
    }.get(source_type, 0.5)


def publisher_from_url(url: str) -> str | None:
    if url.startswith("offline://"):
        return "offline_fixture"
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1) if match else None


def compact_quote(text: str, max_len: int = 520) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def summarize_text(text: str, max_len: int = 240) -> str:
    text = compact_quote(text, max_len=max_len)
    return text if text else "unknown"


def create_claim(
    project_id: str,
    claim_text: str,
    claim_type: str,
    subject: str,
    confidence: float,
    evidence_ids: list[str],
    created_by: str,
    risk_level: str = "low",
) -> dict:
    return {
        "claim_id": stable_id("claim", project_id, claim_text),
        "claim_text": claim_text,
        "claim_type": claim_type,
        "subject": subject,
        "confidence": round(confidence, 2),
        "risk_level": risk_level,
        "evidence_ids": evidence_ids,
        "created_by_agent": created_by,
        "review_status": "approved" if evidence_ids or claim_type == "unknown" else "needs_revision",
        "review_comments": [] if evidence_ids else ["No supporting evidence; keep as unknown or low confidence."],
    }


def claim_to_dict(claim: Claim) -> dict:
    return {
        "claim_id": claim.id,
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "subject": claim.subject,
        "confidence": claim.confidence,
        "risk_level": claim.risk_level,
        "evidence_ids": claim.evidence_ids,
        "created_by_agent": claim.created_by_agent,
        "review_status": claim.review_status,
        "review_comments": claim.review_comments,
    }


def evidence_to_dict(evidence: Evidence) -> dict:
    return {
        "evidence_id": evidence.id,
        "source_url": evidence.source_url,
        "source_title": evidence.source_title,
        "source_type": evidence.source_type,
        "publisher": evidence.publisher,
        "published_at": evidence.published_at,
        "retrieved_at": evidence.retrieved_at.isoformat() if hasattr(evidence.retrieved_at, "isoformat") else str(evidence.retrieved_at),
        "doc_id": evidence.document_id,
        "chunk_id": evidence.chunk_id,
        "quote": evidence.quote,
        "summary": evidence.summary,
        "credibility_score": evidence.credibility_score,
        "freshness_score": evidence.freshness_score,
        "is_primary_source": evidence.is_primary_source,
        "is_potentially_outdated": evidence.is_potentially_outdated,
        "supports_claim_ids": evidence.supports_claim_ids,
        "metadata": evidence.evidence_metadata,
    }


def compute_quality_score(competitors: list[Competitor], evidence: list[Evidence], claims: list[Claim]) -> dict:
    competitor_count = max(1, len(competitors))
    verified_evidence = [item for item in evidence if item.source_type not in {"unverified", "crawl_failed"} and item.credibility_score >= 0.35]
    verified_ids = {item.id for item in verified_evidence}
    coverage_ratio = min(1.0, len(verified_evidence) / (competitor_count * 3))
    evidence_ratio = sum(1 for claim in claims if any(evidence_id in verified_ids for evidence_id in claim.evidence_ids)) / max(1, len(claims))
    citation_accuracy = 1.0 if all(claim.evidence_ids or claim.claim_type == "unknown" for claim in claims) else 0.5
    analysis_depth = min(1.0, len(claims) / max(1, competitor_count + 2)) * (len(verified_evidence) / max(1, len(evidence)))
    consistency = 1.0 if not any(claim.claim_type != "unknown" and not claim.evidence_ids for claim in claims) else 0.6
    score = {
        "coverage": round(20 * coverage_ratio),
        "evidence_strength": round(20 * evidence_ratio),
        "citation_accuracy": round(15 * citation_accuracy),
        "analysis_depth": round(15 * analysis_depth),
        "structure": 9,
        "consistency": round(10 * consistency),
        "readability": 4,
        "novelty": 3,
    }
    score["total"] = sum(score.values())
    return score


def render_markdown(
    project: dict,
    competitors: list[Competitor],
    evidence: list[Evidence],
    claims: list[Claim],
    analysis: dict,
    quality: dict,
    agent_outputs: dict | None = None,
) -> str:
    agent_outputs = agent_outputs or {}
    quality_gate = agent_outputs.get("quality_gate", {}).get("payload", {})
    red_team = agent_outputs.get("red_team", {}).get("payload", {})
    bias = agent_outputs.get("bias_detection", {}).get("payload", {})
    swot = agent_outputs.get("swot", {}).get("payload", {})
    strategic = agent_outputs.get("strategic_insight", {}).get("payload", {})
    project_id = project.get("project_id", "")
    lines = [
        f"# CompeteScope AI 竞品分析报告",
        "",
        f"**分析任务**：{project['query']}",
        "",
        f"**生成方式**：深度 DAG 自动生成，包含多 Agent 并行分析、证据绑定、红队挑战和质量门禁。",
        "",
        "## 执行摘要",
        "",
        f"- 已结构化竞品：{len(competitors)} 个。",
        f"- 已构建证据：{len(evidence)} 条。",
        f"- 质量评分：{quality['total']}/100。",
        f"- 交付状态：{quality_gate.get('status', 'pass_with_warnings')}。",
        "",
        "## 一页结论",
        "",
    ]
    top_claims = [claim for claim in claims if claim.claim_type in {"inference", "recommendation", "opportunity"}][:6]
    lines.extend(render_claim_lines(top_claims, project_id))
    lines.extend([
        "## 事实结论",
        "",
    ])
    facts = [claim for claim in claims if claim.claim_type in {"fact", "unknown"}]
    lines.extend(render_claim_lines(facts, project_id))
    lines.extend(["", "## 推断", ""])
    lines.extend(render_claim_lines([claim for claim in claims if claim.claim_type == "inference"], project_id))
    lines.extend(["", "## 建议", ""])
    lines.extend(render_claim_lines([claim for claim in claims if claim.claim_type == "recommendation"], project_id))
    lines.extend(["", "## 战略洞察与机会地图", ""])
    for insight in strategic.get("strategic_insights", []):
        lines.append(
            f"- **{insight.get('type', 'insight')}**：{insight.get('claim', 'unknown')} "
            f"[confidence: {insight.get('confidence', 0):.2f}; risk: {insight.get('risk_level', 'medium')}; "
            f"证据: {citation_list(insight.get('evidence_ids', []), project_id)}]"
        )
    if not strategic.get("strategic_insights"):
        lines.append("- unknown：当前证据不足以形成额外战略洞察。")
    lines.extend(["", "## 竞品知识库摘要", ""])
    for competitor in competitors:
        profile = competitor.profile
        feature_names = ", ".join(feature["name"] for feature in profile.get("features", [])[:8]) or "unknown"
        pricing = profile.get("pricing", [])
        pricing_text = pricing[0]["price"] if pricing else "unknown"
        lines.extend(
            [
                f"### {competitor.name}",
                "",
                f"- 定位：{profile.get('positioning', {}).get('short_summary', 'unknown')} "
                f"[证据: {citation_list(profile.get('positioning', {}).get('evidence_ids', []), project_id)}]",
                f"- 功能信号：{feature_names}",
                f"- 价格信号：{pricing_text}",
                f"- 信息源覆盖：{', '.join(profile.get('source_coverage', [])) or 'unknown'}",
                "",
            ]
        )
    lines.extend(["## 功能矩阵", ""])
    feature_matrix = analysis.get("feature_matrix", {})
    competitor_names = [competitor.name for competitor in competitors]
    if feature_matrix and competitor_names:
        lines.append("| 功能 | " + " | ".join(competitor_names) + " |")
        lines.append("|---|" + "|".join("---" for _ in competitor_names) + "|")
        for feature, values in feature_matrix.items():
            cells = []
            for competitor in competitor_names:
                item = values.get(competitor, {})
                evidence_ids = item.get("evidence_ids", [])
                cells.append(("支持" if item.get("support") else "unknown") + (f" ({citation_list(evidence_ids, project_id)})" if evidence_ids else ""))
            lines.append("| " + feature + " | " + " | ".join(cells) + " |")
    else:
        lines.append("当前证据不足，功能矩阵为 unknown。")
    lines.extend(["", "## SWOT 摘要", ""])
    swot_items = swot.get("swot", {})
    for competitor in competitors:
        block = swot_items.get(competitor.name, {})
        lines.append(f"### {competitor.name}")
        for label, key in [("Strengths", "strengths"), ("Weaknesses", "weaknesses"), ("Opportunities", "opportunities"), ("Threats", "threats")]:
            values = block.get(key, [])
            text = "; ".join(
                f"{item.get('point', 'unknown')} ({citation_list(item.get('evidence_ids', []), project_id)})"
                for item in values[:3]
            ) or "unknown"
            lines.append(f"- {label}: {text}")
        lines.append("")
    lines.extend(["## QA 与红队挑战", ""])
    for warning in quality_gate.get("warnings", []):
        lines.append(f"- 质量门禁警告：{warning}")
    for challenge in red_team.get("red_team_challenges", []):
        lines.append(
            f"- 红队挑战：{challenge.get('challenge')} | severity={challenge.get('severity')} | fix={challenge.get('suggested_fix')}"
        )
    for item in bias.get("bias_report", []):
        lines.append(f"- 偏差提示：{item.get('description')} 建议：{item.get('recommendation')}")
    if not quality_gate.get("warnings") and not red_team.get("red_team_challenges") and not bias.get("bias_report"):
        lines.append("- 暂无高风险 QA 问题。")
    lines.extend(
        [
            "",
            "## 质量评分",
            "",
            "| 维度 | 分数 |",
            "|---|---:|",
            f"| 信息覆盖度 | {quality['coverage']}/20 |",
            f"| 证据充分性 | {quality['evidence_strength']}/20 |",
            f"| 引用准确性 | {quality['citation_accuracy']}/15 |",
            f"| 分析深度 | {quality['analysis_depth']}/15 |",
            f"| 结构化程度 | {quality['structure']}/10 |",
            f"| 逻辑一致性 | {quality['consistency']}/10 |",
            f"| 可读性 | {quality['readability']}/5 |",
            f"| 新颖洞察 | {quality['novelty']}/5 |",
            "",
            "## 引用来源",
            "",
        ]
    )
    for item in evidence:
        lines.append(
            f"- `{item.id}`: [{item.source_title}]({item.source_url}) | "
            f"可信度 {item.credibility_score:.2f} | 新鲜度 {item.freshness_score:.2f} | 摘要：{item.summary}"
        )
    lines.extend(
        [
            "",
            "## Agent 执行说明",
            "",
            "本报告由 IntentAgent、PlannerAgent、采集/清洗/抽取 Agent、多维分析 Agent、QA Agent、RedTeamAgent、QualityGateAgent 和 ReportWriterAgent 生成。"
            "MVP 默认使用离线 fixture 以便本地稳定测试；生产模式应配置合规搜索 API，并保持 robots.txt 检查、速率限制和访问控制合规。",
        ]
    )
    return "\n".join(lines)


def render_claim_lines(claims: list[Claim], project_id: str = "") -> list[str]:
    if not claims:
        return ["- unknown：当前没有足够证据生成该类结论。"]
    lines = []
    for claim in claims:
        evidence_text = citation_list(claim.evidence_ids, project_id)
        lines.append(
            f"- **{claim.claim_type}**：{claim.claim_text} "
            f"[confidence: {claim.confidence:.2f}; risk: {claim.risk_level}; 证据: {evidence_text}]"
        )
    return lines


def render_ppt_outline(project: dict, competitors: list[Competitor], claims: list[Claim], quality: dict) -> str:
    insight_claims = [claim for claim in claims if claim.claim_type in {"inference", "recommendation", "opportunity"}][:5]
    fact_claims = [claim for claim in claims if claim.claim_type == "fact"][:5]
    lines = [
        "# PPT 大纲：CompeteScope AI 竞品分析",
        "",
        "## Slide 1: 任务与范围",
        f"- 任务：{project['query']}",
        f"- 竞品数量：{len(competitors)}",
        f"- 质量评分：{quality['total']}/100",
        "",
        "## Slide 2: 竞品版图",
        *[f"- {competitor.name}: {competitor.profile.get('positioning', {}).get('short_summary', 'unknown')}" for competitor in competitors[:8]],
        "",
        "## Slide 3: 关键事实",
        *[f"- {claim.claim_text} ({', '.join(claim.evidence_ids) or 'unknown'})" for claim in fact_claims],
        "",
        "## Slide 4: 机会与风险",
        *[f"- {claim.claim_text} | confidence={claim.confidence:.2f}" for claim in insight_claims],
        "",
        "## Slide 5: 推荐行动",
        "- 补充最新价格、第三方评价和最近 90 天产品更新。",
        "- 对低置信度结论降级展示，避免作为强事实进入决策。",
    ]
    return "\n".join(lines)


def citation_list(evidence_ids: list[str], project_id: str = "") -> str:
    if not evidence_ids:
        return "unknown"
    if not project_id:
        return ", ".join(evidence_ids)
    return ", ".join(f"[{evidence_id}](/projects/{project_id}/evidence/{evidence_id})" for evidence_id in evidence_ids)


def upsert_report(context: AgentContext, report_id: str, format_: str, content: str, metadata: dict) -> None:
    existing = context.db.get(Report, report_id)
    if existing:
        existing.content = content
        existing.report_metadata = metadata
    else:
        context.db.add(
            Report(
                id=report_id,
                project_id=context.project_id,
                format=format_,
                content=content,
                report_metadata=metadata,
            )
        )
