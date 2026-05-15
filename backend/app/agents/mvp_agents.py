from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from sqlalchemy import delete, select

from app.agents.base import AgentContext, BaseAgent
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
]

MVP_TASKS = [
    {"id": "intent", "agent": "IntentAgent", "depends_on": [], "priority": 1},
    {"id": "planner", "agent": "PlannerAgent", "depends_on": ["intent"], "priority": 2},
    {"id": "web_search", "agent": "WebSearchAgent", "depends_on": ["planner"], "priority": 3},
    {"id": "web_crawler", "agent": "WebCrawlerAgent", "depends_on": ["web_search"], "priority": 4},
    {"id": "schema_extraction", "agent": "SchemaExtractionAgent", "depends_on": ["web_crawler"], "priority": 5},
    {"id": "evidence_builder", "agent": "EvidenceBuilderAgent", "depends_on": ["schema_extraction"], "priority": 6},
    {"id": "analysis", "agent": "AnalysisAgent", "depends_on": ["evidence_builder"], "priority": 7},
    {"id": "report_writer", "agent": "ReportWriterAgent", "depends_on": ["analysis"], "priority": 8},
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
    description = "Plan the MVP DAG and retry policy."
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
                "notes": "MVP path can be extended with parallel analysis and QA nodes.",
            },
            "tasks": tasks,
        }


class WebSearchAgent(BaseAgent):
    name = "WebSearchAgent"
    description = "Collect candidate public sources for each target competitor."
    output_model = SearchResultsOutput

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        intent = input_data["dependency_outputs"].get("intent") or input_data.get("memory", {}).get("intent", {})
        competitors = intent.get("target_companies") or []
        if not competitors:
            competitors = [intent.get("analysis_topic") or input_data["project"]["query"]]

        all_results: list[dict] = []
        seen_urls: set[str] = set()
        for competitor in competitors:
            queries = [
                f"{competitor} official product features pricing",
                f"{competitor} user reviews security integrations",
            ]
            for query in queries[:1 if context.config.offline_mode else 2]:
                result = await context.call_tool(
                    "web_search",
                    {
                        "query": query,
                        "competitor": competitor,
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
        results = search_output.get("search_results", [])[: context.config.max_crawl_documents]
        documents: list[dict] = []
        for result in results:
            crawled = await context.call_tool(
                "web_crawler",
                {
                    "url": result["url"],
                    "competitor": result.get("competitor", "unknown"),
                    "source_type": result.get("source_type", "unknown"),
                },
            )
            document = crawled["document"]
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
        docs_output = input_data["dependency_outputs"].get("web_crawler", {})
        documents = docs_output.get("documents", [])
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
                freshness_score=0.95,
                is_primary_source=source_type in {"official", "pricing", "docs"},
                is_potentially_outdated=document.url.startswith("offline://"),
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
        evidence_by_competitor: dict[str, list[str]] = defaultdict(list)
        for item in evidence:
            competitor = item.evidence_metadata.get("competitor", "unknown")
            evidence_by_competitor[competitor].append(item.id)

        claims: list[dict] = []
        feature_matrix: dict[str, dict[str, dict]] = {}
        all_features = sorted({feature["name"] for c in competitors for feature in c.profile.get("features", [])})
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
                matched = next((item for item in profile.get("features", []) if item["name"] == feature), None)
                feature_matrix[feature][competitor.name] = {
                    "support": bool(matched),
                    "maturity": matched.get("maturity", "unknown") if matched else "unknown",
                    "evidence_ids": matched.get("evidence_ids", []) if matched else [],
                }

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
        analysis = input_data["dependency_outputs"].get("analysis", {})
        quality = compute_quality_score(competitors, evidence, claims)
        markdown = render_markdown(project, competitors, evidence, claims, analysis, quality)
        json_report = {
            "project_id": context.project_id,
            "summary": "Evidence-bound MVP competitive analysis report.",
            "competitors": [competitor.profile for competitor in competitors],
            "feature_matrix": analysis.get("feature_matrix", {}),
            "strategic_insights": analysis.get("strategic_insights", []),
            "claims": [claim_to_dict(claim) for claim in claims],
            "evidence": [evidence_to_dict(item) for item in evidence],
            "quality_score": quality,
        }
        rendered = await context.call_tool("report_renderer", {"markdown": markdown, "json_report": json_report})

        report_id = stable_id("report", context.project_id, "markdown")
        upsert_report(context, report_id, "markdown", rendered["markdown"], {"quality_score": quality})
        upsert_report(context, stable_id("report", context.project_id, "html"), "html", rendered["html"], {"quality_score": quality})
        upsert_report(context, stable_id("report", context.project_id, "json"), "json", rendered["json"], {"quality_score": quality})
        context.db.commit()
        return {
            "report_id": report_id,
            "markdown": rendered["markdown"],
            "html": rendered["html"],
            "json_report": json_report,
            "quality_score": quality,
        }


def extract_companies(query: str) -> list[str]:
    found: list[str] = []
    lower_query = query.lower()
    for name in KNOWN_COMPETITORS:
        if name.lower() in lower_query or name in query:
            found.append(name)
    if found:
        return found
    maybe_segment = re.search(r"(?:包括|分析|对比)([^，。；\n]+)", query)
    if maybe_segment:
        tokens = re.split(r"[、,，/和与]", maybe_segment.group(1))
        return [token.strip() for token in tokens if 1 < len(token.strip()) < 40][:8]
    return []


def infer_industry(query: str) -> str:
    if "Agent" in query or "agent" in query:
        return "AI Agent infrastructure / development platform"
    if "办公" in query or "协作" in query or "productivity" in query.lower():
        return "AI productivity / collaboration software"
    if "知识库" in query:
        return "AI knowledge base / knowledge management"
    if "代码" in query or "coding" in query.lower():
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
        "product_category": "AI product / productivity platform",
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
        "market_signals": [],
        "technical_signals": extract_technical_signals(combined),
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
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
    if not has_pricing_source and not re.search(r"price|pricing|价格|paid|free|enterprise", text, re.I):
        return []
    return [
        {
            "plan_name": "public pricing signal",
            "price": "unknown",
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
    if "review" not in text.lower() and "用户" not in text and "negative" not in text.lower():
        return {"pros": [], "cons": []}
    return {
        "pros": [
            {"theme": "breadth of capability", "summary": "Positive review signal found.", "frequency": None, "sentiment": "positive", "evidence_ids": []}
        ],
        "cons": [
            {"theme": "complexity or verification needed", "summary": "Negative or cautionary review signal found.", "frequency": None, "sentiment": "negative", "evidence_ids": []}
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


def credibility_score(source_type: str) -> float:
    return {
        "official": 0.9,
        "pricing": 0.88,
        "docs": 0.86,
        "github": 0.82,
        "review": 0.7,
        "news": 0.72,
        "third_party": 0.65,
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
    coverage_ratio = min(1.0, len(evidence) / (competitor_count * 3))
    evidence_ratio = sum(1 for claim in claims if claim.evidence_ids) / max(1, len(claims))
    citation_accuracy = 1.0 if all(claim.evidence_ids or claim.claim_type == "unknown" for claim in claims) else 0.5
    analysis_depth = min(1.0, len(claims) / max(1, competitor_count + 2))
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


def render_markdown(project: dict, competitors: list[Competitor], evidence: list[Evidence], claims: list[Claim], analysis: dict, quality: dict) -> str:
    lines = [
        f"# CompeteScope AI 竞品分析报告",
        "",
        f"**分析任务**：{project['query']}",
        "",
        f"**生成方式**：MVP DAG 自动生成，事实、推断和建议分区展示；所有非 unknown 结论绑定 evidence_ids。",
        "",
        "## 执行摘要",
        "",
        f"- 已结构化竞品：{len(competitors)} 个。",
        f"- 已构建证据：{len(evidence)} 条。",
        f"- 质量评分：{quality['total']}/100。",
        "",
        "## 事实结论",
        "",
    ]
    facts = [claim for claim in claims if claim.claim_type in {"fact", "unknown"}]
    lines.extend(render_claim_lines(facts))
    lines.extend(["", "## 推断", ""])
    lines.extend(render_claim_lines([claim for claim in claims if claim.claim_type == "inference"]))
    lines.extend(["", "## 建议", ""])
    lines.extend(render_claim_lines([claim for claim in claims if claim.claim_type == "recommendation"]))
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
                f"[证据: {', '.join(profile.get('positioning', {}).get('evidence_ids', [])) or 'unknown'}]",
                f"- 功能信号：{feature_names}",
                f"- 价格信号：{pricing_text}",
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
                cells.append(("支持" if item.get("support") else "unknown") + (f" ({', '.join(evidence_ids)})" if evidence_ids else ""))
            lines.append("| " + feature + " | " + " | ".join(cells) + " |")
    else:
        lines.append("当前证据不足，功能矩阵为 unknown。")
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
            f"- `{item.id}`: {item.source_title} | {item.source_url} | "
            f"可信度 {item.credibility_score:.2f} | 新鲜度 {item.freshness_score:.2f} | 摘要：{item.summary}"
        )
    lines.extend(
        [
            "",
            "## Agent 执行说明",
            "",
            "本报告由 IntentAgent、PlannerAgent、WebSearchAgent、WebCrawlerAgent、SchemaExtractionAgent、EvidenceBuilderAgent、AnalysisAgent 和 ReportWriterAgent 顺序生成。"
            "MVP 默认使用离线 fixture 以便本地稳定测试；生产模式应配置合规搜索 API，并保持 robots.txt 检查、速率限制和访问控制合规。",
        ]
    )
    return "\n".join(lines)


def render_claim_lines(claims: list[Claim]) -> list[str]:
    if not claims:
        return ["- unknown：当前没有足够证据生成该类结论。"]
    lines = []
    for claim in claims:
        evidence_text = ", ".join(claim.evidence_ids) if claim.evidence_ids else "unknown"
        lines.append(
            f"- **{claim.claim_type}**：{claim.claim_text} "
            f"[confidence: {claim.confidence:.2f}; risk: {claim.risk_level}; 证据: {evidence_text}]"
        )
    return lines


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
