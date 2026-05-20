from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Any

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
    "MacBook Air",
    "MacBook Pro",
    "联想小新",
    "华硕无畏",
    "华硕灵耀",
    "惠普战66",
    "惠普星Book",
    "戴尔灵越",
    "荣耀MagicBook",
    "机械革命无界",
    "Acer Swift",
    "宏碁非凡",
    "小米 RedmiBook",
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

CORE_TASKS = [
    {"id": "intent", "agent": "IntentAgent", "depends_on": [], "priority": 1},
    {"id": "planner", "agent": "PlannerAgent", "depends_on": ["intent"], "priority": 2},
    {"id": "competitor_discovery", "agent": "CompetitorDiscoveryAgent", "depends_on": ["planner"], "priority": 3},
    {"id": "source_planning", "agent": "SourcePlanningAgent", "depends_on": ["competitor_discovery"], "priority": 4},
    {"id": "web_search", "agent": "WebSearchAgent", "depends_on": ["source_planning"], "priority": 5},
    {"id": "web_crawler", "agent": "WebCrawlerAgent", "depends_on": ["web_search"], "priority": 6},
    {"id": "schema_extraction", "agent": "SchemaExtractionAgent", "depends_on": ["web_crawler"], "priority": 7},
    {"id": "evidence_builder", "agent": "EvidenceBuilderAgent", "depends_on": ["schema_extraction"], "priority": 8},
]

SPECIALIST_TASKS = [
    {"id": "product_positioning", "agent": "ProductPositioningAgent", "depends_on": ["evidence_builder"], "priority": 9},
    {"id": "feature_matrix", "agent": "FeatureMatrixAgent", "depends_on": ["evidence_builder"], "priority": 10},
    {"id": "pricing_analysis", "agent": "PricingAnalysisAgent", "depends_on": ["evidence_builder"], "priority": 11},
    {"id": "user_voice", "agent": "UserVoiceAgent", "depends_on": ["evidence_builder"], "priority": 12},
    {"id": "technology_intelligence", "agent": "TechnologyIntelligenceAgent", "depends_on": ["evidence_builder"], "priority": 13},
    {"id": "gtm", "agent": "GTMAgent", "depends_on": ["evidence_builder"], "priority": 14},
    {
        "id": "swot",
        "agent": "SWOTAgent",
        "depends_on": [
            "product_positioning",
            "feature_matrix",
            "pricing_analysis",
            "user_voice",
            "technology_intelligence",
            "gtm",
        ],
        "priority": 15,
    },
    {"id": "strategic_insight", "agent": "StrategicInsightAgent", "depends_on": ["swot"], "priority": 16},
    {"id": "analysis", "agent": "AnalysisAgent", "depends_on": ["strategic_insight"], "priority": 17},
]

DEEP_REVIEW_TASKS = [
    {"id": "fact_check", "agent": "FactCheckAgent", "depends_on": ["analysis"], "priority": 18},
    {"id": "citation_check", "agent": "CitationCheckAgent", "depends_on": ["analysis"], "priority": 19},
    {"id": "consistency_check", "agent": "ConsistencyCheckAgent", "depends_on": ["analysis"], "priority": 20},
    {"id": "bias_detection", "agent": "BiasDetectionAgent", "depends_on": ["analysis"], "priority": 21},
    {"id": "red_team", "agent": "RedTeamAgent", "depends_on": ["analysis"], "priority": 22},
]


def build_mvp_tasks(enable_deep_review: bool = True) -> list[dict]:
    tasks = [*CORE_TASKS, *SPECIALIST_TASKS]
    if enable_deep_review:
        tasks.extend(DEEP_REVIEW_TASKS)
        quality_depends_on = ["fact_check", "citation_check", "consistency_check", "bias_detection", "red_team"]
        quality_priority = 23
        report_priority = 24
    else:
        quality_depends_on = ["analysis"]
        quality_priority = 18
        report_priority = 19
    tasks.extend(
        [
            {"id": "quality_gate", "agent": "QualityGateAgent", "depends_on": quality_depends_on, "priority": quality_priority},
            {"id": "report_writer", "agent": "ReportWriterAgent", "depends_on": ["quality_gate"], "priority": report_priority},
        ]
    )
    return [dict(task) for task in tasks]


MVP_TASKS = build_mvp_tasks(True)

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
            llm_intent = await context.complete_json(
                intent_llm_prompt(project, query),
                self.output_schema,
            )
            explicit_companies = extract_companies(query)
            if explicit_companies:
                if project.get("max_competitors"):
                    explicit_companies = explicit_companies[: int(project["max_competitors"])]
                deterministic_industry = infer_industry(query)
                llm_intent["target_companies"] = explicit_companies
                llm_intent["needs_competitor_confirmation"] = False
                if deterministic_industry != "unknown":
                    llm_intent["industry"] = deterministic_industry
                llm_intent["analysis_topic"] = infer_topic(query, llm_intent["industry"], explicit_companies)
            else:
                llm_intent["target_companies"] = clean_target_companies(llm_intent.get("target_companies", []))
                if is_auto_discovery_query(query):
                    llm_intent["target_companies"] = []
                    llm_intent["needs_competitor_confirmation"] = True
            validate_intent(llm_intent, project, query)
            return llm_intent
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
        research_plan = {"mode": "simulated", "research_questions": [], "quality_bar": "fixture-only"}
        if not should_simulate(context.config):
            research_plan = await context.complete_json(
                planner_llm_prompt(input_data["project"], input_data["dependency_outputs"].get("intent", {})),
                PLANNER_RESEARCH_SCHEMA,
            )
            validate_research_plan(research_plan)
        tasks = [
            {
                **task,
                "max_retries": context.config.task_default_retries,
                "human_review_required": task["id"] == "web_search"
                and input_data["dependency_outputs"].get("intent", {}).get("needs_competitor_confirmation", False),
            }
            for task in build_mvp_tasks(bool(input_data["project"].get("enable_deep_review", True)))
        ]
        return {
            "dag": {
                "nodes": tasks,
                "edges": [
                    {"source": dependency, "target": task["id"]}
                    for task in tasks
                    for dependency in task["depends_on"]
                ],
                "notes": "Focused path: intent, competitor discovery, source collection, schema extraction, evidence-bound synthesis, quality gate and final report.",
            },
            "tasks": tasks,
            "research_plan": research_plan,
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
        semaphore = asyncio.Semaphore(3)

        async def run_search(plan: dict) -> dict:
            async with semaphore:
                competitor = plan.get("competitor", "unknown")
                query = plan.get("query") or f"{competitor} official product features pricing reviews"
                try:
                    return await context.call_tool(
                        "web_search",
                        {
                            "query": query,
                            "competitor": competitor,
                            "source_type": plan.get("source_type", "mixed"),
                            "max_results": context.config.max_search_results_per_competitor,
                        },
                    )
                except Exception as exc:
                    return {
                        "search_results": [],
                        "search_error": describe_exception(exc),
                        "query": query,
                        "competitor": competitor,
                    }

        search_outputs = await asyncio.gather(*(run_search(plan) for plan in plans))
        failures: list[str] = []
        for result in search_outputs:
            if result.get("search_error"):
                failures.append(f"{result.get('competitor', 'unknown')}: {result.get('query', '')} -> {result['search_error']}")
            for item in result.get("search_results", []):
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])
                all_results.append(item)
        if not all_results:
            detail = "; ".join(failures[:6]) or "no provider returned results"
            raise RuntimeError(f"Live search failed for all planned queries: {detail}")
        return {"search_results": all_results}


class WebCrawlerAgent(BaseAgent):
    name = "WebCrawlerAgent"
    description = "Fetch candidate sources and persist normalized documents."
    output_model = DocumentsOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        search_output = input_data["dependency_outputs"].get("web_search", {})
        results = select_balanced_results(search_output.get("search_results", []), context.config.max_crawl_documents)
        semaphore = asyncio.Semaphore(max(1, context.config.crawler_concurrency))

        async def crawl_result(result: dict) -> tuple[dict, dict | None]:
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
                except Exception:
                    return result, None

        crawled_documents = await asyncio.gather(*(crawl_result(result) for result in results))
        documents: list[dict] = []
        for result, document in crawled_documents:
            if document is None:
                continue
            document = sanitize_document_text(document)
            doc_id = stable_id("doc", context.project_id, document["url"])
            persisted = Document(
                id=doc_id,
                project_id=context.project_id,
                url=document["url"],
                title=document.get("title", ""),
                source_type=canonical_source_type(document.get("source_type", "unknown")),
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
        validate_crawl_coverage(results, documents)
        context.db.commit()
        return {"documents": documents}


class SchemaExtractionAgent(BaseAgent):
    name = "SchemaExtractionAgent"
    description = "Extract competitor schema candidates from crawled documents."
    output_model = ExtractionOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        all_outputs = collect_outputs(input_data)
        docs_output = all_outputs.get("web_crawler", {})
        documents = docs_output.get("documents", [])
        intent = all_outputs.get("intent", {})
        industry = intent.get("industry", "")
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
                        "llm_cleaning": document.get("metadata", {}).get("llm_cleaning", {}),
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
            profile = build_profile(context.project_id, competitor, docs, industry)
            if not should_simulate(context.config):
                try:
                    extracted = await context.complete_json(
                        profile_extraction_prompt(input_data["project"], intent, competitor, docs, profile),
                        COMPETITOR_PROFILE_SCHEMA,
                        max_tokens=4096,
                    )
                except Exception:
                    extracted = await context.complete_json(
                        profile_extraction_prompt(input_data["project"], intent, competitor, docs, profile, doc_limit=3, content_limit=650),
                        COMPETITOR_PROFILE_SCHEMA,
                        max_tokens=4096,
                    )
                profile = merge_llm_profile(profile, extracted, context.project_id, competitor)
                validate_llm_profile(profile, competitor, docs)
                profile["llm_extraction"] = {"used": True, "error": None}
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
        candidate_chunks = select_evidence_candidate_chunks(chunks, documents)
        if candidate_chunks and not should_simulate(context.config):
            all_outputs = collect_outputs(input_data)
            evidence_annotations = await build_llm_evidence_annotations(
                input_data.get("project", {}),
                all_outputs.get("intent", {}),
                candidate_chunks,
                documents,
                context,
            )
        else:
            evidence_annotations = {}
        evidence_items: list[dict] = []
        evidence_by_competitor: dict[str, list[str]] = defaultdict(list)
        for chunk in candidate_chunks:
            document = documents.get(chunk.document_id)
            if not document:
                continue
            source_type = canonical_source_type(chunk.chunk_metadata.get("source_type", document.source_type))
            competitor = chunk.chunk_metadata.get("competitor", "unknown")
            annotation = evidence_annotations.get(chunk.id, {})
            if annotation and not bool(annotation.get("keep", True)):
                continue
            evidence_id = stable_id("ev", context.project_id, chunk.id)
            quote = evidence_quote_from_annotation(annotation, chunk.text)
            summary = evidence_summary_from_annotation(annotation, chunk.text)
            credibility = bounded_score(annotation.get("credibility_score"), credibility_score(source_type))
            freshness = bounded_score(
                annotation.get("freshness_score"),
                0.35 if source_type in {"unverified", "crawl_failed", "search_snippet"} else 0.95,
            )
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
                summary=summary,
                credibility_score=credibility,
                freshness_score=freshness,
                is_primary_source=bool(annotation.get("is_primary_source", source_type in {"official", "pricing", "docs", "changelog"})),
                is_potentially_outdated=bool(annotation.get("is_potentially_outdated", False))
                or document.url.startswith("offline://")
                or source_type in {"unverified", "crawl_failed", "search_snippet"},
                supports_claim_ids=[],
                evidence_metadata={
                    "competitor": competitor,
                    "llm_evidence": {
                        "used": bool(annotation),
                        "claim_area": annotation.get("claim_area"),
                        "evidence_type": annotation.get("evidence_type"),
                        "risk_note": annotation.get("risk_note"),
                    },
                },
                retrieved_at=utc_now(),
            )
            context.db.add(evidence)
            evidence_by_competitor[competitor].append(evidence_id)
            evidence_items.append(evidence_to_dict(evidence))

        coverage_repairs = ensure_evidence_competitor_coverage(
            context,
            candidate_chunks,
            documents,
            evidence_items,
            evidence_by_competitor,
            evidence_annotations,
        )
        if candidate_chunks and not should_simulate(context.config):
            validate_llm_evidence_coverage(candidate_chunks, evidence_items, allow_repaired=True)

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
        return {"evidence": evidence_items, "coverage_repairs": coverage_repairs}


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
        intent = all_outputs.get("intent", {})
        payload = build_deterministic_analysis(input_data["project"], intent, competitors, evidence, context.project_id)
        payload = merge_specialist_outputs(payload, all_outputs, context.project_id, {item.id for item in evidence})

        if not should_simulate(context.config):
            llm_payload = await context.complete_json(
                analysis_llm_prompt(input_data["project"], intent, competitors, evidence, payload),
                ANALYSIS_SYNTHESIS_SCHEMA,
                max_tokens=5200,
            )
            payload = merge_llm_analysis(payload, llm_payload, context.project_id, competitors, evidence)
            validate_analysis_payload(payload, competitors, evidence)

        persisted_claims = persist_claims(context, payload["claims"], self.name)
        for item in evidence:
            supported = [claim["claim_id"] for claim in persisted_claims if item.id in claim["evidence_ids"]]
            item.supports_claim_ids = supported

        context.db.commit()
        payload["claims"] = persisted_claims
        payload.setdefault("source_mix", {})
        payload["source_mix"]["llm_synthesis"] = {"used": not should_simulate(context.config)}
        return payload


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
        report_synthesis = {"used": False, "error": None, "mode": "simulated_structured_renderer"}
        if not should_simulate(context.config):
            llm_report_payload = await context.complete_json(
                report_synthesis_prompt(project, competitors, evidence, claims, analysis, quality),
                REPORT_SYNTHESIS_SCHEMA,
                max_tokens=5200,
            )
            analysis = merge_report_synthesis(analysis, llm_report_payload, competitors, evidence)
            validate_report_ingredients(analysis, competitors, evidence)
            report_synthesis = {"used": True, "error": None, "mode": "llm_structured_synthesis"}
        runtime_warnings = collect_report_runtime_warnings(all_outputs, competitors, report_synthesis, context.config)
        markdown = render_markdown(project, competitors, evidence, claims, analysis, quality, all_outputs, runtime_warnings)
        if not should_simulate(context.config):
            markdown_payload = await context.complete_json(
                report_llm_prompt(project, competitors, evidence, claims, quality, markdown),
                REPORT_MARKDOWN_SCHEMA,
                max_tokens=8192,
            )
            markdown = validate_llm_markdown(
                markdown_payload.get("markdown"),
                competitors=competitors,
                evidence=evidence,
                required_sections=["执行摘要", "决策建议", "关键结论", "竞品对比表", "功能/能力矩阵", "证据质量与风险", "引用来源"],
            )
            report_synthesis["mode"] = "llm_final_markdown"
        markdown = make_citations_readable(markdown, evidence, context.project_id)
        llm_rewrite = {
            **report_synthesis,
        }
        json_report = {
            "project_id": context.project_id,
            "summary": "Evidence-bound deep competitive intelligence report.",
            "competitors": [competitor.profile for competitor in competitors],
            "feature_matrix": analysis.get("feature_matrix", {}),
            "strategic_insights": analysis.get("strategic_insights", []),
            "comparison_dimensions": analysis.get("comparison_dimensions", []),
            "pricing_table": analysis.get("pricing_table", []),
            "competitor_cards": analysis.get("competitor_cards", []),
            "evidence_gaps": analysis.get("evidence_gaps", []),
            "source_mix": analysis.get("source_mix", {}),
            "runtime_warnings": runtime_warnings,
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
- If the text says AI should automatically choose/discover competitors, target_companies must be [] and needs_competitor_confirmation must be true.
- Never treat phrases like "由 AI 自动选择 5 个合适竞品" as a competitor name.
"""


PLANNER_RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "research_questions": {"type": "array", "items": {"type": "string"}},
        "comparison_dimensions": {"type": "array", "items": {"type": "string"}},
        "source_strategy": {"type": "array", "items": {"type": "string"}},
        "quality_bar": {"type": "string"},
        "stop_conditions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["research_questions", "comparison_dimensions", "source_strategy", "quality_bar", "stop_conditions"],
    "additionalProperties": True,
}


def planner_llm_prompt(project: dict, intent: dict) -> str:
    return f"""
You are PlannerAgent. Create a concrete research plan for this competitive intelligence run.

Project:
{json.dumps(project, ensure_ascii=False)}

Intent:
{json.dumps(intent, ensure_ascii=False)}

Rules:
- Make the plan category-specific. For phones, include performance, display, battery, camera, system/ecosystem, design/build, after-sales, and price/value when relevant.
- For laptops or other categories, choose domain-appropriate dimensions.
- Include evidence quality stop conditions that should block a final report if not met.
- Return JSON only.
"""


def validate_research_plan(plan: dict) -> None:
    if not isinstance(plan, dict):
        raise ValueError("PlannerAgent must return a JSON object.")
    if len(plan.get("research_questions", [])) < 3:
        raise ValueError("PlannerAgent research plan is too thin: fewer than 3 research questions.")
    if len(plan.get("comparison_dimensions", [])) < 3:
        raise ValueError("PlannerAgent research plan is too thin: fewer than 3 comparison dimensions.")


def clean_target_companies(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return dedupe_companies([str(value).strip() for value in values if is_plausible_company_name(str(value).strip()) and not is_invalid_competitor_name(str(value))])


def validate_intent(intent: dict, project: dict, query: str) -> None:
    if not intent.get("analysis_topic"):
        raise ValueError("IntentAgent did not produce an analysis_topic.")
    if is_auto_discovery_query(query) and intent.get("target_companies"):
        raise ValueError("IntentAgent incorrectly produced target_companies for an AI discovery task.")
    invalid = [name for name in intent.get("target_companies", []) if is_invalid_competitor_name(name)]
    if invalid:
        raise ValueError(f"IntentAgent produced invalid competitor names: {invalid}")
    if not intent.get("required_dimensions"):
        raise ValueError("IntentAgent did not produce required_dimensions.")


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
Rewrite the existing Markdown report into a polished, decision-ready competitive intelligence report.

Audience:
- Product managers, founders, strategy analysts, or investment researchers who need to make a practical decision after reading.

Hard constraints:
- Return JSON with a single key: markdown.
- Use the project language: {project.get("language", "zh-CN")}.
- Preserve evidence traceability. Use only evidence_ids that appear below; never invent evidence IDs, URLs, claims, prices, certifications, or dates.
- Keep unsupported or volatile facts cautious and mark them as needing live verification.
- Keep these report sections where applicable: 执行摘要, 决策建议, 关键结论, 竞品对比表, 功能/能力矩阵, 定价与商业化信号, 证据质量与风险, 下一步验证清单, 引用来源.
- Do not include Markdown code fences around the report.

Editorial requirements:
- Do not write a laundry list. Every section must answer "so what" and "what should the reader do with this".
- Start with a short bottom-line executive summary, then decision recommendations, then supporting evidence.
- Consolidate repeated facts. Prefer 3 to 5 high-value judgments over many shallow bullets.
- Use tables only when they help comparison. Keep table cells concise and decision-oriented.
- Avoid raw agent/process language except in a short appendix if needed.
- Avoid exposing internal confidence metadata after every sentence. Mention confidence/risk naturally and cite evidence.
- For each major recommendation, include: recommendation, why it matters, uncertainty/risk, and cited support.
- If evidence is weak, explicitly say which conclusion is tentative instead of presenting it as equal to well-supported conclusions.

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

Current structured draft:
{markdown[:8000]}
"""


REPORT_MARKDOWN_SCHEMA = {
    "type": "object",
    "properties": {"markdown": {"type": "string"}},
    "required": ["markdown"],
    "additionalProperties": False,
}


EVIDENCE_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "string"},
                    "keep": {"type": "boolean"},
                    "claim_area": {"type": "string"},
                    "evidence_type": {"type": "string"},
                    "quote": {"type": "string"},
                    "summary": {"type": "string"},
                    "credibility_score": {"type": "number"},
                    "freshness_score": {"type": "number"},
                    "is_primary_source": {"type": "boolean"},
                    "is_potentially_outdated": {"type": "boolean"},
                    "risk_note": {"type": "string"},
                },
                "required": ["chunk_id", "keep", "quote", "summary", "credibility_score", "freshness_score"],
                "additionalProperties": True,
            },
        }
    },
    "required": ["evidence"],
    "additionalProperties": False,
}


def validate_llm_markdown(
    value: object,
    competitors: list[Competitor] | None = None,
    evidence: list[Evidence] | None = None,
    required_sections: list[str] | None = None,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("LLM report response must contain a non-empty markdown string.")
    markdown = value.strip()
    if required_sections:
        missing_sections = [section for section in required_sections if section not in markdown]
        if missing_sections:
            raise ValueError(f"LLM report omitted required sections: {missing_sections}")
    if competitors:
        missing = [competitor.name for competitor in competitors if competitor.name and competitor.name not in markdown]
        if len(missing) > max(1, len(competitors) // 3):
            raise ValueError(f"LLM report omitted too many competitors: {missing[:4]}")
    if evidence:
        valid_ids = {item.id for item in evidence}
        referenced_ids = set(re.findall(r"\bev_[a-z0-9]+", markdown, flags=re.I))
        fake_ids = sorted(referenced_ids - valid_ids)
        if fake_ids:
            raise ValueError(f"LLM report referenced unknown evidence IDs: {fake_ids[:5]}")
        if evidence and len(referenced_ids) < min(5, len(evidence)):
            raise ValueError("LLM report does not cite enough collected evidence.")
    return markdown


ANALYSIS_SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_text": {"type": "string"},
                    "claim_type": {"type": "string"},
                    "subject": {"type": "string"},
                    "confidence": {"type": "number"},
                    "risk_level": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claim_text", "claim_type", "subject", "confidence", "evidence_ids"],
                "additionalProperties": False,
            },
        },
        "strategic_insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "claim": {"type": "string"},
                    "basis": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "risk_level": {"type": "string"},
                },
                "required": ["type", "claim", "basis", "evidence_ids", "confidence", "risk_level"],
                "additionalProperties": False,
            },
        },
        "competitor_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "positioning": {"type": "string"},
                    "best_for": {"type": "string"},
                    "strongest_signals": {"type": "array", "items": {"type": "string"}},
                    "watch_out": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "positioning", "best_for", "watch_out", "recommendation", "evidence_ids"],
                "additionalProperties": True,
            },
        },
    },
    "required": ["claims", "strategic_insights", "competitor_cards"],
    "additionalProperties": True,
}


COMPETITOR_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "product_category": {"type": "string"},
        "target_users": {"type": "array", "items": {"type": "string"}},
        "business_model": {"type": "array", "items": {"type": "string"}},
        "positioning": {
            "type": "object",
            "properties": {
                "short_summary": {"type": "string"},
                "long_summary": {"type": "string"},
            },
            "required": ["short_summary", "long_summary"],
            "additionalProperties": True,
        },
        "features": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "support_status": {"type": "string"},
                    "maturity": {"type": "string"},
                },
                "required": ["name", "category", "description", "support_status", "maturity"],
                "additionalProperties": True,
            },
        },
        "pricing": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "plan_name": {"type": "string"},
                    "price": {"type": "string"},
                    "currency": {"type": ["string", "null"]},
                    "billing_cycle": {"type": "string"},
                    "target_segment": {"type": "string"},
                    "limitations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["plan_name", "price"],
                "additionalProperties": True,
            },
        },
        "technical_signals": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "signal_type": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["signal_type", "description"],
                "additionalProperties": True,
            },
        },
        "user_feedback": {
            "type": "object",
            "properties": {
                "pros": {"type": "array", "items": {"type": "object"}},
                "cons": {"type": "array", "items": {"type": "object"}},
            },
            "additionalProperties": True,
        },
        "source_assessment": {
            "type": "object",
            "properties": {
                "relevant_source_count": {"type": "number"},
                "irrelevant_or_weak_sources": {"type": "array", "items": {"type": "string"}},
                "coverage_gaps": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": True,
        },
    },
    "required": ["product_category", "target_users", "business_model", "positioning", "features", "pricing"],
    "additionalProperties": True,
}


REPORT_SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "strategic_insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "claim": {"type": "string"},
                    "basis": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "risk_level": {"type": "string"},
                },
                "required": ["type", "claim", "basis", "evidence_ids", "confidence", "risk_level"],
                "additionalProperties": True,
            },
        },
        "competitor_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "positioning": {"type": "string"},
                    "best_for": {"type": "string"},
                    "strongest_signals": {"type": "array", "items": {"type": "string"}},
                    "pricing_signal": {"type": "string"},
                    "watch_out": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "positioning", "best_for", "watch_out", "recommendation", "evidence_ids"],
                "additionalProperties": True,
            },
        },
        "evidence_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "competitor": {"type": "string"},
                    "gap": {"type": "string"},
                    "severity": {"type": "string"},
                    "recommended_action": {"type": "string"},
                },
                "required": ["competitor", "gap", "severity", "recommended_action"],
                "additionalProperties": True,
            },
        },
    },
    "required": ["strategic_insights", "competitor_cards", "evidence_gaps"],
    "additionalProperties": True,
}


def profile_extraction_prompt(
    project: dict,
    intent: dict,
    competitor: str,
    docs: list[dict],
    deterministic_profile: dict,
    doc_limit: int = 5,
    content_limit: int = 1000,
) -> str:
    doc_payload = [
        {
            "url": doc.get("url"),
            "title": doc.get("title"),
            "source_type": doc.get("source_type"),
            "content": compact_quote(doc.get("content", ""), max_len=content_limit),
        }
        for doc in rank_documents_for_profile(docs)[:doc_limit]
    ]
    return f"""
Extract a competitor profile for a competitive-intelligence report.

Language: {project.get("language", "zh-CN")}
User task: {project.get("query")}
Parsed intent: {json.dumps(intent, ensure_ascii=False)}
Competitor: {competitor}

Rules:
- Infer the product category and comparison dimensions from the user task and evidence, not from a fixed software template.
- For a phone task, extract dimensions such as camera/影像, chipset/performance, display, battery/charging, OS/ecosystem, design, price/value, after-sales. For other domains, choose domain-appropriate dimensions.
- Do not mark generic website text such as "support", "search", "video", "AI", "security", "database", or "API" as product features unless the evidence clearly says they are features of the analyzed product in this task.
- If a source is irrelevant, crawler boilerplate, navigation text, or only a weak search snippet, mention it in source_assessment and avoid using it as a strong fact.
- Do not invent exact prices, specs, market share, review sentiment, or dates. Use "unknown" or "needs live verification" when evidence is insufficient.
- Be concise: return at most 8 features, 3 pricing rows, 6 technical signals, 5 target-user segments, and 5 business-model signals.
- Do not include reasoning prose outside JSON. Keep field values short.
- Return JSON only.

Evidence documents:
{json.dumps(doc_payload, ensure_ascii=False)}

Deterministic fallback profile that you may correct:
{json.dumps({key: deterministic_profile.get(key) for key in ["product_category", "target_users", "business_model", "features", "pricing", "source_coverage"]}, ensure_ascii=False)}
"""


def rank_documents_for_profile(docs: list[dict]) -> list[dict]:
    source_priority = {"official": 0, "pricing": 1, "docs": 2, "review": 3, "news": 4, "changelog": 5}
    return sorted(
        docs,
        key=lambda doc: (
            source_priority.get(canonical_source_type(doc.get("source_type", "unknown")), 10),
            -len(str(doc.get("content", ""))),
        ),
    )


def merge_llm_profile(base_profile: dict, llm_profile: dict, project_id: str, competitor: str) -> dict:
    profile = dict(base_profile)
    product_category = clean_profile_text(llm_profile.get("product_category"))
    if product_category:
        profile["product_category"] = product_category
    target_users = clean_string_list(llm_profile.get("target_users"), limit=8)
    if target_users:
        profile["target_users"] = target_users
    business_model = clean_string_list(llm_profile.get("business_model"), limit=8)
    if business_model:
        profile["business_model"] = business_model

    positioning = llm_profile.get("positioning") if isinstance(llm_profile.get("positioning"), dict) else {}
    short_summary = clean_profile_text(positioning.get("short_summary"))
    long_summary = clean_profile_text(positioning.get("long_summary"))
    if short_summary or long_summary:
        profile["positioning"] = {
            **profile.get("positioning", {}),
            "short_summary": short_summary or profile.get("positioning", {}).get("short_summary", "unknown"),
            "long_summary": long_summary or short_summary or profile.get("positioning", {}).get("long_summary", "unknown"),
            "evidence_ids": profile.get("positioning", {}).get("evidence_ids", []),
        }

    features = normalize_llm_features(llm_profile.get("features"), project_id, competitor)
    if features:
        profile["features"] = features
    pricing = normalize_llm_pricing(llm_profile.get("pricing"))
    if pricing:
        profile["pricing"] = pricing
    technical = normalize_llm_technical_signals(llm_profile.get("technical_signals"))
    if technical:
        profile["technical_signals"] = technical
    user_feedback = llm_profile.get("user_feedback")
    if isinstance(user_feedback, dict):
        profile["user_feedback"] = {
            "pros": user_feedback.get("pros", []) if isinstance(user_feedback.get("pros", []), list) else [],
            "cons": user_feedback.get("cons", []) if isinstance(user_feedback.get("cons", []), list) else [],
        }
    if isinstance(llm_profile.get("source_assessment"), dict):
        profile["source_assessment"] = llm_profile["source_assessment"]
    return profile


def validate_llm_profile(profile: dict, competitor: str, docs: list[dict]) -> None:
    if is_invalid_competitor_name(competitor):
        raise ValueError(f"Invalid competitor name reached SchemaExtractionAgent: {competitor}")
    if not docs:
        raise ValueError(f"SchemaExtractionAgent has no documents for {competitor}.")
    category = clean_profile_text(profile.get("product_category"))
    if not category or category == "unknown":
        raise ValueError(f"SchemaExtractionAgent LLM profile for {competitor} did not identify a product category.")
    features = [feature for feature in profile.get("features", []) if isinstance(feature, dict) and feature.get("name") != "unknown"]
    if len(features) < 2:
        raise ValueError(f"SchemaExtractionAgent LLM profile for {competitor} extracted fewer than 2 comparable features.")
    positioning = profile.get("positioning", {}) if isinstance(profile.get("positioning"), dict) else {}
    if not clean_profile_text(positioning.get("short_summary")):
        raise ValueError(f"SchemaExtractionAgent LLM profile for {competitor} has no positioning summary.")


def normalize_llm_features(values: object, project_id: str, competitor: str) -> list[dict]:
    if not isinstance(values, list):
        return []
    features = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        name = clean_profile_text(value.get("name"))
        if not name or name.lower() == "unknown":
            continue
        display_name = canonical_feature_label(name)
        key = normalize_feature_name(display_name)
        if key in seen:
            continue
        seen.add(key)
        features.append(
            {
                "feature_id": stable_id("feat", project_id, competitor, display_name),
                "name": display_name,
                "category": clean_profile_text(value.get("category")) or "domain",
                "description": clean_profile_text(value.get("description")) or f"Evidence supports {display_name}.",
                "support_status": clean_profile_text(value.get("support_status")) or "yes",
                "maturity": clean_profile_text(value.get("maturity")) or "medium",
                "evidence_ids": [],
            }
        )
        if len(features) >= 12:
            break
    return features


def normalize_llm_pricing(values: object) -> list[dict]:
    if not isinstance(values, list):
        return []
    pricing = []
    for value in values[:4]:
        if not isinstance(value, dict):
            continue
        price = clean_profile_text(value.get("price")) or "unknown"
        pricing.append(
            {
                "plan_name": clean_profile_text(value.get("plan_name")) or "public price signal",
                "price": price,
                "currency": clean_profile_text(value.get("currency")) or None,
                "billing_cycle": clean_profile_text(value.get("billing_cycle")) or "unknown",
                "target_segment": clean_profile_text(value.get("target_segment")) or "unknown",
                "included_features": [],
                "limitations": clean_string_list(value.get("limitations"), limit=5) or ["Exact current price must be verified before decisions."],
                "evidence_ids": [],
            }
        )
    return pricing


def normalize_llm_technical_signals(values: object) -> list[dict]:
    if not isinstance(values, list):
        return []
    signals = []
    for value in values[:10]:
        if not isinstance(value, dict):
            continue
        signal_type = clean_profile_text(value.get("signal_type"))
        description = clean_profile_text(value.get("description"))
        if not signal_type or not description:
            continue
        signals.append(
            {
                "signal_type": signal_type,
                "description": description,
                "confidence": clamp_float(value.get("confidence", 0.6), 0.1, 0.95),
                "evidence_ids": [],
            }
        )
    return signals


def clean_profile_text(value: object, max_len: int = 420) -> str:
    if value is None:
        return ""
    return compact_quote(normalize_text(str(value)), max_len=max_len).strip()


def clean_string_list(value: object, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    seen: set[str] = set()
    for item in value:
        text = clean_profile_text(item, max_len=120)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def report_synthesis_prompt(project: dict, competitors: list[Competitor], evidence: list[Evidence], claims: list[Claim], analysis: dict, quality: dict) -> str:
    valid_evidence = [
        {
            "evidence_id": item.id,
            "competitor": item.evidence_metadata.get("competitor", "unknown"),
            "source_type": item.source_type,
            "title": item.source_title,
            "summary": item.summary[:220],
            "credibility_score": item.credibility_score,
        }
        for item in report_evidence_items(evidence, limit=40)
    ]
    profile_payload = [
        {
            "name": competitor.name,
            "product_category": competitor.profile.get("product_category"),
            "positioning": competitor.profile.get("positioning", {}),
            "features": competitor.profile.get("features", [])[:10],
            "pricing": competitor.profile.get("pricing", [])[:3],
            "source_assessment": competitor.profile.get("source_assessment", {}),
        }
        for competitor in competitors
    ]
    return f"""
You are the ReportWriterAgent. Produce structured report ingredients for a product-manager-facing competitive intelligence report.

User task: {project.get("query")}
Language: {project.get("language", "zh-CN")}
Quality score: {json.dumps(quality, ensure_ascii=False)}

Rules:
- Use only competitors and evidence IDs below.
- Correct domain drift. If the task is about phones, do not use SaaS/AI-office dimensions. If the task is about another category, choose dimensions appropriate to that category.
- Keep claims decision-useful and cautious. Do not invent exact specs, prices, rankings, market share, dates, or review sentiment beyond evidence.
- Synthesize instead of listing. Focus on what matters for selection, positioning, risk, and next verification.
- Each strategic insight should contain an implication, not just a restatement of a competitor fact.
- Competitor cards should explain the competitor's role in the market map, who should care, and the main uncertainty.
- Return concise JSON; the renderer will build the final Markdown.

Competitor profiles:
{json.dumps(profile_payload, ensure_ascii=False)}

Current analysis:
{json.dumps({key: analysis.get(key) for key in ["strategic_insights", "competitor_cards", "pricing_table", "evidence_gaps", "comparison_dimensions"]}, ensure_ascii=False)}

Representative evidence:
{json.dumps(valid_evidence, ensure_ascii=False)}

Claims:
{json.dumps([claim_to_dict(claim) for claim in claims[:24]], ensure_ascii=False)}
"""


def merge_report_synthesis(analysis: dict, llm_payload: dict, competitors: list[Competitor], evidence: list[Evidence]) -> dict:
    merged = dict(analysis)
    valid_ids = {item.id for item in evidence}
    known = {competitor.name.casefold(): competitor.name for competitor in competitors}

    insights = []
    for item in llm_payload.get("strategic_insights", []) if isinstance(llm_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        claim = clean_profile_text(item.get("claim"), max_len=420)
        if not claim:
            continue
        insights.append(
            {
                "type": normalize_claim_type(str(item.get("type", "inference"))),
                "claim": claim,
                "basis": clean_profile_text(item.get("basis"), max_len=220) or "来自证据综合。",
                "evidence_ids": sanitize_evidence_ids(item.get("evidence_ids", []), valid_ids),
                "confidence": clamp_float(item.get("confidence", 0.6), 0.1, 0.9),
                "risk_level": normalize_risk(str(item.get("risk_level", "medium"))),
            }
        )
    if insights:
        merged["strategic_insights"] = dedupe_insights(insights)[:10]

    existing_cards = {card.get("name", "").casefold(): dict(card) for card in analysis.get("competitor_cards", []) if isinstance(card, dict)}
    for item in llm_payload.get("competitor_cards", []) if isinstance(llm_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        name = known.get(str(item.get("name", "")).casefold())
        if not name:
            continue
        card = existing_cards.get(name.casefold(), {"name": name})
        for key in ["positioning", "best_for", "pricing_signal", "watch_out", "recommendation"]:
            text = clean_profile_text(item.get(key), max_len=260)
            if text:
                card[key] = text
        signals = clean_string_list(item.get("strongest_signals"), limit=6)
        if signals:
            card["strongest_signals"] = signals
        ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_ids)
        if ids:
            card["evidence_ids"] = ids[:5]
        existing_cards[name.casefold()] = card
    if existing_cards:
        merged["competitor_cards"] = list(existing_cards.values())

    gaps = []
    for item in llm_payload.get("evidence_gaps", []) if isinstance(llm_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        competitor = known.get(str(item.get("competitor", "")).casefold(), clean_profile_text(item.get("competitor"), max_len=80))
        gap = clean_profile_text(item.get("gap"), max_len=220)
        if not competitor or not gap:
            continue
        gaps.append(
            {
                "competitor": competitor,
                "gap": gap,
                "severity": normalize_risk(str(item.get("severity", "medium"))),
                "recommended_action": clean_profile_text(item.get("recommended_action"), max_len=220) or "补充证据后复核。",
            }
        )
    if gaps:
        merged["evidence_gaps"] = gaps
    return merged


def build_deterministic_analysis(
    project: dict,
    intent: dict,
    competitors: list[Competitor],
    evidence: list[Evidence],
    project_id: str,
) -> dict:
    grouped = evidence_by_competitor(evidence)
    feature_matrix = build_feature_matrix(competitors)
    comparison_dimensions = build_comparison_dimensions(feature_matrix, competitors)
    source_mix = build_source_mix(evidence, grouped)
    competitor_cards: list[dict] = []
    pricing_table: list[dict] = []
    evidence_gaps: list[dict] = []
    claims: list[dict] = []

    for competitor in competitors:
        profile = competitor.profile
        items = grouped.get(competitor.name, [])
        evidence_ids = usable_evidence_ids(items)[:4]
        all_ids = [item.id for item in items][:4]
        feature_names = profile_feature_names(profile)
        pricing_summary = summarize_pricing(profile)
        positioning_summary = readable_positioning_summary(competitor.name, profile, feature_names)
        card_gaps = competitor_evidence_gaps(competitor, items, profile)
        evidence_gaps.extend(card_gaps)
        card = {
            "name": competitor.name,
            "positioning": positioning_summary,
            "best_for": infer_best_fit(competitor.name, profile, feature_names),
            "strongest_signals": feature_names[:5],
            "pricing_signal": pricing_summary,
            "source_types": sorted({item.source_type for item in items}),
            "evidence_count": len(items),
            "watch_out": summarize_card_risk(card_gaps, items),
            "recommendation": competitor_recommendation(competitor.name, profile, card_gaps),
            "evidence_ids": evidence_ids or all_ids,
        }
        competitor_cards.append(card)
        pricing_table.append(
            {
                "competitor": competitor.name,
                "pricing_signal": pricing_summary,
                "currency": first_pricing_value(profile, "currency"),
                "billing_cycle": first_pricing_value(profile, "billing_cycle") or "unknown",
                "confidence": confidence_from_evidence(evidence_ids),
                "evidence_ids": profile_evidence_ids(profile, "pricing") or evidence_ids[:2],
                "caveat": "价格、套餐和促销变化快，需要上线前刷新。" if pricing_summary != "unknown" else "未采集到可靠价格信号。",
            }
        )

        if evidence_ids:
            claims.append(
                create_claim(
                    project_id,
                    claim_text=f"{competitor.name} 在本次采集资料中的核心定位是：{positioning_summary}",
                    claim_type="fact",
                    subject=competitor.name,
                    confidence=confidence_from_evidence(evidence_ids),
                    evidence_ids=evidence_ids[:3],
                    created_by=AnalysisAgent.name,
                    risk_level="low" if len(evidence_ids) >= 2 else "medium",
                )
            )
            if pricing_summary != "unknown":
                claims.append(
                    create_claim(
                        project_id,
                        claim_text=f"{competitor.name} 的价格/商业化信号为：{pricing_summary}",
                        claim_type="fact",
                        subject=competitor.name,
                        confidence=min(0.78, confidence_from_evidence(evidence_ids)),
                        evidence_ids=(profile_evidence_ids(profile, "pricing") or evidence_ids[:2]),
                        created_by=AnalysisAgent.name,
                        risk_level="medium",
                    )
                )
        else:
            claims.append(
                create_claim(
                    project_id,
                    claim_text=f"{competitor.name} 缺少可用公开证据，报告只能把定位、价格和用户反馈标为 unknown 或低置信度线索。",
                    claim_type="unknown",
                    subject=competitor.name,
                    confidence=0.1,
                    evidence_ids=all_ids,
                    created_by=AnalysisAgent.name,
                    risk_level="high",
                )
            )

    all_usable_ids = first_usable_evidence_ids(evidence, 8)
    strategic_insights = build_strategic_insights(project, intent, competitor_cards, comparison_dimensions, evidence_gaps, all_usable_ids)
    for insight in strategic_insights:
        claims.append(
            create_claim(
                project_id,
                claim_text=insight["claim"],
                claim_type=insight["type"],
                subject=insight.get("subject", "overall"),
                confidence=insight["confidence"],
                evidence_ids=insight["evidence_ids"],
                created_by=AnalysisAgent.name,
                risk_level=insight["risk_level"],
            )
        )

    return {
        "claims": dedupe_claim_dicts(claims),
        "feature_matrix": feature_matrix,
        "strategic_insights": strategic_insights,
        "comparison_dimensions": comparison_dimensions,
        "pricing_table": pricing_table,
        "competitor_cards": competitor_cards,
        "evidence_gaps": evidence_gaps,
        "source_mix": source_mix,
    }


SPECIALIST_OUTPUT_KEYS = [
    "product_positioning",
    "feature_matrix",
    "pricing_analysis",
    "user_voice",
    "technology_intelligence",
    "gtm",
    "swot",
    "strategic_insight",
]


def merge_specialist_outputs(base_payload: dict, agent_outputs: dict, project_id: str, valid_evidence_ids: set[str]) -> dict:
    merged = dict(base_payload)
    source_mix = dict(merged.get("source_mix", {}))
    used_outputs: list[str] = []
    specialist_claims: list[dict] = []
    specialist_insights: list[dict] = []

    for output_key in SPECIALIST_OUTPUT_KEYS:
        output = agent_outputs.get(output_key, {})
        payload = output.get("payload", {}) if isinstance(output, dict) else {}
        if not isinstance(payload, dict) or not payload:
            continue
        used_outputs.append(output_key)
        specialist_claims.extend(
            specialist_findings_to_claims(
                payload.get("findings", []),
                project_id,
                valid_evidence_ids,
                default_agent=str(output.get("agent") or output_key),
            )
        )

    feature_payload = agent_outputs.get("feature_matrix", {}).get("payload", {})
    if isinstance(feature_payload, dict) and isinstance(feature_payload.get("feature_matrix"), dict):
        merged["feature_matrix"] = merge_feature_matrices(
            merged.get("feature_matrix", {}),
            feature_payload["feature_matrix"],
            valid_evidence_ids,
        )

    pricing_payload = agent_outputs.get("pricing_analysis", {}).get("payload", {})
    if isinstance(pricing_payload, dict) and isinstance(pricing_payload.get("pricing_table"), list):
        merged["pricing_table"] = merge_pricing_tables(
            merged.get("pricing_table", []),
            pricing_payload["pricing_table"],
            valid_evidence_ids,
        )
        specialist_insights.extend(pricing_payload.get("insights", []))

    strategic_payload = agent_outputs.get("strategic_insight", {}).get("payload", {})
    if isinstance(strategic_payload, dict):
        specialist_insights.extend(strategic_payload.get("strategic_insights", []))

    swot_payload = agent_outputs.get("swot", {}).get("payload", {})
    if isinstance(swot_payload, dict) and swot_payload.get("swot"):
        source_mix["swot_profiles_written"] = True

    merged["claims"] = dedupe_claim_dicts([*merged.get("claims", []), *specialist_claims])[:40]
    merged["strategic_insights"] = dedupe_insights(
        [*merged.get("strategic_insights", []), *normalize_specialist_insights(specialist_insights, valid_evidence_ids)]
    )[:14]
    source_mix["specialist_outputs_used"] = used_outputs
    merged["source_mix"] = source_mix
    return merged


def specialist_findings_to_claims(values: object, project_id: str, valid_evidence_ids: set[str], default_agent: str) -> list[dict]:
    if not isinstance(values, list):
        return []
    claims: list[dict] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        text = compact_quote(str(item.get("claim") or item.get("claim_text") or "").strip(), max_len=420)
        if not text:
            continue
        evidence_ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_evidence_ids)
        claim_type = normalize_claim_type(str(item.get("claim_type", "inference")))
        claims.append(
            create_claim(
                project_id,
                claim_text=text,
                claim_type=claim_type if evidence_ids or claim_type == "unknown" else "unknown",
                subject=compact_quote(str(item.get("subject") or "overall"), max_len=100),
                confidence=clamp_float(item.get("confidence", 0.55), 0.1, 0.88 if evidence_ids else 0.35),
                evidence_ids=evidence_ids[:5],
                created_by=str(item.get("created_by_agent") or default_agent),
                risk_level=normalize_risk(str(item.get("risk_level", "medium"))),
            )
        )
    return claims


def normalize_specialist_insights(values: object, valid_evidence_ids: set[str]) -> list[dict]:
    if not isinstance(values, list):
        return []
    insights: list[dict] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        claim = compact_quote(str(item.get("claim", "")).strip(), max_len=420)
        if not claim:
            continue
        evidence_ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_evidence_ids)
        insights.append(
            {
                "type": normalize_claim_type(str(item.get("type", "inference"))),
                "claim": claim,
                "basis": compact_quote(str(item.get("basis", "来自专家 Agent 的证据综合。")), max_len=240),
                "evidence_ids": evidence_ids[:6],
                "confidence": clamp_float(item.get("confidence", 0.6), 0.1, 0.88 if evidence_ids else 0.35),
                "risk_level": normalize_risk(str(item.get("risk_level", "medium"))),
            }
        )
    return insights


def merge_feature_matrices(base_matrix: dict, specialist_matrix: dict, valid_evidence_ids: set[str]) -> dict:
    merged = {str(feature): dict(values) for feature, values in base_matrix.items() if isinstance(values, dict)}
    for feature, values in specialist_matrix.items():
        if not isinstance(values, dict):
            continue
        existing = merged.setdefault(str(feature), {})
        for competitor, cell in values.items():
            if not isinstance(cell, dict):
                continue
            normalized_cell = dict(cell)
            normalized_cell["evidence_ids"] = sanitize_evidence_ids(cell.get("evidence_ids", []), valid_evidence_ids)
            existing[str(competitor)] = {**existing.get(str(competitor), {}), **normalized_cell}
    return merged


def merge_pricing_tables(base_rows: list[dict], specialist_rows: list[dict], valid_evidence_ids: set[str]) -> list[dict]:
    by_name = {str(row.get("competitor", "")).casefold(): dict(row) for row in base_rows if isinstance(row, dict)}
    for row in specialist_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("competitor", "")).strip()
        if not name:
            continue
        existing = by_name.get(name.casefold(), {"competitor": name})
        merged_row = {**existing, **row}
        merged_row["evidence_ids"] = sanitize_evidence_ids(row.get("evidence_ids", existing.get("evidence_ids", [])), valid_evidence_ids)
        by_name[name.casefold()] = merged_row
    return list(by_name.values())


def analysis_llm_prompt(project: dict, intent: dict, competitors: list[Competitor], evidence: list[Evidence], base_payload: dict) -> str:
    competitor_payload = [
        {
            "name": competitor.name,
            "profile": {
                "product_category": competitor.profile.get("product_category"),
                "target_users": competitor.profile.get("target_users", []),
                "positioning": competitor.profile.get("positioning", {}),
                "features": competitor.profile.get("features", [])[:8],
                "pricing": competitor.profile.get("pricing", [])[:3],
                "source_coverage": competitor.profile.get("source_coverage", []),
            },
        }
        for competitor in competitors
    ]
    evidence_payload = [
        {
            "evidence_id": item.id,
            "competitor": item.evidence_metadata.get("competitor", "unknown"),
            "source_type": item.source_type,
            "publisher": item.publisher,
            "title": item.source_title,
            "summary": item.summary[:260],
            "quote": item.quote[:320],
            "credibility_score": item.credibility_score,
        }
        for item in evidence[:42]
    ]
    return f"""
Create a concise, evidence-bound competitive-intelligence synthesis.

Language: {project.get("language", "zh-CN")}
User task: {project.get("query")}
Parsed intent: {json.dumps(intent, ensure_ascii=False)}

Rules:
- Use only competitors and evidence IDs listed below.
- Prefer clear product-manager language: practical positioning, buying/selection criteria, risks, and next checks.
- Do not invent exact prices, dates, certifications, market share, benchmark scores, or user-review sentiment.
- When evidence is weak, say it is a low-confidence signal and recommend verification.
- Keep the deterministic feature matrix intact conceptually; you may improve wording in cards, claims, and insights.

Competitors:
{json.dumps(competitor_payload, ensure_ascii=False)}

Evidence:
{json.dumps(evidence_payload, ensure_ascii=False)}

Deterministic baseline:
{json.dumps({key: base_payload.get(key) for key in ["competitor_cards", "comparison_dimensions", "pricing_table", "evidence_gaps", "strategic_insights"]}, ensure_ascii=False)}
"""


def merge_llm_analysis(base_payload: dict, llm_payload: dict, project_id: str, competitors: list[Competitor], evidence: list[Evidence]) -> dict:
    valid_ids = {item.id for item in evidence}
    known_competitors = {competitor.name.casefold(): competitor.name for competitor in competitors}
    merged = dict(base_payload)

    llm_claims = []
    for item in llm_payload.get("claims", []) if isinstance(llm_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        text = compact_quote(str(item.get("claim_text", "")).strip(), max_len=420)
        if not text:
            continue
        evidence_ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_ids)
        claim_type = normalize_claim_type(str(item.get("claim_type", "inference")))
        confidence = clamp_float(item.get("confidence", 0.55), 0.1, 0.85 if evidence_ids else 0.35)
        llm_claims.append(
            create_claim(
                project_id,
                claim_text=text,
                claim_type=claim_type if evidence_ids or claim_type == "unknown" else "unknown",
                subject=str(item.get("subject") or "overall")[:80],
                confidence=confidence,
                evidence_ids=evidence_ids,
                created_by="AnalysisAgent:llm",
                risk_level=normalize_risk(str(item.get("risk_level", "medium"))),
            )
        )
    merged["claims"] = dedupe_claim_dicts([*base_payload.get("claims", []), *llm_claims])[:28]

    insights = list(base_payload.get("strategic_insights", []))
    for item in llm_payload.get("strategic_insights", []) if isinstance(llm_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        evidence_ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_ids)
        claim = compact_quote(str(item.get("claim", "")).strip(), max_len=420)
        if not claim:
            continue
        insights.append(
            {
                "type": normalize_claim_type(str(item.get("type", "inference"))),
                "claim": claim,
                "basis": compact_quote(str(item.get("basis", "来自证据综合。")), max_len=220),
                "evidence_ids": evidence_ids,
                "confidence": clamp_float(item.get("confidence", 0.55), 0.1, 0.85 if evidence_ids else 0.35),
                "risk_level": normalize_risk(str(item.get("risk_level", "medium"))),
            }
        )
    merged["strategic_insights"] = dedupe_insights(insights)[:10]

    cards_by_name = {card["name"].casefold(): dict(card) for card in base_payload.get("competitor_cards", [])}
    for item in llm_payload.get("competitor_cards", []) if isinstance(llm_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        name = known_competitors.get(str(item.get("name", "")).casefold())
        if not name or name.casefold() not in cards_by_name:
            continue
        card = cards_by_name[name.casefold()]
        for key in ["positioning", "best_for", "watch_out", "recommendation"]:
            value = str(item.get(key, "")).strip()
            if value:
                card[key] = compact_quote(value, max_len=260)
        signals = item.get("strongest_signals", [])
        if isinstance(signals, list) and signals:
            card["strongest_signals"] = dedupe_text(
                [canonical_feature_label(compact_quote(str(signal), max_len=80)) for signal in signals[:8] if str(signal).strip()]
            )[:6]
        ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_ids)
        if ids:
            card["evidence_ids"] = ids[:4]
        cards_by_name[name.casefold()] = card
    merged["competitor_cards"] = list(cards_by_name.values())
    return merged


def validate_analysis_payload(payload: dict, competitors: list[Competitor], evidence: list[Evidence]) -> None:
    valid_ids = {item.id for item in evidence}
    competitor_names = {competitor.name for competitor in competitors}
    cards = payload.get("competitor_cards", [])
    if len(cards) < len(competitors):
        raise ValueError(f"AnalysisAgent produced {len(cards)} competitor cards for {len(competitors)} competitors.")
    card_names = {str(card.get("name", "")) for card in cards if isinstance(card, dict)}
    missing = sorted(competitor_names - card_names)
    if missing:
        raise ValueError(f"AnalysisAgent omitted competitor cards: {missing[:6]}")
    if not payload.get("strategic_insights"):
        raise ValueError("AnalysisAgent produced no strategic insights.")
    cited_claims = 0
    for claim in payload.get("claims", []):
        if not isinstance(claim, dict):
            continue
        ids = sanitize_evidence_ids(claim.get("evidence_ids", []), valid_ids)
        if ids:
            cited_claims += 1
    if cited_claims < max(2, len(competitors)):
        raise ValueError("AnalysisAgent produced too few evidence-cited claims.")


def validate_report_ingredients(analysis: dict, competitors: list[Competitor], evidence: list[Evidence]) -> None:
    valid_ids = {item.id for item in evidence}
    cards = analysis.get("competitor_cards", [])
    if len(cards) < len(competitors):
        raise ValueError("ReportWriterAgent synthesis omitted competitor cards.")
    for card in cards:
        if not isinstance(card, dict):
            continue
        if not sanitize_evidence_ids(card.get("evidence_ids", []), valid_ids):
            raise ValueError(f"ReportWriterAgent card lacks valid evidence IDs: {card.get('name')}")
    if len(analysis.get("strategic_insights", [])) < 3:
        raise ValueError("ReportWriterAgent synthesis produced fewer than 3 strategic insights.")


def persist_claims(context: AgentContext, claims: list[dict], default_agent: str) -> list[dict]:
    persisted: list[dict] = []
    seen: set[str] = set()
    for claim in claims:
        claim_text = str(claim.get("claim_text", "")).strip()
        if not claim_text:
            continue
        claim_id = claim.get("claim_id") or stable_id("claim", context.project_id, claim_text)
        if claim_id in seen:
            continue
        seen.add(claim_id)
        evidence_ids = [str(item) for item in claim.get("evidence_ids", []) if item]
        normalized = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "claim_type": normalize_claim_type(str(claim.get("claim_type", "inference"))),
            "subject": str(claim.get("subject", "overall")),
            "confidence": clamp_float(claim.get("confidence", 0.5), 0.0, 1.0),
            "risk_level": normalize_risk(str(claim.get("risk_level", "medium"))),
            "evidence_ids": evidence_ids,
            "created_by_agent": str(claim.get("created_by_agent", default_agent)),
            "review_status": claim.get("review_status") or ("approved" if evidence_ids or claim.get("claim_type") == "unknown" else "needs_revision"),
            "review_comments": claim.get("review_comments") or ([] if evidence_ids else ["No supporting evidence; keep as unknown or low confidence."]),
        }
        context.db.add(
            Claim(
                id=normalized["claim_id"],
                project_id=context.project_id,
                claim_text=normalized["claim_text"],
                claim_type=normalized["claim_type"],
                subject=normalized["subject"],
                confidence=normalized["confidence"],
                risk_level=normalized["risk_level"],
                evidence_ids=normalized["evidence_ids"],
                created_by_agent=normalized["created_by_agent"],
                review_status=normalized["review_status"],
                review_comments=normalized["review_comments"],
                claim_metadata={},
            )
        )
        persisted.append(normalized)
    return persisted


def evidence_by_competitor(evidence: list[Evidence]) -> dict[str, list[Evidence]]:
    grouped: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.evidence_metadata.get("competitor", "unknown")].append(item)
    return grouped


def usable_evidence_ids(items: list[Evidence]) -> list[str]:
    return [
        item.id
        for item in items
        if item.source_type != "crawl_failed" and item.credibility_score >= 0.35 and item.quote and "Crawl failed for" not in item.quote
    ]


def first_usable_evidence_ids(evidence: list[Evidence], limit: int) -> list[str]:
    ids = []
    for item in evidence:
        if item.id in ids:
            continue
        if item.source_type == "crawl_failed":
            continue
        ids.append(item.id)
        if len(ids) >= limit:
            break
    return ids


def build_feature_matrix(competitors: list[Competitor]) -> dict[str, dict[str, dict]]:
    feature_names = select_feature_names(competitors)
    matrix: dict[str, dict[str, dict]] = {feature: {} for feature in feature_names}
    for feature in feature_names:
        for competitor in competitors:
            matched = next(
                (
                    item
                    for item in competitor.profile.get("features", [])
                    if normalize_feature_name(item.get("name", "")) == normalize_feature_name(feature)
                ),
                None,
            )
            matrix[feature][competitor.name] = {
                "support": bool(matched and matched.get("support_status", "yes") != "unknown"),
                "maturity": matched.get("maturity", "unknown") if matched else "unknown",
                "evidence_ids": matched.get("evidence_ids", []) if matched else [],
                "note": matched.get("description", "") if matched else "",
            }
    return matrix


def select_feature_names(competitors: list[Competitor], limit: int = 10) -> list[str]:
    counts: Counter[str] = Counter()
    original: dict[str, str] = {}
    for competitor in competitors:
        for feature in competitor.profile.get("features", []):
            name = str(feature.get("name", "")).strip()
            if not name or name == "unknown":
                continue
            canonical = canonical_feature_label(name)
            key = normalize_feature_name(canonical)
            counts[key] += 1
            original.setdefault(key, canonical)
    ordered = [original[key] for key, _ in counts.most_common(limit)]
    return ordered or ["Positioning clarity", "Pricing clarity", "User feedback coverage", "Recent update signal"]


def build_comparison_dimensions(feature_matrix: dict[str, dict[str, dict]], competitors: list[Competitor]) -> list[dict]:
    dimensions = []
    competitor_count = max(1, len(competitors))
    for feature, values in feature_matrix.items():
        support_count = sum(1 for item in values.values() if item.get("support"))
        if support_count == 0:
            continue
        if support_count == competitor_count:
            interpretation = "基础门槛项：主要竞品都已有信号，需要比较成熟度和体验。"
        elif support_count == 1:
            interpretation = "差异化线索：目前只有少数竞品被证据覆盖，适合继续验证。"
        else:
            interpretation = "分层维度：部分竞品具备信号，可作为短名单筛选条件。"
        dimensions.append(
            {
                "dimension": feature,
                "support_count": support_count,
                "competitor_count": competitor_count,
                "interpretation": interpretation,
            }
        )
    return dimensions[:8]


def build_source_mix(evidence: list[Evidence], grouped: dict[str, list[Evidence]]) -> dict:
    source_counts = Counter(canonical_source_type(item.source_type) for item in evidence)
    by_competitor = {
        competitor: {
            "total": len(items),
            "source_types": dict(Counter(canonical_source_type(item.source_type) for item in items)),
            "usable": len(usable_evidence_ids(items)),
        }
        for competitor, items in grouped.items()
    }
    return {"total": len(evidence), "source_types": dict(source_counts), "by_competitor": by_competitor}


def competitor_evidence_gaps(competitor: Competitor, items: list[Evidence], profile: dict) -> list[dict]:
    source_types = {canonical_source_type(item.source_type) for item in items}
    gaps = []
    if len(usable_evidence_ids(items)) < 2:
        gaps.append(
            {
                "competitor": competitor.name,
                "gap": "可用证据少于 2 条",
                "severity": "high",
                "recommended_action": "补充官方页、价格页、评测/评论至少两类来源。",
            }
        )
    if not (source_types & {"official", "docs", "changelog"}):
        gaps.append(
            {
                "competitor": competitor.name,
                "gap": "缺少官方/文档类来源",
                "severity": "medium",
                "recommended_action": "优先抓取官网产品页、帮助中心、发布说明或规格页。",
            }
        )
    if not profile.get("pricing") or summarize_pricing(profile) == "unknown":
        gaps.append(
            {
                "competitor": competitor.name,
                "gap": "价格或商业化信号不足",
                "severity": "medium",
                "recommended_action": "补充官方价格页、渠道价格、套餐说明或电商详情页。",
            }
        )
    if not (source_types & {"review", "third_party", "news"}):
        gaps.append(
            {
                "competitor": competitor.name,
                "gap": "缺少第三方评价/新闻/用户反馈",
                "severity": "low",
                "recommended_action": "加入评测、媒体报道、社区讨论或应用商店评论。",
            }
        )
    if source_types and source_types <= {"search_snippet", "unverified", "crawl_failed"}:
        gaps.append(
            {
                "competitor": competitor.name,
                "gap": "来源主要是搜索摘要或失败抓取兜底",
                "severity": "high",
                "recommended_action": "重新抓取可访问页面或切换到更稳定的来源。",
            }
        )
    return gaps


def build_strategic_insights(
    project: dict,
    intent: dict,
    competitor_cards: list[dict],
    comparison_dimensions: list[dict],
    evidence_gaps: list[dict],
    evidence_ids: list[str],
) -> list[dict]:
    insights = []
    if comparison_dimensions:
        dimensions = "、".join(item["dimension"] for item in comparison_dimensions[:4])
        insights.append(
            {
                "type": "inference",
                "subject": "comparison_framework",
                "claim": f"本次任务最适合用「{dimensions}」作为首轮比较框架，再结合价格/渠道和证据质量做短名单筛选。",
                "basis": "来自各竞品公开资料中被反复抽取到的能力/卖点信号。",
                "evidence_ids": evidence_ids[:5],
                "confidence": 0.68 if evidence_ids else 0.25,
                "risk_level": "medium",
            }
        )
    if competitor_cards:
        ranked = sorted(competitor_cards, key=lambda card: (len(card.get("strongest_signals", [])), card.get("evidence_count", 0)), reverse=True)
        leaders = "、".join(card["name"] for card in ranked[: min(3, len(ranked))])
        insights.append(
            {
                "type": "opportunity",
                "subject": "shortlist",
                "claim": f"在当前证据下，{leaders} 的资料完整度或能力信号更适合作为第一轮重点对标对象；其余竞品应先补齐证据后再下强结论。",
                "basis": "按可用证据数量、功能信号和资料覆盖度排序。",
                "evidence_ids": evidence_ids[:5],
                "confidence": 0.64 if evidence_ids else 0.2,
                "risk_level": "medium",
            }
        )
    high_gaps = [gap for gap in evidence_gaps if gap.get("severity") == "high"]
    if high_gaps:
        names = "、".join(sorted({gap["competitor"] for gap in high_gaps})[:4])
        insights.append(
            {
                "type": "recommendation",
                "subject": "research_plan",
                "claim": f"报告交付前应优先补齐 {names} 的高风险证据缺口，否则相关定位、价格和用户反馈结论只能作为低置信度线索。",
                "basis": "质量门禁发现部分竞品来源不足或主要依赖搜索摘要/失败抓取兜底。",
                "evidence_ids": evidence_ids[:5],
                "confidence": 0.74 if evidence_ids else 0.35,
                "risk_level": "low",
            }
        )
    else:
        insights.append(
            {
                "type": "recommendation",
                "subject": "next_step",
                "claim": "下一步建议刷新实时价格、补充用户评价，并用同一套维度做人工复核，避免把营销表述直接当作事实。",
                "basis": "价格和口碑属于高波动信息，即使本轮有证据也需要临近决策前复查。",
                "evidence_ids": evidence_ids[:5],
                "confidence": 0.72 if evidence_ids else 0.35,
                "risk_level": "low",
            }
        )
    return insights


def profile_feature_names(profile: dict) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for feature in profile.get("features", []):
        name = feature.get("name", "unknown")
        if not name or name == "unknown":
            continue
        label = canonical_feature_label(str(name))
        key = normalize_feature_name(label)
        if key in seen:
            continue
        seen.add(key)
        names.append(label)
    return names


def summarize_pricing(profile: dict) -> str:
    pricing = profile.get("pricing", [])
    if not pricing:
        return "unknown"
    value = pricing[0].get("price") or "unknown"
    if value == "unknown":
        return "unknown"
    observed = re.sub(r"^observed price signals:\s*", "", str(value), flags=re.I)
    if observed != value:
        return f"已观察到价格信号：{observed}"
    if value == "needs live price verification":
        return "需要实时价格验证"
    return str(value)


def readable_positioning_summary(name: str, profile: dict, features: list[str]) -> str:
    category = profile.get("product_category") or "unknown category"
    users = "、".join(profile.get("target_users", [])[:3]) or "目标用户未确认"
    feature_text = "、".join(features[:4]) if features else "能力信号不足"
    source_coverage = "、".join(profile.get("source_coverage", [])[:4]) or "unknown"
    if "laptop" in category:
        return f"{name} 是面向 {users} 的笔记本电脑竞品，本轮证据主要覆盖 {feature_text}，来源覆盖 {source_coverage}。"
    return f"{name} 属于 {category}，面向 {users}，本轮证据主要覆盖 {feature_text}，来源覆盖 {source_coverage}。"


def first_pricing_value(profile: dict, key: str) -> str | None:
    pricing = profile.get("pricing", [])
    if not pricing:
        return None
    value = pricing[0].get(key)
    return str(value) if value else None


def profile_evidence_ids(profile: dict, section: str) -> list[str]:
    if section == "pricing":
        return flatten_ids(profile.get("pricing", []))
    if section == "features":
        return flatten_ids(profile.get("features", []))
    return profile.get("positioning", {}).get("evidence_ids", [])


def confidence_from_evidence(ids: list[str]) -> float:
    if not ids:
        return 0.1
    return round(min(0.88, 0.5 + 0.1 * len(ids)), 2)


def flatten_ids(items: list[object]) -> list[str]:
    ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for evidence_id in item.get("evidence_ids", []):
            text = str(evidence_id)
            if text and text not in ids:
                ids.append(text)
    return ids


def infer_best_fit(name: str, profile: dict, features: list[str]) -> str:
    category = profile.get("product_category", "")
    lower_name = name.lower()
    if "laptop" in category:
        if "macbook" in lower_name:
            return "重视 macOS 生态、轻薄续航、静音体验的用户。"
        if any(keyword in name for keyword in ["战", "ThinkBook", "惠普"]):
            return "偏商务办公、稳定性、售后和企业采购的人群。"
        if any(keyword in name for keyword in ["机械", "游戏", "ROG"]):
            return "更关注性能释放和性价比的用户。"
        return "主流办公、学习和轻内容创作用户。"
    target = "、".join(profile.get("target_users", [])[:3]) or "目标用户"
    if features:
        return f"适合需要 {', '.join(features[:3])} 的{target}。"
    return f"适合范围仍需验证的{target}。"


def summarize_card_risk(gaps: list[dict], evidence: list[Evidence]) -> str:
    if any(gap.get("severity") == "high" for gap in gaps):
        return "证据覆盖不足，相关结论需要低置信度处理。"
    if any(item.source_type == "search_snippet" for item in evidence):
        return "部分来源来自搜索摘要，需回源验证。"
    if gaps:
        return gaps[0]["gap"]
    return "暂无明显证据缺口，但价格和口碑仍应临近决策前刷新。"


def competitor_recommendation(name: str, profile: dict, gaps: list[dict]) -> str:
    if any(gap.get("severity") == "high" for gap in gaps):
        return f"先补齐 {name} 的可靠来源，再纳入强对比结论。"
    features = profile_feature_names(profile)
    if features:
        return f"把 {', '.join(features[:3])} 作为 {name} 的重点验证维度。"
    return f"继续采集 {name} 的定位、价格和用户反馈证据。"


def dedupe_claim_dicts(claims: list[dict]) -> list[dict]:
    result = []
    seen: set[str] = set()
    for claim in claims:
        key = normalize_text(str(claim.get("claim_text", ""))).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(claim)
    return result


def dedupe_insights(insights: list[dict]) -> list[dict]:
    result = []
    seen: set[str] = set()
    for insight in insights:
        key = normalize_text(str(insight.get("claim", ""))).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(insight)
    return result


def sanitize_evidence_ids(values: object, valid_ids: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    result = []
    for value in values:
        text = str(value)
        if text in valid_ids and text not in result:
            result.append(text)
    return result


def normalize_claim_type(value: str) -> str:
    value = value.strip().lower()
    if value in {"fact", "inference", "recommendation", "opportunity", "unknown"}:
        return value
    return "inference"


def normalize_risk(value: str) -> str:
    value = value.strip().lower()
    if value in {"low", "medium", "high"}:
        return value
    return "medium"


def clamp_float(value: object, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    return round(max(low, min(high, number)), 2)


def normalize_feature_name(value: str) -> str:
    return re.sub(r"\s+", " ", canonical_feature_label(value).strip().lower())


def canonical_feature_label(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    lowered = text.casefold()
    rules = [
        (r"camera|imaging|photo|photography|影像|拍照|相机|摄像|镜头|长焦|主摄", "影像能力"),
        (r"chip|chipset|performance|processor|cpu|gpu|性能|芯片|处理器|算力", "性能与芯片"),
        (r"display|screen|refresh|屏幕|显示|刷新率|亮度|分辨率", "屏幕显示"),
        (r"battery|charging|charge|续航|电池|快充|充电", "续航与充电"),
        (r"os|ecosystem|ios|android|harmonyos|hyperos|originos|coloros|系统|生态|互联", "系统与生态"),
        (r"price|value|pricing|cost|性价比|价格|定价|渠道|优惠", "价格与性价比"),
        (r"design|durability|weight|material|ip68|外观|设计|机身|重量|耐用|防水", "设计与耐用性"),
        (r"connectivity|satellite|5g|wifi|通信|信号|卫星", "通信能力"),
        (r"\bai\b|artificial intelligence|智能|大模型|端侧模型", "AI能力"),
        (r"after.?sales|service|warranty|support|售后|保修|服务", "售后服务"),
        (r"port|接口|扩展|usb|thunderbolt|hdmi", "接口与扩展"),
        (r"cooling|thermal|heat|散热|发热|温控", "散热与稳定性"),
        (r"portability|portable|lightweight|便携|轻薄", "便携性"),
        (r"software|app|workflow|automation|协作|工作流|自动化", "工作流与自动化"),
        (r"security|compliance|permission|权限|安全|合规", "安全与治理"),
        (r"integration|api|plugin|集成|开放平台|生态连接", "集成与开放性"),
    ]
    for pattern, label in rules:
        if re.search(pattern, lowered, flags=re.I):
            return label
    return text


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_companies(query: str) -> list[str]:
    if is_auto_discovery_query(query):
        return []
    parsed = parse_delimited_competitors(query)
    known = ordered_known_competitor_matches(query)
    if parsed:
        return dedupe_companies([*parsed, *known])[:20]
    return dedupe_companies(known)[:20]


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
        r"(?:竞品|竞争产品|对标对象)\s*[:：]\s*([^。；\n]+)",
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


def is_auto_discovery_query(query: str) -> bool:
    return bool(re.search(r"(?:AI|模型|系统)?\s*(?:自动|自行|帮我)?\s*(?:选择|发现|推荐|找出)\s*\d*\s*个?\s*(?:合适|主要|核心|头部)?\s*竞品", query, flags=re.I))


def is_invalid_competitor_name(value: object) -> bool:
    text = normalize_text(str(value or ""))
    if not text:
        return True
    invalid_patterns = [
        r"自动选择",
        r"AI\s*自动",
        r"合适竞品",
        r"竞品数量",
        r"分析任务",
        r"其他说明",
        r"报告视角",
        r"请分析",
        r"由\s*AI",
    ]
    return any(re.search(pattern, text, flags=re.I) for pattern in invalid_patterns)


def is_plausible_company_name(value: str) -> bool:
    if not (1 < len(value) <= 48):
        return False
    bad_terms = ["领域", "市场", "赛道", "视角", "报告", "格局", "不指定", "竞品分析", "价格", "用户口碑", "自动选择", "合适竞品"]
    if any(term in value for term in bad_terms):
        return False
    if is_invalid_competitor_name(value):
        return False
    if re.fullmatch(r"(AI|SaaS|CRM|Agent|产品经理|投资人|技术)", value, flags=re.I):
        return False
    return bool(re.search(r"[A-Za-z0-9\u4e00-\u9fff]", value))


def dedupe_companies(names: list[str]) -> list[str]:
    normalized_aliases = {
        "可灵": "Kling",
        "秘塔": "秘塔 AI 搜索",
        "macbook air": "MacBook Air",
        "macbook pro": "MacBook Pro",
        "荣耀magicbook": "荣耀MagicBook",
    }
    result: list[str] = []
    seen: set[str] = set()
    for name in names:
        value = normalized_aliases.get(name, normalized_aliases.get(name.lower(), name)).strip()
        key = re.sub(r"\s+", " ", value.lower())
        if not key or key in seen:
            continue
        if any(key in existing and len(key) < len(existing) for existing in seen):
            continue
        shorter_existing = {existing for existing in seen if existing in key and len(existing) < len(key)}
        if shorter_existing:
            seen -= shorter_existing
            result = [item for item in result if re.sub(r"\s+", " ", item.lower()) not in shorter_existing]
        seen.add(key)
        result.append(value)
    return result


def infer_industry(query: str) -> str:
    lower = query.lower()
    if any(keyword in query for keyword in ["手机", "智能手机", "安卓", "旗舰机", "影像旗舰"]) or any(
        keyword in lower for keyword in ["smartphone", "phone", "iphone", "android"]
    ):
        return "smartphone / consumer electronics"
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


def select_evidence_candidate_chunks(
    chunks: list[Chunk],
    documents: dict[str, Document],
    max_per_competitor: int = 10,
    max_total: int = 40,
) -> list[Chunk]:
    grouped: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        document = documents.get(chunk.document_id)
        if not document or not chunk.text.strip():
            continue
        competitor = str(chunk.chunk_metadata.get("competitor", "unknown") or "unknown")
        grouped[competitor].append(chunk)

    selected: list[Chunk] = []
    seen_ids: set[str] = set()
    for competitor in sorted(grouped):
        ranked = sorted(grouped[competitor], key=lambda item: evidence_candidate_score(item, documents), reverse=True)
        competitor_selected: list[Chunk] = []
        seen_signatures: set[str] = set()
        required_source_types = ["official", "pricing", "review", "news", "docs", "changelog"]

        for source_type in required_source_types:
            for chunk in ranked:
                if len(competitor_selected) >= max_per_competitor:
                    break
                if canonical_source_type(chunk.chunk_metadata.get("source_type")) != source_type:
                    continue
                if add_candidate_chunk(chunk, competitor_selected, seen_ids, seen_signatures):
                    break

        for chunk in ranked:
            if len(competitor_selected) >= max_per_competitor:
                break
            add_candidate_chunk(chunk, competitor_selected, seen_ids, seen_signatures)
        selected.extend(competitor_selected)

    if len(selected) <= max_total:
        return selected
    by_competitor: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in selected:
        by_competitor[str(chunk.chunk_metadata.get("competitor", "unknown") or "unknown")].append(chunk)
    final: list[Chunk] = []
    per_competitor = max(4, max_total // max(1, len(by_competitor)))
    for competitor in sorted(by_competitor):
        final.extend(by_competitor[competitor][:per_competitor])
    if len(final) < max_total:
        final_ids = {chunk.id for chunk in final}
        for chunk in selected:
            if chunk.id not in final_ids:
                final.append(chunk)
                final_ids.add(chunk.id)
            if len(final) >= max_total:
                break
    return final[:max_total]


def add_candidate_chunk(chunk: Chunk, selected: list[Chunk], seen_ids: set[str], seen_signatures: set[str]) -> bool:
    if chunk.id in seen_ids:
        return False
    signature = evidence_text_signature(chunk.text)
    if signature and signature in seen_signatures:
        return False
    seen_ids.add(chunk.id)
    if signature:
        seen_signatures.add(signature)
    selected.append(chunk)
    return True


def evidence_candidate_score(chunk: Chunk, documents: dict[str, Document]) -> tuple[int, int, int, int]:
    document = documents.get(chunk.document_id)
    source_type = canonical_source_type(chunk.chunk_metadata.get("source_type", document.source_type if document else "unknown"))
    source_priority = {
        "official": 90,
        "pricing": 86,
        "docs": 80,
        "changelog": 76,
        "review": 72,
        "news": 68,
        "github": 64,
        "search_snippet": 35,
        "crawl_failed": 10,
        "unverified": 8,
    }.get(source_type, 45)
    text = chunk.text
    signal_score = evidence_signal_score(text)
    length_score = min(80, len(text) // 12)
    position_score = max(0, 50 - int(chunk.start_char or 0) // 240)
    return (source_priority, signal_score, length_score, position_score)


def evidence_signal_score(text: str) -> int:
    patterns = [
        r"价格|售价|报价|pricing|price|¥|￥|元",
        r"功能|feature|支持|能力|自动化|看板|任务|协作|屏幕|续航|影像|芯片|性能",
        r"用户|评价|review|评分|口碑|投诉|优点|缺点",
        r"官方|发布|更新|changelog|release|安全|集成|API",
        r"客户|案例|市场|份额|增长|渠道|生态|伙伴",
    ]
    score = 0
    for pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            score += 20
    return score


def evidence_text_signature(text: str) -> str:
    normalized = re.sub(r"\W+", "", text.lower())[:180]
    return normalized


async def build_llm_evidence_annotations(
    project: dict,
    intent: dict,
    chunks: list[Chunk],
    documents: dict[str, Document],
    context: AgentContext,
) -> dict[str, dict[str, Any]]:
    usable_chunks = [chunk for chunk in chunks if chunk.document_id in documents and chunk.text.strip()]
    if not usable_chunks:
        raise ValueError("EvidenceBuilderAgent has no usable chunks to evaluate.")
    annotations: dict[str, dict[str, Any]] = {}
    for batch in batch_sequence(usable_chunks, 10):
        payload = await context.complete_json(
            evidence_selection_prompt(project, intent, batch, documents),
            EVIDENCE_SELECTION_SCHEMA,
            max_tokens=3600,
        )
        for item in payload.get("evidence", []):
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id") or "").strip()
            if chunk_id:
                annotations[chunk_id] = item
    expected_ids = {chunk.id for chunk in usable_chunks}
    missing = sorted(expected_ids - set(annotations))
    if missing:
        chunk_by_id = {chunk.id: chunk for chunk in usable_chunks}
        for chunk_id in missing:
            chunk = chunk_by_id.get(chunk_id)
            if chunk:
                annotations[chunk_id] = default_evidence_annotation(chunk, documents)
    return annotations


def evidence_selection_prompt(project: dict, intent: dict, chunks: list[Chunk], documents: dict[str, Document]) -> str:
    chunk_payload = []
    for chunk in chunks:
        document = documents[chunk.document_id]
        cleaning = chunk.chunk_metadata.get("llm_cleaning", {}) if isinstance(chunk.chunk_metadata, dict) else {}
        chunk_payload.append(
            {
                "chunk_id": chunk.id,
                "competitor": chunk.chunk_metadata.get("competitor", "unknown"),
                "source_type": canonical_source_type(chunk.chunk_metadata.get("source_type", document.source_type)),
                "source_title": document.title,
                "source_url": document.url,
                "document_cleaning": {
                    "is_relevant": cleaning.get("is_relevant"),
                    "information_density": cleaning.get("information_density"),
                    "key_facts": cleaning.get("key_facts", [])[:5] if isinstance(cleaning.get("key_facts"), list) else [],
                    "summary": cleaning.get("summary"),
                },
                "text": compact_quote(chunk.text, max_len=650),
            }
        )
    return f"""
Select and summarize evidence from document chunks for a competitive-intelligence report.

Language: {project.get("language", "zh-CN")}
User task: {project.get("query")}
Parsed intent: {json.dumps(intent, ensure_ascii=False)}

Return exactly one JSON item for every input chunk_id.

Rules:
- keep=true only when the chunk contains useful factual evidence about the competitor, category, price, feature, positioning, review sentiment, channel, technology, or market signal.
- For every competitor in this batch, keep at least one best available factual chunk when any chunk contains source-grounded product, pricing, feature, positioning, review, channel, technology, or market information.
- keep=false for navigation text, cookie text, empty snippets, unrelated content, duplicate boilerplate, or generic search-result glue.
- quote must be a short source-grounded snippet from the chunk text. Do not invent wording, specs, prices, dates, rankings, market share, or citations.
- summary must be a concise Chinese evidence summary, not a broad conclusion.
- credibility_score and freshness_score must be between 0 and 1.
- evidence_type should be one of: feature, pricing, positioning, user_voice, technology, gtm, market_signal, risk, source_context, unknown.
- claim_area should name the comparison dimension this evidence can support.
- is_primary_source should be true for official/pricing/docs/changelog pages when the content actually comes from that source.
- is_potentially_outdated should be true for crawl failures, search snippets, weak pages, old news, or volatile price/spec claims.

Chunks:
{json.dumps(chunk_payload, ensure_ascii=False)}
"""


def default_evidence_annotation(chunk: Chunk, documents: dict[str, Document]) -> dict[str, Any]:
    document = documents.get(chunk.document_id)
    source_type = canonical_source_type(chunk.chunk_metadata.get("source_type", document.source_type if document else "unknown"))
    return {
        "chunk_id": chunk.id,
        "keep": True,
        "claim_area": "source coverage",
        "evidence_type": "source_context",
        "quote": compact_quote(chunk.text, max_len=520),
        "summary": summarize_text(chunk.text, max_len=220),
        "credibility_score": min(0.68, credibility_score(source_type)),
        "freshness_score": 0.55 if source_type in {"unverified", "crawl_failed", "search_snippet"} else 0.75,
        "is_primary_source": source_type in {"official", "pricing", "docs", "changelog"},
        "is_potentially_outdated": source_type in {"unverified", "crawl_failed", "search_snippet"},
        "risk_note": "LLM evidence annotation omitted this chunk; kept a source-grounded default annotation for coverage and downstream QA.",
    }


def batch_sequence(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def evidence_quote_from_annotation(annotation: dict[str, Any], chunk_text_value: str) -> str:
    quote = compact_quote(annotation.get("quote", ""), max_len=520)
    text = normalize_for_match(chunk_text_value)
    if quote and normalize_for_match(quote) in text:
        return quote
    if quote and len(quote) >= 24 and any(part and part in text for part in normalize_for_match(quote).split(" ")[:8]):
        return quote
    return compact_quote(chunk_text_value)


def evidence_summary_from_annotation(annotation: dict[str, Any], chunk_text_value: str) -> str:
    summary = compact_quote(annotation.get("summary", ""), max_len=260)
    if summary and summary.lower() != "unknown":
        return summary
    return summarize_text(chunk_text_value)


def ensure_evidence_competitor_coverage(
    context: AgentContext,
    chunks: list[Chunk],
    documents: dict[str, Document],
    evidence_items: list[dict],
    evidence_by_competitor: dict[str, list[str]],
    annotations: dict[str, dict[str, Any]],
    min_items_per_competitor: int = 2,
) -> list[dict]:
    competitors = sorted(
        {
            str(chunk.chunk_metadata.get("competitor", "")).strip()
            for chunk in chunks
            if str(chunk.chunk_metadata.get("competitor", "")).strip()
            and str(chunk.chunk_metadata.get("competitor", "")).strip() != "unknown"
        }
    )
    coverage_counts: Counter[str] = Counter()
    for item in evidence_items:
        metadata = item.get("metadata", {})
        if isinstance(metadata, dict):
            competitor = str(metadata.get("competitor", "")).strip()
            if competitor:
                coverage_counts[competitor] += 1
    undercovered = [competitor for competitor in competitors if coverage_counts[competitor] < min_items_per_competitor]
    repairs: list[dict] = []
    if not undercovered:
        return repairs

    chunks_by_competitor: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        competitor = str(chunk.chunk_metadata.get("competitor", "unknown") or "unknown")
        chunks_by_competitor[competitor].append(chunk)

    existing_ids = {item.get("evidence_id") for item in evidence_items}
    for competitor in undercovered:
        ranked = sorted(chunks_by_competitor.get(competitor, []), key=lambda item: evidence_candidate_score(item, documents), reverse=True)
        target_count = min_items_per_competitor
        for chunk in ranked[: max(4, target_count + 2)]:
            if coverage_counts[competitor] >= target_count:
                break
            document = documents.get(chunk.document_id)
            if not document:
                continue
            evidence_id = stable_id("ev", context.project_id, chunk.id)
            if evidence_id in existing_ids:
                continue
            source_type = canonical_source_type(chunk.chunk_metadata.get("source_type", document.source_type))
            annotation = annotations.get(chunk.id, {})
            quote = evidence_quote_from_annotation(annotation, chunk.text)
            summary = evidence_summary_from_annotation(annotation, chunk.text)
            credibility = min(
                bounded_score(annotation.get("credibility_score"), credibility_score(source_type)),
                0.72,
            )
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
                summary=summary,
                credibility_score=credibility,
                freshness_score=bounded_score(annotation.get("freshness_score"), 0.55),
                is_primary_source=bool(annotation.get("is_primary_source", source_type in {"official", "pricing", "docs", "changelog"})),
                is_potentially_outdated=True
                if source_type in {"unverified", "crawl_failed", "search_snippet"}
                else bool(annotation.get("is_potentially_outdated", False)),
                supports_claim_ids=[],
                evidence_metadata={
                    "competitor": competitor,
                    "coverage_repair": {
                        "used": True,
                        "reason": "LLM evidence selection dropped every candidate for this competitor; kept the strongest real source chunk to preserve competitor coverage.",
                        "llm_keep": annotation.get("keep"),
                        "llm_risk_note": annotation.get("risk_note"),
                    },
                    "llm_evidence": {
                        "used": bool(annotation),
                        "claim_area": annotation.get("claim_area"),
                        "evidence_type": annotation.get("evidence_type"),
                        "risk_note": annotation.get("risk_note"),
                    },
                },
                retrieved_at=utc_now(),
            )
            context.db.add(evidence)
            item = evidence_to_dict(evidence)
            evidence_items.append(item)
            evidence_by_competitor[competitor].append(evidence_id)
            existing_ids.add(evidence_id)
            coverage_counts[competitor] += 1
            repairs.append({"competitor": competitor, "evidence_id": evidence_id, "chunk_id": chunk.id, "source_type": source_type})
    return repairs


def bounded_score(value: object, default: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, round(score, 2)))


def normalize_for_match(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def validate_llm_evidence_coverage(chunks: list[Chunk], evidence_items: list[dict], allow_repaired: bool = False) -> None:
    if not evidence_items:
        raise ValueError("EvidenceBuilderAgent LLM did not keep any evidence items.")
    competitors = {chunk.chunk_metadata.get("competitor", "unknown") for chunk in chunks if chunk.chunk_metadata.get("competitor")}
    covered = {item.get("metadata", {}).get("competitor") for item in evidence_items if isinstance(item.get("metadata"), dict)}
    missing = sorted(str(name) for name in competitors - covered if name and name != "unknown")
    if missing and not allow_repaired:
        raise ValueError(f"EvidenceBuilderAgent LLM did not keep evidence for competitors: {missing[:6]}")


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


def validate_crawl_coverage(results: list[dict], documents: list[dict]) -> None:
    if results and not documents:
        raise RuntimeError("WebCrawlerAgent could not fetch any live documents from the search results.")
    expected_competitors = {str(result.get("competitor", "")).strip() for result in results if result.get("competitor")}
    covered_competitors = {str(document.get("competitor", "")).strip() for document in documents if document.get("competitor")}
    missing = sorted(expected_competitors - covered_competitors)
    if missing:
        raise RuntimeError(f"WebCrawlerAgent did not fetch usable documents for competitors: {missing[:6]}")
    if len(documents) < min(len(results), max(2, len(expected_competitors))):
        raise RuntimeError(f"WebCrawlerAgent fetched too few usable documents: {len(documents)} of {len(results)} candidates.")


def sanitize_document_text(document: dict) -> dict:
    sanitized = dict(document)
    for key in ["url", "title", "content", "competitor", "source_type"]:
        if key in sanitized:
            sanitized[key] = strip_db_forbidden_chars(sanitized.get(key, ""))
    sanitized["content"] = normalize_crawled_content(sanitized.get("content", ""))
    metadata = sanitized.get("metadata", {})
    if isinstance(metadata, dict):
        sanitized["metadata"] = sanitize_json_text(metadata)
    else:
        sanitized["metadata"] = {}
    sanitized["metadata"] = {
        **sanitized["metadata"],
        "cleaning": {
            "stage": "web_crawler",
            "method": "deterministic_text_normalization",
            "content_quality": crawled_content_quality(sanitized.get("content", "")),
        },
    }
    content = sanitized.get("content", "")
    sanitized["content_hash"] = hashlib.sha256(str(content).encode("utf-8")).hexdigest()
    return sanitized


def normalize_crawled_content(text: object) -> str:
    lines = []
    seen: set[str] = set()
    for line in str(text or "").replace("\x00", "").splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        if not normalized:
            continue
        signature = normalized.casefold()
        if signature in seen and len(normalized) < 160:
            continue
        seen.add(signature)
        lines.append(normalized)
    return "\n".join(lines)


def crawled_content_quality(text: str) -> str:
    if len(text) > 1200:
        return "rich"
    if len(text) > 320:
        return "usable"
    if len(text) > 80:
        return "thin"
    return "noise"


def strip_db_forbidden_chars(value: object) -> str:
    text = str(value or "")
    return text.replace("\x00", "")


def sanitize_json_text(value: object) -> object:
    if isinstance(value, str):
        return strip_db_forbidden_chars(value)
    if isinstance(value, dict):
        return {strip_db_forbidden_chars(key): sanitize_json_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_text(item) for item in value]
    return value


def build_profile(project_id: str, competitor: str, docs: list[dict], industry: str = "") -> dict:
    combined = "\n".join(doc["content"] for doc in docs)
    source_urls = [doc["url"] for doc in docs]
    source_types = {canonical_source_type(doc.get("source_type", "unknown")) for doc in docs}
    features = extract_features(project_id, competitor, combined, industry)
    pricing = extract_pricing(project_id, combined, bool(source_types & {"pricing"}), industry)
    return {
        "competitor_id": stable_id("comp", project_id, competitor),
        "name": competitor,
        "aliases": [],
        "company_name": competitor.replace(" AI", ""),
        "website": next((url for url in source_urls if not url.startswith("offline://")), source_urls[0] if source_urls else None),
        "founded_year": None,
        "headquarters": None,
        "company_stage": "unknown",
        "product_category": infer_product_category(combined, industry),
        "target_users": infer_target_users(combined, industry),
        "target_industries": [],
        "regions": [],
        "business_model": infer_business_model(combined, industry),
        "positioning": {
            "short_summary": summarize_text(combined),
            "long_summary": summarize_text(combined, max_len=520),
            "evidence_ids": [],
        },
        "features": features,
        "pricing": pricing,
        "integrations": extract_integrations(combined, industry),
        "security_compliance": extract_security(combined),
        "user_feedback": extract_user_feedback(combined),
        "market_signals": extract_market_signals(combined),
        "technical_signals": extract_technical_signals(combined, industry),
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
        "source_coverage": sorted(source_types),
        "last_updated": iso_now(),
    }


def extract_features(project_id: str, competitor: str, text: str, industry: str = "") -> list[dict]:
    lowered = text.lower()
    if is_smartphone_domain(industry, text):
        candidates = [
            ("Camera / imaging", "camera", ["camera", "摄像", "影像", "镜头", "长焦", "潜望", "光学变焦", "ois", "哈苏", "徕卡", "zeiss", "蔡司"]),
            ("Chipset / performance", "performance", ["chip", "processor", "cpu", "gpu", "a16", "a17", "snapdragon", "骁龙", "天玑", "kirin", "麒麟", "性能"]),
            ("Display quality", "display", ["display", "screen", "oled", "amoled", "ltpo", "刷新率", "高刷", "亮度", "屏幕", "分辨率"]),
            ("Battery / charging", "battery", ["battery", "电池", "续航", "快充", "charging", "mah", "w"]),
            ("OS / ecosystem", "ecosystem", ["ios", "android", "harmonyos", "hyperos", "originos", "coloros", "系统", "生态"]),
            ("Design / durability", "design", ["weight", "厚度", "重量", "防水", "ip68", "玻璃", "钛", "机身", "手感"]),
            ("Storage / memory", "storage", ["storage", "rom", "ram", "内存", "存储", "gb", "tb"]),
            ("Connectivity / satellite", "connectivity", ["5g", "wifi", "bluetooth", "nfc", "satellite", "卫星", "通信"]),
            ("Price / value", "pricing", ["price", "价格", "售价", "¥", "￥", "6000", "性价比", "促销"]),
            ("AI features", "ai", ["ai", "智能", "大模型", "端侧", "aigc"]),
        ]
    elif is_laptop_domain(industry, text):
        candidates = [
            ("Performance / CPU-GPU", "hardware", ["processor", "cpu", "gpu", "core", "酷睿", "ryzen", "锐龙", "m1", "m2", "m3", "m4", "snapdragon", "性能", "显卡"]),
            ("Display quality", "display", ["display", "screen", "retina", "oled", "ips", "2.5k", "3k", "屏幕", "分辨率", "刷新率", "高刷", "nits", "护眼"]),
            ("Battery life", "battery", ["battery", "电池", "续航", "快充", "hours", "wh"]),
            ("Thermals / noise", "thermal", ["thermal", "cooling", "fan", "noise", "散热", "风扇", "噪音"]),
            ("Portability / weight", "design", ["thin", "light", "portable", "air", "kg", "轻薄", "重量", "便携"]),
            ("Memory / storage", "hardware", ["memory", "ram", "storage", "ssd", "内存", "硬盘", "512gb", "1tb", "gb"]),
            ("Ports / connectivity", "connectivity", ["usb", "type-c", "thunderbolt", "hdmi", "wi-fi", "wifi", "接口", "雷电", "蓝牙"]),
            ("After-sales / warranty", "service", ["warranty", "support", "service", "售后", "保修", "服务", "意外险"]),
            ("Price / value", "pricing", ["price", "pricing", "¥", "￥", "6000", "价格", "报价", "售价", "促销", "性价比", "优惠"]),
            ("AI / NPU capability", "hardware_ai", ["ai pc", "copilot", "npu", "tops", "apple intelligence", "神经网络", "ai+"]),
        ]
    else:
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
            display_name = canonical_feature_label(name)
            features.append(
                {
                    "feature_id": stable_id("feat", project_id, competitor, display_name),
                    "name": display_name,
                    "category": category,
                    "description": f"Evidence text contains public signals for {display_name}.",
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


def extract_pricing(project_id: str, text: str, has_pricing_source: bool, industry: str = "") -> list[dict]:
    if is_laptop_domain(industry, text) or is_smartphone_domain(industry, text):
        prices = extract_price_amounts(text)
        price = "unknown"
        if prices:
            price = "observed price signals: " + ", ".join(f"¥{amount}" for amount in prices[:5])
        elif has_pricing_source:
            price = "needs live price verification"
        cycle = "one-time hardware purchase"
        segment = "consumer electronics buyers"
        if is_smartphone_domain(industry, text):
            segment = "smartphone buyers"
        return [
            {
                "plan_name": "market price signal",
                "price": price,
                "currency": "CNY" if prices else None,
                "billing_cycle": cycle,
                "target_segment": segment,
                "included_features": [],
                "limitations": ["Live marketplace prices fluctuate and must be rechecked before purchase decisions."],
                "evidence_ids": [],
            }
        ]
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


def infer_target_users(text: str, industry: str = "") -> list[str]:
    if is_smartphone_domain(industry, text):
        users = ["mainstream consumers"]
        if re.search(r"影像|拍照|camera|creator|创作|摄影", text, re.I):
            users.append("mobile photography users")
        if re.search(r"游戏|gaming|performance|性能", text, re.I):
            users.append("mobile gamers")
        if re.search(r"商务|office|办公|enterprise", text, re.I):
            users.append("office users")
        return dedupe_text(users)
    if is_laptop_domain(industry, text):
        users = ["consumers"]
        if re.search(r"学生|校园|education|student", text, re.I):
            users.append("students")
        if re.search(r"商务|办公|office|business|enterprise|企业", text, re.I):
            users.append("office workers")
        if re.search(r"创作|creator|creative|proart|设计", text, re.I):
            users.append("creators")
        if re.search(r"游戏|gaming|电竞|rog", text, re.I):
            users.append("gamers")
        return dedupe_text(users)
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


def infer_business_model(text: str, industry: str = "") -> list[str]:
    if is_smartphone_domain(industry, text):
        models = ["hardware retail"]
        if re.search(r"官方商城|官网|store|shop|直营", text, re.I):
            models.append("direct sales")
        if re.search(r"京东|天猫|渠道|dealer|retailer|商城", text, re.I):
            models.append("channel retail")
        if re.search(r"运营商|carrier|合约", text, re.I):
            models.append("carrier bundles")
        return dedupe_text(models)
    if is_laptop_domain(industry, text):
        models = ["hardware retail"]
        if re.search(r"官方商城|官网|store|shop|直营", text, re.I):
            models.append("direct sales")
        if re.search(r"京东|天猫|苏宁|渠道|dealer|retailer|商城", text, re.I):
            models.append("channel retail")
        if re.search(r"企业购|enterprise|business", text, re.I):
            models.append("enterprise procurement")
        return dedupe_text(models)
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


def extract_integrations(text: str, industry: str = "") -> list[dict]:
    if is_laptop_domain(industry, text):
        return []
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


def extract_technical_signals(text: str, industry: str = "") -> list[dict]:
    lowered = text.lower()
    if is_smartphone_domain(industry, text):
        signals = []
        for signal_type, keyword in [
            ("camera_system", r"camera|摄像|影像|镜头|长焦|ois|哈苏|徕卡|zeiss|蔡司"),
            ("chipset", r"chip|processor|cpu|gpu|a1[6-9]|snapdragon|骁龙|天玑|kirin|麒麟"),
            ("display", r"display|oled|ltpo|屏幕|刷新率|亮度"),
            ("battery_charging", r"battery|电池|续航|快充|charging|mah"),
            ("os_ecosystem", r"ios|android|harmonyos|hyperos|originos|coloros|系统|生态"),
            ("connectivity", r"5g|nfc|satellite|卫星|wifi|bluetooth"),
            ("ai_on_device", r"\bai\b|大模型|端侧|智能"),
        ]:
            if re.search(keyword, lowered, re.I):
                signals.append(
                    {
                        "signal_type": signal_type,
                        "description": f"Current evidence contains a {signal_type} smartphone signal.",
                        "confidence": 0.65,
                        "evidence_ids": [],
                    }
                )
        return signals
    if is_laptop_domain(industry, text):
        signals = []
        for signal_type, keyword in [
            ("processor", r"processor|cpu|酷睿|ryzen|锐龙|m[1-4]"),
            ("graphics", r"gpu|显卡|geforce|radeon|arc"),
            ("display", r"display|oled|retina|屏幕|分辨率|刷新率"),
            ("battery", r"battery|续航|电池"),
            ("thermal_design", r"thermal|cooling|散热|风扇"),
            ("ai_acceleration", r"npu|tops|copilot|apple intelligence|ai pc"),
        ]:
            if re.search(keyword, lowered, re.I):
                signals.append(
                    {
                        "signal_type": signal_type,
                        "description": f"Current evidence contains a {signal_type} hardware signal.",
                        "confidence": 0.65,
                        "evidence_ids": [],
                    }
                )
        return signals
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


def infer_product_category(text: str, industry: str = "") -> str:
    if is_smartphone_domain(industry, text):
        return "smartphone / consumer electronics"
    if is_laptop_domain(industry, text):
        return "laptop computer / consumer electronics"
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


def is_laptop_domain(industry: str, text: str = "") -> bool:
    lower_industry = industry.lower()
    if "laptop" in lower_industry or "notebook" in lower_industry or "笔记本" in industry or "电脑" in industry:
        return True
    return bool(re.search(r"笔记本|轻薄本|游戏本|全能本|macbook|laptop|notebook", text, re.I))


def is_smartphone_domain(industry: str, text: str = "") -> bool:
    lower_industry = industry.lower()
    if "smartphone" in lower_industry or "phone" in lower_industry or "手机" in industry:
        return True
    return bool(re.search(r"智能手机|手机|旗舰机|iphone|android|harmonyos|骁龙|天玑|影像旗舰", text, re.I))


def extract_price_amounts(text: str) -> list[int]:
    amounts: list[int] = []
    seen: set[int] = set()
    for match in re.finditer(r"(?:¥|￥|rmb|cny)?\s*([2-9]\d{3}|1\d{4}|2\d{4})(?:\s*元)?", text, flags=re.I):
        amount = int(match.group(1))
        if amount < 2500 or amount > 25000:
            continue
        context = text[max(0, match.start() - 16) : match.end() + 16]
        if not re.search(r"¥|￥|元|价格|报价|售价|到手|促销|优惠|price|from|起", context, flags=re.I):
            continue
        if amount in seen:
            continue
        seen.add(amount)
        amounts.append(amount)
    return amounts


def dedupe_text(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


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


def canonical_source_type(value: object) -> str:
    normalized = str(value or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "official_spec": "official",
        "official_specs": "official",
        "official_page": "official",
        "official_product": "official",
        "official_spec_pricing": "official",
        "official_specs_pricing": "official",
        "official_price": "pricing",
        "product_page": "official",
        "price": "pricing",
        "pricing_channel": "pricing",
        "channel_pricing": "pricing",
        "current_pricing_channel": "pricing",
        "latest_pricing_channel": "pricing",
        "commerce": "pricing",
        "ecommerce": "pricing",
        "third_party_review": "review",
        "third_party_reviews": "review",
        "user_review": "review",
        "user_reviews": "review",
        "market_news": "news",
        "media_news": "news",
        "forum": "review",
        "community": "review",
        "social": "review",
        "ecosystem_experience": "review",
    }
    if normalized in aliases:
        return aliases[normalized]
    if "pricing" in normalized or "price" in normalized or "channel" in normalized:
        return "pricing"
    if "official" in normalized or "spec" in normalized or "product" in normalized:
        return "official"
    if "review" in normalized or "feedback" in normalized or "experience" in normalized or "forum" in normalized:
        return "review"
    if "news" in normalized or "market" in normalized:
        return "news"
    return normalized or "unknown"


def credibility_score(source_type: str) -> float:
    source_type = canonical_source_type(source_type)
    return {
        "official": 0.9,
        "pricing": 0.88,
        "docs": 0.86,
        "github": 0.82,
        "review": 0.7,
        "news": 0.72,
        "changelog": 0.8,
        "third_party": 0.65,
        "search_snippet": 0.45,
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


def describe_exception(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message[:320]
    return exc.__class__.__name__


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


def collect_report_runtime_warnings(
    agent_outputs: dict,
    competitors: list[Competitor],
    report_synthesis: dict,
    config: object,
) -> list[str]:
    if should_simulate(config):
        return []
    warnings: list[str] = []

    discovery_payload = agent_outputs.get("competitor_discovery", {}).get("payload", {})
    discovery_reason = discovery_payload.get("discovery_fallback_reason")
    if discovery_reason:
        warnings.append(f"CompetitorDiscoveryAgent 回退到确定性竞品发现：{discovery_reason}")

    source_payload = agent_outputs.get("source_planning", {}).get("payload", {})
    if source_payload and source_payload.get("llm_used") is False:
        reason = source_payload.get("source_planning_fallback_reason") or "LLM source planning was not used."
        warnings.append(f"SourcePlanningAgent 回退到确定性搜索规划：{reason}")

    analysis_source_mix = agent_outputs.get("analysis", {}).get("source_mix", {})
    llm_synthesis = analysis_source_mix.get("llm_synthesis") if isinstance(analysis_source_mix, dict) else {}
    if isinstance(llm_synthesis, dict) and llm_synthesis.get("used") is False and llm_synthesis.get("error"):
        warnings.append(f"AnalysisAgent 回退到确定性综合分析：{llm_synthesis.get('error')}")

    quality_payload = agent_outputs.get("quality_gate", {}).get("payload", {})
    ai_review = quality_payload.get("quality_gate", {}).get("ai_review", {}) if isinstance(quality_payload, dict) else {}
    if isinstance(ai_review, dict) and ai_review.get("used") is False and ai_review.get("error"):
        warnings.append(f"QualityGateAgent 未完成 LLM 质量复核：{ai_review.get('error')}")

    if report_synthesis.get("used") is False and report_synthesis.get("error"):
        warnings.append(f"ReportWriterAgent 回退到模板化报告生成：{report_synthesis.get('error')}")

    failed_profiles = []
    for competitor in competitors:
        extraction = competitor.profile.get("llm_extraction", {})
        if isinstance(extraction, dict) and extraction.get("used") is False:
            failed_profiles.append(f"{competitor.name}: {extraction.get('error') or 'unknown error'}")
    if failed_profiles:
        warnings.append("SchemaExtractionAgent 以下竞品 profile 使用 fallback：" + "；".join(failed_profiles[:5]))
    return dedupe_text(warnings)


def render_markdown(
    project: dict,
    competitors: list[Competitor],
    evidence: list[Evidence],
    claims: list[Claim],
    analysis: dict,
    quality: dict,
    agent_outputs: dict | None = None,
    runtime_warnings: list[str] | None = None,
) -> str:
    agent_outputs = agent_outputs or {}
    runtime_warnings = runtime_warnings or []
    quality_gate = agent_outputs.get("quality_gate", {}).get("payload", {})
    project_id = project.get("project_id", "")
    evidence_by_id = {item.id: item for item in evidence}
    cards = analysis.get("competitor_cards", [])
    comparison_dimensions = analysis.get("comparison_dimensions", [])
    pricing_table = analysis.get("pricing_table", [])
    evidence_gaps = analysis.get("evidence_gaps", [])
    source_mix = analysis.get("source_mix", {})
    gate = quality_gate.get("quality_gate", {})
    warnings = quality_gate.get("warnings", []) or gate.get("warnings", [])
    status = quality_gate.get("status") or gate.get("status", "pass_with_warnings")
    decision_rows = build_decision_rows(cards)
    lines = [
        f"# mira 竞品分析报告",
        "",
        f"**分析任务**：{project['query']}",
        "",
        f"**生成方式**：多 Agent 自动调研与证据约束生成，覆盖任务理解、竞品发现、公开资料采集、结构化抽取、综合判断和质量门禁。",
        "",
    ]
    if runtime_warnings:
        lines.extend(
            [
                "## 运行风险提示",
                "",
                "**本次运行出现 LLM 调用失败或回退。fallback 结果只适合作为调试线索，不应作为正式竞品分析结论使用。**",
                "",
            ]
        )
        for warning in runtime_warnings[:8]:
            lines.append(f"- {warning}")
        lines.append("")
    lines.extend(
        [
        "## 执行摘要",
        "",
        executive_summary_text(project, competitors, evidence, analysis, quality, status, source_mix),
        "",
        "### 本报告适合怎么用",
        "",
        "- 用作首轮竞品筛选、对标维度设计和后续人工验证清单。",
        "- 对价格、用户口碑、参数细节等高波动信息，按「下一步验证清单」在决策前刷新。",
        "- 对证据不足的判断，不应直接进入对外材料或不可逆决策。",
        "",
        "## 决策建议",
        "",
        ]
    )
    if decision_rows:
        lines.append("| 优先级 | 竞品角色 | 竞品 | 为什么值得看 | 主要不确定性 | 证据 |")
        lines.append("|---:|---|---|---|---|---|")
        for index, row in enumerate(decision_rows, start=1):
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(index),
                        markdown_cell(row["role"]),
                        markdown_cell(row["name"]),
                        markdown_cell(row["why"]),
                        markdown_cell(row["uncertainty"]),
                        markdown_cell(citation_list(row.get("evidence_ids", []), project_id, evidence_by_id, limit=2)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("当前证据不足，无法形成明确优先级建议。")

    lines.extend(
        [
        "",
        "## 关键结论",
        "",
        ]
    )
    for line in render_insight_blocks(analysis.get("strategic_insights", [])[:6], project_id, evidence_by_id):
        lines.append(line)
    if not analysis.get("strategic_insights"):
        lines.extend(render_claim_lines([claim for claim in claims if claim.claim_type in {"inference", "recommendation", "opportunity"}][:6], project_id, evidence_by_id))

    lines.extend(["", "## 事实结论", ""])
    fact_claims = [claim for claim in claims if claim.claim_type in {"fact", "unknown"}][:8]
    if fact_claims:
        lines.append("| 事实/缺口 | 对报告的意义 | 证据 |")
        lines.append("|---|---|---|")
        for claim in fact_claims:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(claim.claim_text),
                        markdown_cell(claim_implication(claim)),
                        markdown_cell(citation_list(claim.evidence_ids, project_id, evidence_by_id)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("当前没有足够证据生成事实类结论。")

    lines.extend(["", "## 竞品对比表", ""])
    if cards:
        lines.append("| 竞品 | 对标角色 | 适合场景 | 核心信号 | 主要风险 | 建议动作 |")
        lines.append("|---|---|---|---|---|---|")
        row_by_name = {row["name"]: row for row in decision_rows}
        for card in cards:
            row = row_by_name.get(card.get("name", ""), {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(card.get("name", "unknown")),
                        markdown_cell(row.get("role", infer_competitor_role(card, 0))),
                        markdown_cell(card.get("best_for", "unknown")),
                        markdown_cell("、".join(card.get("strongest_signals", [])[:5]) or "unknown"),
                        markdown_cell(card.get("watch_out", "unknown")),
                        markdown_cell(card.get("recommendation", "继续补充证据后复核。")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("当前证据不足，无法形成竞品对比表。")

    lines.extend(["", "## 功能/能力矩阵", ""])
    feature_matrix = analysis.get("feature_matrix", {})
    competitor_names = [competitor.name for competitor in competitors]
    if feature_matrix and competitor_names:
        lines.append("| 维度 | " + " | ".join(markdown_cell(name) for name in competitor_names) + " |")
        lines.append("|---|" + "|".join("---" for _ in competitor_names) + "|")
        for feature, values in list(feature_matrix.items())[:8]:
            cells = []
            for competitor in competitor_names:
                item = values.get(competitor, {})
                evidence_ids = item.get("evidence_ids", [])
                cells.append(markdown_cell(matrix_cell_label(item) + (f" ({citation_list(evidence_ids, project_id, evidence_by_id)})" if evidence_ids else "")))
            lines.append("| " + markdown_cell(feature) + " | " + " | ".join(cells) + " |")
    else:
        lines.append("当前证据不足，能力矩阵为 unknown。")

    if comparison_dimensions:
        lines.extend(["", "### 如何解读这些维度", ""])
        for item in comparison_dimensions:
            lines.append(
                f"- **{item.get('dimension')}**：{item.get('support_count')}/{item.get('competitor_count')} 个竞品出现信号。"
                f"{item.get('interpretation')}"
            )

    lines.extend(["", "## 定价与商业化信号", ""])
    if pricing_table:
        lines.append("| 竞品 | 价格/商业化信号 | 置信度 | 注意事项 | 证据 |")
        lines.append("|---|---|---:|---|---|")
        for row in pricing_table:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(row.get("competitor", "unknown")),
                        markdown_cell(row.get("pricing_signal", "unknown")),
                        f"{float(row.get('confidence', 0)):.2f}",
                        markdown_cell(row.get("caveat", "需要刷新验证")),
                        markdown_cell(citation_list(row.get("evidence_ids", []), project_id, evidence_by_id)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("未采集到足够价格/商业化信号。")

    lines.extend(["", "## 单个竞品解读", ""])
    for card in cards[:8]:
        lines.extend(
            [
                f"### {card.get('name', 'unknown')}",
                "",
                f"{card.get('positioning', 'unknown')}",
                "",
                f"- **适合场景**：{card.get('best_for', 'unknown')}",
                f"- **重点信号**：{'、'.join(card.get('strongest_signals', [])[:5]) or 'unknown'}",
                f"- **需要警惕**：{card.get('watch_out', 'unknown')}",
                f"- **建议动作**：{card.get('recommendation', 'unknown')}",
                f"- **支撑证据**：{citation_list(card.get('evidence_ids', []), project_id, evidence_by_id)}",
                "",
            ]
        )

    lines.extend(["## 证据质量与风险", ""])
    if source_mix:
        lines.append(f"- **来源结构**：{source_mix_sentence(source_mix)}。")
        lines.append(f"- **证据规模**：共 {len(evidence)} 条证据，覆盖 {len(competitors)} 个竞品。")
        lines.append(f"- **质量状态**：{status}，综合评分 {quality['total']}/100。")
    for warning in warnings:
        lines.append(f"- 质量门禁：{warning}")
    if evidence_gaps:
        for gap in evidence_gaps[:12]:
            lines.append(
                f"- **{gap.get('competitor', 'unknown')}**：{gap.get('gap', 'unknown')} "
                f"[severity={gap.get('severity', 'medium')}; 建议：{gap.get('recommended_action', '补充证据')}]"
            )
    if not warnings and not evidence_gaps:
        lines.append("- 暂无高风险证据缺口，但仍建议在正式决策前刷新价格、用户评价和最新更新。")

    lines.extend(["", "## 下一步验证清单", ""])
    for action in verification_actions(evidence_gaps):
        lines.append(f"- {action}")
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
    appendix_items = report_evidence_items(evidence)
    for item in appendix_items:
        label = readable_evidence_label(item)
        summary = readable_evidence_summary(item)
        lines.append(
            f"- **{label}**："
            f"[证据页](/projects/{project_id}/evidence/{item.id}) / [原文]({item.source_url}) | "
            f"可信度 {item.credibility_score:.2f} | 新鲜度 {item.freshness_score:.2f} | 摘要：{summary}"
        )
    if len(evidence) > len(appendix_items):
        lines.append(f"- 其余 {len(evidence) - len(appendix_items)} 条证据可在项目的「证据」页面继续查看。")
    lines.extend(
        [
            "",
            "## Agent 执行说明",
            "",
            "本报告由 IntentAgent、PlannerAgent、CompetitorDiscoveryAgent、SourcePlanningAgent、WebSearchAgent、WebCrawlerAgent、SchemaExtractionAgent、EvidenceBuilderAgent、AnalysisAgent、QualityGateAgent 和 ReportWriterAgent 生成。"
            "生产模式会调用配置的搜索 API 和 LLM API；网页抓取遵守 robots.txt、限速和失败降级策略。",
        ]
    )
    return "\n".join(lines)


def executive_summary_text(
    project: dict,
    competitors: list[Competitor],
    evidence: list[Evidence],
    analysis: dict,
    quality: dict,
    status: str,
    source_mix: dict,
) -> str:
    cards = analysis.get("competitor_cards", [])
    decision_rows = build_decision_rows(cards)
    leading_names = "、".join(row["name"] for row in decision_rows[:3]) or "暂无明确短名单"
    top_insight = ""
    insights = analysis.get("strategic_insights", [])
    if insights:
        top_insight = normalize_text(str(insights[0].get("claim", "")))
    if not top_insight:
        top_insight = "当前证据更适合支持首轮筛选和后续验证设计，而不是直接形成最终采购/产品战略结论。"
    return (
        f"本次报告围绕「{compact_quote(project.get('query', ''), max_len=90)}」展开，"
        f"共分析 {len(competitors)} 个竞品、整理 {len(evidence)} 条证据，来源结构为 {source_mix_sentence(source_mix)}。"
        f"当前最值得优先阅读和复核的对象是：{leading_names}。"
        f"核心判断是：{top_insight} "
        f"综合质量评分为 {quality['total']}/100，状态为 {status}；因此本报告适合作为决策前的高质量草案，"
        "但涉及价格、具体参数和口碑的部分仍需临近决策前刷新。"
    )


def build_decision_rows(cards: list[dict]) -> list[dict]:
    ranked = sorted(
        [card for card in cards if isinstance(card, dict)],
        key=decision_card_score,
        reverse=True,
    )
    rows: list[dict] = []
    for index, card in enumerate(ranked):
        name = normalize_text(str(card.get("name", "unknown")))
        if not name:
            continue
        signals = "、".join(card.get("strongest_signals", [])[:3]) if isinstance(card.get("strongest_signals"), list) else ""
        best_for = normalize_text(str(card.get("best_for") or "适合场景仍需补充证据。"))
        why_parts = [part for part in [best_for, f"核心信号：{signals}" if signals else ""] if part]
        rows.append(
            {
                "name": name,
                "role": infer_competitor_role(card, index),
                "why": compact_quote("；".join(why_parts), max_len=220),
                "uncertainty": compact_quote(str(card.get("watch_out") or "价格、口碑和最新变化需要刷新验证。"), max_len=180),
                "evidence_ids": card.get("evidence_ids", []) if isinstance(card.get("evidence_ids"), list) else [],
            }
        )
    return rows


def decision_card_score(card: dict) -> float:
    score = float(card.get("evidence_count") or 0)
    if isinstance(card.get("strongest_signals"), list):
        score += 0.8 * len(card["strongest_signals"])
    if isinstance(card.get("evidence_ids"), list):
        score += 0.6 * len(card["evidence_ids"])
    risk_text = str(card.get("watch_out") or "")
    if re.search(r"不足|失败|缺少|unknown|低置信|兜底|无法", risk_text, re.I):
        score -= 2.0
    return score


def infer_competitor_role(card: dict, rank: int) -> str:
    name = str(card.get("name") or "")
    risk_text = str(card.get("watch_out") or "")
    signals = " ".join(card.get("strongest_signals", [])) if isinstance(card.get("strongest_signals"), list) else ""
    if re.search(r"iphone|apple|苹果", name, re.I):
        return "跨生态标杆"
    if re.search(r"价格|性价比|value", signals, re.I):
        return "价格/价值标杆"
    if re.search(r"不足|失败|缺少|unknown|低置信|兜底|无法", risk_text, re.I):
        return "待补证观察"
    if rank == 0:
        return "首轮重点对标"
    if rank <= 2:
        return "重点备选"
    return "补充观察"


def render_insight_blocks(insights: list[dict], project_id: str, evidence_by_id: dict[str, Evidence]) -> list[str]:
    if not insights:
        return []
    labels = {
        "fact": "事实判断",
        "inference": "综合判断",
        "recommendation": "行动建议",
        "opportunity": "机会判断",
        "unknown": "待验证判断",
    }
    blocks: list[str] = []
    for index, insight in enumerate(insights, start=1):
        kind = normalize_claim_type(str(insight.get("type", "inference")))
        claim = normalize_text(str(insight.get("claim") or "unknown"))
        basis = normalize_text(str(insight.get("basis") or "来自多源证据综合。"))
        confidence = float(insight.get("confidence", 0) or 0)
        risk = normalize_risk(str(insight.get("risk_level", "medium")))
        evidence_text = citation_list(insight.get("evidence_ids", []), project_id, evidence_by_id)
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {labels.get(kind, '综合判断')}",
                    "",
                    claim,
                    "",
                    f"- **为什么重要**：{basis}",
                    f"- **可信度与风险**：{confidence_phrase(confidence)}，风险为{risk_label(risk)}",
                    f"- **支撑证据**：{evidence_text}",
                    "",
                ]
            )
        )
    return blocks


def claim_implication(claim: Claim) -> str:
    if claim.claim_type == "unknown":
        return "该项不能作为强结论，需要补证或人工复核。"
    if claim.risk_level == "high":
        return "方向有参考价值，但风险高，决策前必须复核。"
    if not claim.evidence_ids:
        return "缺少引用支撑，只能作为低置信度线索。"
    return "可作为当前报告的支撑事实，但高波动信息仍需刷新。"


def matrix_cell_label(item: dict) -> str:
    if not item or not item.get("support"):
        return "待验证"
    maturity = str(item.get("maturity", "medium")).lower()
    if maturity in {"high", "strong", "mature"}:
        return "强信号"
    if maturity in {"low", "weak"}:
        return "弱信号"
    return "有信号"


def scope_sentence(project: dict, competitors: list[Competitor]) -> str:
    names = "、".join(competitor.name for competitor in competitors) or "未确认竞品"
    return f"{names}；原始任务为「{compact_quote(project.get('query', ''), max_len=120)}」。"


def source_mix_sentence(source_mix: dict) -> str:
    counts = source_mix.get("source_types", {}) if isinstance(source_mix, dict) else {}
    if not counts:
        return "unknown"
    normalized_counts: Counter[str] = Counter()
    for source_type, count in counts.items():
        normalized_counts[canonical_source_type(source_type)] += int(count)
    labels = {
        "official": "官方/规格",
        "pricing": "价格/渠道",
        "docs": "文档/参数",
        "review": "评测/用户反馈",
        "news": "新闻/市场",
        "changelog": "更新/发布",
        "search_snippet": "搜索摘要",
        "unverified": "未验证",
        "crawl_failed": "抓取失败",
    }
    ordered = sorted(normalized_counts.items(), key=lambda item: (-int(item[1]), item[0]))
    return "，".join(f"{labels.get(source_type, source_type)} {count}" for source_type, count in ordered[:6])


REPORT_TEXT_REPLACEMENTS = {
    "mainstream consumers": "主流消费者",
    "office users": "办公用户",
    "mobile photography users": "移动影像用户",
    "mobile gamers": "手游用户",
    "consumer electronics buyers": "消费电子用户",
    "smartphone buyers": "手机用户",
    "unknown": "待确认",
    "needs live price verification": "需要实时价格验证",
}


def report_display_text(value: str) -> str:
    text = value
    for source, target in REPORT_TEXT_REPLACEMENTS.items():
        text = re.sub(re.escape(source), target, text, flags=re.I)
    text = re.sub(r"\s*,\s*", "、", text)
    return text


def confidence_phrase(confidence: float) -> str:
    if confidence >= 0.75:
        return "较高"
    if confidence >= 0.5:
        return "中等"
    return "较低"


def risk_label(value: str) -> str:
    labels = {"low": "低", "medium": "中", "high": "高"}
    return labels.get(value, value)


def markdown_cell(value: object) -> str:
    text = normalize_text(report_display_text(str(value if value is not None else "unknown")))
    text = text.replace("|", " / ")
    return text or "unknown"


def verification_actions(evidence_gaps: list[dict]) -> list[str]:
    actions = []
    for gap in evidence_gaps:
        action = str(gap.get("recommended_action", "")).strip()
        if action and action not in actions:
            actions.append(action)
    defaults = [
        "刷新每个竞品的官方产品页、价格页和最新发布信息。",
        "补充第三方评测、用户评论或社区讨论，避免只依赖官方营销表述。",
        "对报告中的低置信度结论进行人工复核，再进入业务决策或对外材料。",
    ]
    for action in defaults:
        if action not in actions:
            actions.append(action)
    return actions[:6]


def report_evidence_items(evidence: list[Evidence], limit: int = 36) -> list[Evidence]:
    selected: list[Evidence] = []
    seen_ids: set[str] = set()
    grouped: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.evidence_metadata.get("competitor", "unknown")].append(item)
    for competitor in sorted(grouped):
        ranked = sorted(grouped[competitor], key=lambda item: (item.source_type in {"search_snippet", "unverified", "crawl_failed"}, -item.credibility_score))
        for item in ranked[:4]:
            if item.id not in seen_ids:
                selected.append(item)
                seen_ids.add(item.id)
    if len(selected) < limit:
        for item in sorted(evidence, key=lambda item: (-item.credibility_score, item.source_type)):
            if item.id in seen_ids:
                continue
            selected.append(item)
            seen_ids.add(item.id)
            if len(selected) >= limit:
                break
    return selected[:limit]


def render_claim_lines(claims: list[Claim], project_id: str = "", evidence_by_id: dict[str, Evidence] | None = None) -> list[str]:
    if not claims:
        return ["- unknown：当前没有足够证据生成该类结论。"]
    lines = []
    for claim in claims:
        evidence_text = citation_list(claim.evidence_ids, project_id, evidence_by_id)
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


def citation_list(evidence_ids: list[str], project_id: str = "", evidence_by_id: dict[str, Evidence] | None = None, limit: int = 3) -> str:
    if not evidence_ids:
        return "unknown"
    if not project_id:
        return ", ".join(evidence_ids[:limit])
    citations = []
    visible_ids = evidence_ids[: max(1, limit)]
    for evidence_id in visible_ids:
        evidence = evidence_by_id.get(evidence_id) if evidence_by_id else None
        label = readable_evidence_label(evidence) if evidence else evidence_id
        citations.append(f"[{markdown_link_label(label)}](/projects/{project_id}/evidence/{evidence_id})")
    if len(evidence_ids) > len(visible_ids):
        citations.append(f"另 {len(evidence_ids) - len(visible_ids)} 条")
    return ", ".join(citations)


def make_citations_readable(markdown: str, evidence: list[Evidence], project_id: str) -> str:
    if not markdown or not evidence or not project_id:
        return markdown
    by_id = {item.id: item for item in evidence}
    result = markdown
    for evidence_id, item in sorted(by_id.items(), key=lambda pair: len(pair[0]), reverse=True):
        label = markdown_link_label(readable_evidence_label(item))
        result = re.sub(
            rf"\[{re.escape(evidence_id)}\]\(([^)]*{re.escape(evidence_id)}[^)]*)\)",
            rf"[{label}](\1)",
            result,
        )

    def replace_bare_id(match: re.Match[str]) -> str:
        evidence_id = match.group(0)
        item = by_id.get(evidence_id)
        if not item:
            return evidence_id
        label = markdown_link_label(readable_evidence_label(item))
        return f"[{label}](/projects/{project_id}/evidence/{evidence_id})"

    return re.sub(r"(?<![A-Za-z0-9_./-])ev_[a-z0-9]+(?![A-Za-z0-9_-])", replace_bare_id, result)


def readable_evidence_label(evidence: Evidence | None) -> str:
    if evidence is None:
        return "证据来源"
    competitor = clean_label_part(evidence.evidence_metadata.get("competitor")) or "综合"
    source = source_type_readable(evidence.source_type)
    title = readable_source_title(evidence)
    parts = [competitor, source]
    if title and title.casefold() not in {competitor.casefold(), source.casefold()}:
        parts.append(title)
    return "｜".join(parts[:3])


def readable_evidence_summary(evidence: Evidence) -> str:
    summary = compact_quote(evidence.summary or evidence.quote or "", max_len=180)
    if not summary or looks_mojibake(summary):
        return "该来源文本质量较差，建议打开证据页或原文核验。"
    return summary


def readable_source_title(evidence: Evidence) -> str:
    title = clean_label_part(evidence.source_title)
    if not title or title.lower() == "untitled" or looks_mojibake(title):
        title = clean_label_part(evidence.publisher) or domain_from_url(evidence.source_url)
    title = re.sub(r"[-_丨|｜]\s*(官网|官方商城|官方|首页)\s*$", "", title, flags=re.I).strip()
    return compact_quote(title, max_len=34)


def source_type_readable(source_type: str) -> str:
    labels = {
        "official": "官方",
        "pricing": "价格",
        "docs": "参数",
        "review": "评测",
        "news": "新闻",
        "changelog": "更新",
        "github": "开源",
        "third_party": "第三方",
        "search_snippet": "搜索摘要",
        "unverified": "待核验",
        "crawl_failed": "抓取失败",
    }
    return labels.get(canonical_source_type(source_type), canonical_source_type(source_type) or "来源")


def clean_label_part(value: object) -> str:
    text = normalize_text(str(value or ""))
    text = text.replace("|", "｜").replace("[", "【").replace("]", "】")
    text = re.sub(r"\s+", " ", text).strip(" -_｜")
    return text


def markdown_link_label(value: str) -> str:
    return clean_label_part(value).replace("(", "（").replace(")", "）") or "证据来源"


def looks_mojibake(text: str) -> bool:
    if not text:
        return False
    if "�" in text or "��" in text:
        return True
    suspicious = sum(text.count(marker) for marker in ["Ã", "Â", "ð", "½", "¼"])
    return suspicious >= 3


def domain_from_url(url: str) -> str:
    match = re.match(r"https?://([^/]+)", str(url or ""))
    return match.group(1) if match else "来源"


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
