from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent
from app.config import should_simulate
from app.core.ids import stable_id
from app.core.time import iso_now
from app.db.models import Claim, Competitor, Evidence
from app.schemas.agent_io import GenericAgentOutput


class DeepSpecializedAgent(BaseAgent):
    output_model = GenericAgentOutput
    name = "DeepSpecializedAgent"
    description = "Deep analysis agent with evidence-bound output."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        return self.pack("success", "Agent executed.", [], {})

    def pack(self, status: str, summary: str, evidence_ids: list[str], payload: dict) -> dict:
        return {
            "agent": self.name,
            "status": status,
            "summary": summary,
            "evidence_ids": evidence_ids,
            "payload": payload,
        }

    def load_competitors(self, context: AgentContext) -> list[Competitor]:
        return list(context.db.scalars(select(Competitor).where(Competitor.project_id == context.project_id)).all())

    def load_evidence(self, context: AgentContext) -> list[Evidence]:
        return list(context.db.scalars(select(Evidence).where(Evidence.project_id == context.project_id)).all())

    def evidence_by_competitor(self, evidence: list[Evidence]) -> dict[str, list[Evidence]]:
        grouped: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            grouped[item.evidence_metadata.get("competitor", "unknown")].append(item)
        return grouped

    def ids_for(self, grouped: dict[str, list[Evidence]], competitor_name: str, limit: int = 3) -> list[str]:
        return [item.id for item in grouped.get(competitor_name, [])[:limit]]


class CompetitorDiscoveryAgent(DeepSpecializedAgent):
    name = "CompetitorDiscoveryAgent"
    description = "Discover direct, indirect, substitute and emerging competitors."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        intent = collect_outputs(input_data).get("intent", {})
        project = input_data.get("project", {})
        max_count = int(project.get("max_competitors") or 6)
        explicit_competitors = normalize_competitor_names(intent.get("target_companies") or [], max_count)
        llm_details: list[dict[str, Any]] = []
        fallback_reason = ""

        competitors = explicit_competitors
        if not competitors and not should_simulate(context.config):
            try:
                llm_payload = await context.complete_json(
                    competitor_discovery_prompt(project, intent, max_count),
                    COMPETITOR_DISCOVERY_SCHEMA,
                )
                competitors = normalize_competitor_names(llm_payload.get("competitors") or [], max_count)
                llm_details = normalize_competitor_details(llm_payload.get("competitor_details") or [], competitors)
            except Exception as exc:
                fallback_reason = str(exc)

        if not competitors:
            competitors = normalize_competitor_names(default_competitors(intent.get("industry", "unknown")), max_count)

        details = [
            {
                "name": name,
                "type": "direct",
                "confidence": 0.92 if name in explicit_competitors else 0.72,
                "reason": discovery_reason(name, llm_details, intent),
                "evidence_ids": [],
            }
            for name in competitors
        ]
        payload = {
            "competitors": competitors,
            "competitor_details": details,
            "needs_human_confirmation": not bool(explicit_competitors),
        }
        if fallback_reason:
            payload["discovery_fallback_reason"] = fallback_reason
        return self.pack(
            "success",
            f"Identified {len(competitors)} competitors for downstream source planning.",
            [],
            payload,
        )


class SourcePlanningAgent(DeepSpecializedAgent):
    name = "SourcePlanningAgent"
    description = "Plan official, pricing, docs, review, news, social, GitHub and hiring sources."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        outputs = collect_outputs(input_data)
        competitors = outputs.get("competitor_discovery", {}).get("payload", {}).get("competitors", [])
        intent = outputs.get("intent", {})
        plan = []
        source_types = ["official", "pricing", "docs", "review", "news", "changelog"]
        if "infrastructure" in intent.get("industry", "").lower() or "open" in intent.get("industry", "").lower():
            source_types.append("github")
        for competitor in competitors:
            for source_type in source_types:
                plan.append(
                    {
                        "competitor": competitor,
                        "source_type": source_type,
                        "query": source_query(competitor, source_type, intent.get("industry", "unknown")),
                        "priority": "high" if source_type in {"official", "pricing"} else "medium",
                    }
                )
        return self.pack("success", f"Planned {len(plan)} public-source searches.", [], {"source_plan": plan})


class DocumentCleanerAgent(DeepSpecializedAgent):
    name = "DocumentCleanerAgent"
    description = "Clean documents, preserve quote locations, chunk content and prepare embeddings."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        docs = collect_outputs(input_data).get("web_crawler", {}).get("documents", [])
        cleaned = []
        for doc in docs:
            parsed = await context.call_tool("document_parser", {"content": doc.get("content", ""), "content_type": "text"})
            text = normalize_text(parsed.get("text", ""))
            cleaned.append(
                {
                    **doc,
                    "content": text,
                    "metadata": {
                        **doc.get("metadata", {}),
                        "cleaned_at": iso_now(),
                        "content_quality": content_quality(text),
                    },
                }
            )
        return self.pack("success", f"Cleaned {len(cleaned)} documents.", [], {"cleaned_documents": cleaned})


class ProductPositioningAgent(DeepSpecializedAgent):
    name = "ProductPositioningAgent"
    description = "Analyze target users, use cases, value proposition and positioning differences."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        analysis = []
        findings = []
        for competitor in competitors:
            profile = competitor.profile
            ids = self.ids_for(grouped, competitor.name)
            features = [feature["name"] for feature in profile.get("features", []) if feature["name"] != "unknown"]
            target_users = profile.get("target_users", ["unknown"])
            differentiation = positioning_sentence(competitor.name, profile, features)
            item = {
                "competitor": competitor.name,
                "target_users": target_users,
                "core_value": profile.get("positioning", {}).get("short_summary", "unknown"),
                "differentiation": differentiation,
                "confidence": confidence_from_evidence(ids),
                "evidence_ids": ids,
            }
            analysis.append(item)
            findings.append(
                finding(
                    self.name,
                    "fact",
                    competitor.name,
                    f"{competitor.name} 的定位信号显示，其主要服务对象是 {', '.join(target_users)}，差异点可概括为：{differentiation}",
                    ids,
                    item["confidence"],
                    "low",
                )
            )
        return self.pack("success", "Positioning analysis completed.", flatten_ids(analysis), {"positioning_analysis": analysis, "findings": findings})


class FeatureMatrixAgent(DeepSpecializedAgent):
    name = "FeatureMatrixAgent"
    description = "Build horizontal feature matrices with evidence-bound support status."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        all_features = sorted({feature["name"] for competitor in competitors for feature in competitor.profile.get("features", []) if feature["name"] != "unknown"})
        matrix: dict[str, dict[str, dict[str, Any]]] = {feature: {} for feature in all_features}
        scores = []
        findings = []
        for competitor in competitors:
            feature_names = {feature["name"]: feature for feature in competitor.profile.get("features", [])}
            ids = self.ids_for(grouped, competitor.name)
            support_count = 0
            for feature in all_features:
                matched = feature_names.get(feature)
                support_count += 1 if matched else 0
                matrix[feature][competitor.name] = {
                    "support": bool(matched),
                    "maturity": matched.get("maturity", "unknown") if matched else "unknown",
                    "evidence_ids": matched.get("evidence_ids", ids[:1]) if matched else [],
                }
            score = round(100 * support_count / max(1, len(all_features)))
            scores.append({"competitor": competitor.name, "feature_breadth_score": score, "supported_features": support_count})
            findings.append(
                finding(
                    self.name,
                    "fact",
                    competitor.name,
                    f"{competitor.name} 在当前证据下覆盖 {support_count}/{max(1, len(all_features))} 个可比功能维度，功能广度评分为 {score}。",
                    ids,
                    confidence_from_evidence(ids),
                    "low",
                )
            )
        return self.pack("success", f"Feature matrix built with {len(all_features)} comparable dimensions.", flatten_ids(findings), {"feature_matrix": matrix, "scores": scores, "findings": findings})


class PricingAnalysisAgent(DeepSpecializedAgent):
    name = "PricingAnalysisAgent"
    description = "Analyze free tiers, paid plans, enterprise pricing and AI charging models."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        table = []
        findings = []
        for competitor in competitors:
            profile = competitor.profile
            pricing = profile.get("pricing", [])
            ids = [item.id for item in grouped.get(competitor.name, []) if item.source_type in {"pricing", "third_party", "official"}][:3]
            price_signal = pricing[0]["price"] if pricing else "unknown"
            model = ", ".join(profile.get("business_model", [])) or "unknown"
            row = {
                "competitor": competitor.name,
                "public_price_signal": price_signal,
                "business_model": model,
                "pricing_risk": "needs_live_verification" if price_signal == "unknown" else "medium",
                "evidence_ids": ids,
            }
            table.append(row)
            findings.append(
                finding(
                    self.name,
                    "fact" if ids else "unknown",
                    competitor.name,
                    f"{competitor.name} 的商业化信号为 {model}，公开价格/收费信号为 {price_signal}。",
                    ids,
                    confidence_from_evidence(ids),
                    "medium" if price_signal == "unknown" else "low",
                )
            )
        insights = [
            {
                "claim": "价格与收费项是当前报告最需要实时刷新验证的维度，尤其是佣金、广告、履约或 AI 附加收费。",
                "confidence": 0.7,
                "evidence_ids": [item.id for item in evidence[:5]],
            }
        ]
        return self.pack("success", "Pricing analysis completed with live-verification flags.", flatten_ids(table), {"pricing_table": table, "insights": insights, "findings": findings})


class UserVoiceAgent(DeepSpecializedAgent):
    name = "UserVoiceAgent"
    description = "Mine reviews and community discussions for pros, cons, pain points and sentiment."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        summaries = []
        findings = []
        for competitor in competitors:
            review_ids = [item.id for item in grouped.get(competitor.name, []) if item.source_type == "review"]
            profile_feedback = competitor.profile.get("user_feedback", {"pros": [], "cons": []})
            has_review = bool(review_ids)
            summary = {
                "competitor": competitor.name,
                "pros": profile_feedback.get("pros", []),
                "cons": profile_feedback.get("cons", []),
                "sentiment_score": 0.64 if has_review else 0.5,
                "evidence_gap": not has_review,
                "evidence_ids": review_ids,
            }
            summaries.append(summary)
            findings.append(
                finding(
                    self.name,
                    "fact" if has_review else "unknown",
                    competitor.name,
                    f"{competitor.name} 的用户声音维度{'已有评论来源支撑' if has_review else '缺少独立评论来源，不能下强结论'}。",
                    review_ids,
                    0.66 if has_review else 0.1,
                    "medium" if not has_review else "low",
                )
            )
        return self.pack("success", "User voice analysis completed with evidence-gap flags.", flatten_ids(summaries), {"user_voice_summary": summaries, "findings": findings})


class TechnologyIntelligenceAgent(DeepSpecializedAgent):
    name = "TechnologyIntelligenceAgent"
    description = "Analyze technology, API, RAG, agent, SDK, infrastructure and security signals."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        analysis = []
        findings = []
        for competitor in competitors:
            signals = competitor.profile.get("technical_signals", [])
            ids = [item.id for item in grouped.get(competitor.name, []) if item.source_type in {"docs", "github", "official"}][:3]
            maturity = maturity_from_signal_count(len(signals))
            analysis.append({"competitor": competitor.name, "tech_stack_signals": signals, "technical_maturity": maturity, "evidence_ids": ids})
            findings.append(
                finding(
                    self.name,
                    "fact" if ids else "unknown",
                    competitor.name,
                    f"{competitor.name} 的技术成熟度在当前公开信号下评估为 {maturity}。",
                    ids,
                    confidence_from_evidence(ids),
                    "medium" if maturity == "unknown" else "low",
                )
            )
        return self.pack("success", "Technology intelligence analysis completed.", flatten_ids(analysis), {"technology_analysis": analysis, "findings": findings})


class GTMAgent(DeepSpecializedAgent):
    name = "GTMAgent"
    description = "Analyze go-to-market strategy, channels, partnerships and customer cases."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        analysis = []
        findings = []
        for competitor in competitors:
            profile = competitor.profile
            ids = self.ids_for(grouped, competitor.name)
            signals = gtm_signals(profile)
            strategy = strategy_from_profile(profile)
            analysis.append({"competitor": competitor.name, "strategy": strategy, "signals": signals, "confidence": confidence_from_evidence(ids), "evidence_ids": ids})
            findings.append(
                finding(
                    self.name,
                    "inference",
                    competitor.name,
                    f"{competitor.name} 的 GTM 更接近“{strategy}”，主要信号包括 {', '.join(signals) or 'unknown'}。",
                    ids,
                    min(0.78, confidence_from_evidence(ids)),
                    "medium",
                )
            )
        return self.pack("success", "GTM analysis completed.", flatten_ids(analysis), {"gtm_analysis": analysis, "findings": findings})


class SWOTAgent(DeepSpecializedAgent):
    name = "SWOTAgent"
    description = "Generate evidence-bound strengths, weaknesses, opportunities and threats."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        swot = {}
        findings = []
        for competitor in competitors:
            profile = competitor.profile
            ids = self.ids_for(grouped, competitor.name)
            feature_count = len([feature for feature in profile.get("features", []) if feature["name"] != "unknown"])
            source_coverage = set(profile.get("source_coverage", []))
            block = {
                "strengths": [
                    {"point": f"已出现 {feature_count} 个能力信号，说明公开资料可支撑基础能力画像。", "evidence_ids": ids[:2], "confidence": confidence_from_evidence(ids)}
                ],
                "weaknesses": [
                    {"point": "用户声音或价格细节不足，部分结论需要实时资料补强。", "evidence_ids": ids[:1], "confidence": 0.55}
                ]
                if not {"review", "pricing"}.issubset(source_coverage)
                else [],
                "opportunities": [
                    {"point": opportunity_from_profile(profile), "evidence_ids": ids[:2], "confidence": 0.62}
                ],
                "threats": [
                    {"point": "强平台型竞品可能通过生态、履约或企业销售形成防御壁垒。", "evidence_ids": ids[:2], "confidence": 0.58}
                ],
            }
            swot[competitor.name] = block
            profile["swot"] = block
            competitor.profile = profile
            findings.append(
                finding(
                    self.name,
                    "inference",
                    competitor.name,
                    f"{competitor.name} 的 SWOT 显示：主要优势是公开能力信号较明确，主要风险是证据覆盖仍需补强。",
                    ids,
                    0.62,
                    "medium",
                )
            )
        context.db.commit()
        return self.pack("success", "SWOT analysis completed and written back to competitor profiles.", flatten_ids(findings), {"swot": swot, "findings": findings})


class StrategicInsightAgent(DeepSpecializedAgent):
    name = "StrategicInsightAgent"
    description = "Generate strategic opportunities, risks, differentiators and recommendations."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        all_ids = [item.id for item in evidence[:8]]
        category_counter = Counter()
        for competitor in competitors:
            for feature in competitor.profile.get("features", []):
                category_counter[feature.get("category", "unknown")] += 1
        sparse_categories = [category for category, count in category_counter.items() if count < max(2, len(competitors) // 2)]
        insights = [
            {
                "type": "opportunity",
                "claim": f"当前竞品在 {', '.join(sparse_categories[:3]) or '可验证差异化能力'} 上的证据密度较低，可作为差异化探索方向。",
                "basis": "FeatureMatrixAgent and SWOTAgent outputs show uneven evidence coverage across comparable dimensions.",
                "evidence_ids": all_ids,
                "confidence": 0.66,
                "risk_level": "medium",
            },
            {
                "type": "recommendation",
                "claim": "下一轮调研应优先补充三类信息：实时价格/收费规则、第三方用户评价、最近 90 天产品更新或商家政策变化。",
                "basis": "QA agents treat stale pricing and missing review evidence as the highest uncertainty drivers.",
                "evidence_ids": all_ids,
                "confidence": 0.74,
                "risk_level": "low",
            },
        ]
        findings = [
            finding(self.name, item["type"], "overall", item["claim"], item["evidence_ids"], item["confidence"], item["risk_level"])
            for item in insights
        ]
        return self.pack("success", "Strategic insight generation completed.", all_ids, {"strategic_insights": insights, "findings": findings})


class FactCheckAgent(DeepSpecializedAgent):
    name = "FactCheckAgent"
    description = "Check fact claims for evidence support, freshness and hallucination risk."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        claims = list(context.db.scalars(select(Claim).where(Claim.project_id == context.project_id)).all())
        evidence_by_id = {item.id: item for item in self.load_evidence(context)}
        issues = []
        for claim in claims:
            if claim.claim_type != "unknown" and not claim.evidence_ids:
                issues.append({"claim_id": claim.id, "issue_type": "missing_evidence", "severity": "high", "message": "Claim has no evidence IDs."})
            if claim.confidence > 0.85 and len(claim.evidence_ids) < 2:
                issues.append({"claim_id": claim.id, "issue_type": "overconfident_claim", "severity": "medium", "message": "High confidence needs multiple sources."})
            weak_ids = [
                evidence_id
                for evidence_id in claim.evidence_ids
                if evidence_by_id.get(evidence_id)
                and (evidence_by_id[evidence_id].source_type in {"unverified", "crawl_failed"} or evidence_by_id[evidence_id].credibility_score < 0.35)
            ]
            if weak_ids and claim.claim_type in {"fact", "inference"}:
                issues.append(
                    {
                        "claim_id": claim.id,
                        "issue_type": "weak_or_unverified_evidence",
                        "severity": "high" if claim.claim_type == "fact" else "medium",
                        "message": f"Claim relies on weak or unverified evidence IDs: {weak_ids}.",
                    }
                )
        return self.pack("success", "Fact check completed.", [], {"fact_check_result": {"passed": not issues, "issues": issues}})


class CitationCheckAgent(DeepSpecializedAgent):
    name = "CitationCheckAgent"
    description = "Check whether each citation supports its linked claim."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        evidence_by_id = {item.id: item for item in self.load_evidence(context)}
        evidence_ids = set(evidence_by_id)
        claims = list(context.db.scalars(select(Claim).where(Claim.project_id == context.project_id)).all())
        checks = []
        for claim in claims:
            missing = [item for item in claim.evidence_ids if item not in evidence_ids]
            support_scores = [
                semantic_support_score(claim.claim_text, evidence_by_id[evidence_id].quote, evidence_by_id[evidence_id].summary)
                for evidence_id in claim.evidence_ids
                if evidence_id in evidence_by_id
            ]
            weak_sources = [
                evidence_id
                for evidence_id in claim.evidence_ids
                if evidence_id in evidence_by_id and evidence_by_id[evidence_id].source_type in {"unverified", "crawl_failed"}
            ]
            max_support = max(support_scores, default=0.0)
            if missing:
                status = "invalid_reference"
                reason = f"Missing evidence IDs: {missing}"
            elif weak_sources:
                status = "weak_support"
                reason = f"Evidence exists but is weak/unverified: {weak_sources}"
            elif claim.claim_type != "unknown" and max_support < 0.08:
                status = "weak_support"
                reason = f"Low lexical-semantic overlap between claim and evidence; support_score={max_support:.2f}"
            elif len(claim.evidence_ids) == 1 and claim.claim_type != "fact":
                status = "weak_support"
                reason = "Only one source supports a non-factual conclusion; add more evidence or lower confidence."
            else:
                status = "supported"
                reason = f"Evidence IDs exist and claim/evidence support_score={max_support:.2f}."
            checks.append(
                {
                    "claim_id": claim.id,
                    "status": status,
                    "reason": reason,
                    "support_score": round(max_support, 2),
                    "recommended_action": "add evidence, refresh live source, or lower confidence" if status != "supported" else "keep citation and refresh volatile sources before external delivery",
                }
            )
        return self.pack("success", "Citation check completed.", [], {"citation_checks": checks})


class ConsistencyCheckAgent(DeepSpecializedAgent):
    name = "ConsistencyCheckAgent"
    description = "Detect contradictions across pricing, feature, SWOT and recommendation sections."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        issues = []
        for competitor in competitors:
            profile = competitor.profile
            if not profile.get("features") and profile.get("positioning", {}).get("evidence_ids"):
                issues.append({"type": "profile_gap", "location_a": "positioning", "location_b": "features", "message": f"{competitor.name} has positioning evidence but no feature extraction."})
        return self.pack("success", "Consistency check completed.", [], {"consistency_issues": issues})


class BiasDetectionAgent(DeepSpecializedAgent):
    name = "BiasDetectionAgent"
    description = "Detect source, competitor, region, segment and over-interpretation bias."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        evidence = self.load_evidence(context)
        source_counter = Counter(item.source_type for item in evidence)
        total = max(1, len(evidence))
        report = []
        official_ratio = (source_counter["official"] + source_counter["docs"] + source_counter["pricing"]) / total
        if official_ratio > 0.7:
            report.append(
                {
                    "bias_type": "source_bias",
                    "description": "大部分证据来自官方/文档/价格页，可能高估产品成熟度或忽略用户痛点。",
                    "impact": "Positive positioning may be over-weighted.",
                    "recommendation": "Add third-party reviews, community discussions and recent news.",
                }
            )
        if source_counter["review"] == 0:
            report.append(
                {
                    "bias_type": "missing_user_voice",
                    "description": "缺少独立用户评价证据，用户满意度相关判断只能低置信度处理。",
                    "impact": "User pain points may be incomplete.",
                    "recommendation": "Collect G2/Capterra/社媒/应用商店/社区评论等来源。",
                }
            )
        return self.pack("success", "Bias detection completed.", [], {"source_mix": dict(source_counter), "bias_report": report})


class RedTeamAgent(DeepSpecializedAgent):
    name = "RedTeamAgent"
    description = "Challenge evidence sufficiency, omitted competitors and overconfident conclusions."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        grouped = self.evidence_by_competitor(evidence)
        challenges = []
        for competitor in competitors:
            ids = grouped.get(competitor.name, [])
            source_types = {item.source_type for item in ids}
            if len(ids) < 3:
                challenges.append(
                    {
                        "challenge": f"{competitor.name} 的证据少于 3 条，报告不能支撑强商业判断。",
                        "severity": "high",
                        "suggested_fix": "补充官方、价格、用户评价和新闻至少三类来源。",
                    }
                )
            if "pricing" not in source_types and "third_party" not in source_types:
                challenges.append(
                    {
                        "challenge": f"{competitor.name} 缺少价格/商业化来源，定价策略分析可能偏弱。",
                        "severity": "medium",
                        "suggested_fix": "补充最新价格页、招商规则、财报或商家成本资料。",
                    }
                )
        return self.pack("success", "Red team review completed.", [], {"red_team_challenges": challenges})


class QualityGateAgent(DeepSpecializedAgent):
    name = "QualityGateAgent"
    description = "Decide whether the report can ship and calculate final delivery warnings."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        claims = list(context.db.scalars(select(Claim).where(Claim.project_id == context.project_id)).all())
        outputs = collect_outputs(input_data)
        warnings = []
        for key in ["fact_check", "citation_check", "consistency_check", "bias_detection", "red_team"]:
            payload = outputs.get(key, {}).get("payload", {})
            warnings.extend(extract_warnings(key, payload))
        relevance = compute_relevance(outputs.get("intent", {}), competitors)
        for missing in relevance["missing_requested"]:
            warnings.append(f"Relevance high: requested competitor not represented in output: {missing}")
        for extra in relevance["off_topic_competitors"]:
            warnings.append(f"Relevance medium: output competitor may be off-scope: {extra}")
        if relevance["requested_count"] and relevance["match_ratio"] < 0.8:
            warnings.append(f"Relevance high: only {relevance['matched_count']}/{relevance['requested_count']} requested competitors matched.")
        if evidence and all(item.source_type in {"unverified", "crawl_failed"} for item in evidence):
            warnings.append("Evidence high: no verified public-source content was collected; report must stay low-confidence.")
        quality_score = compute_quality_score(competitors, evidence, claims, warnings, relevance)
        status = "pass" if quality_score["total"] >= 88 and not warnings else "pass_with_warnings"
        if quality_score["total"] < 70:
            status = "needs_revision"
        return self.pack("success", "Quality gate completed.", [], {"quality_gate": {"status": status, "score": quality_score["total"], "warnings": warnings, "required_fixes": [] if status != "needs_revision" else warnings[:5], "relevance": relevance}, "quality_score": quality_score, "warnings": warnings, "status": status})


def collect_outputs(input_data: dict) -> dict:
    outputs = dict(input_data.get("memory", {}))
    outputs.update(input_data.get("dependency_outputs", {}))
    return outputs


COMPETITOR_DISCOVERY_SCHEMA = {
    "type": "object",
    "properties": {
        "competitors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "competitor_details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "reason": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["name", "reason"],
            },
        },
    },
    "required": ["competitors"],
}


def competitor_discovery_prompt(project: dict, intent: dict, max_count: int) -> str:
    return f"""
Choose suitable competitors for a competitive-intelligence task.

Project:
{project}

Parsed intent:
{intent}

Rules:
- Return exactly {max_count} competitors when the market has enough credible options; otherwise return as many as are genuinely relevant.
- Choose real companies, brands, product lines, or platforms that users would actually compare in this category.
- If the category includes a price segment or geography, respect it.
- Keep names concise and search-friendly. Chinese names are acceptable for Chinese-market products.
- Do not include generic categories, explanations, or invented brands in the competitors array.
"""


def normalize_competitor_names(values: list[Any], limit: int) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for value in values:
        name = str(value).strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
        if len(names) >= limit:
            break
    return names


def normalize_competitor_details(values: list[Any], competitors: list[str]) -> list[dict[str, Any]]:
    competitor_set = {name.casefold() for name in competitors}
    details = []
    for value in values:
        if not isinstance(value, dict):
            continue
        name = str(value.get("name", "")).strip()
        if not name or name.casefold() not in competitor_set:
            continue
        details.append(value)
    return details


def discovery_reason(name: str, llm_details: list[dict[str, Any]], intent: dict) -> str:
    for detail in llm_details:
        if str(detail.get("name", "")).casefold() == name.casefold() and detail.get("reason"):
            return str(detail["reason"])
    return f"Matches the requested scope: {intent.get('industry', 'unknown')}."


def default_competitors(industry: str) -> list[str]:
    lower = industry.lower()
    if "laptop" in lower or "notebook" in lower or "笔记本" in industry or "电脑" in industry:
        return ["联想小新", "华硕无畏", "惠普战66", "戴尔灵越", "荣耀MagicBook", "机械革命无界"]
    if "e-commerce" in industry:
        return ["京东", "阿里巴巴", "拼多多", "唯品会"]
    if "Agent" in industry:
        return ["LangChain", "LlamaIndex", "Dify", "Flowise", "CrewAI", "AutoGen"]
    if "video" in lower:
        return ["Runway", "Pika", "Kling", "Luma", "Synthesia", "HeyGen"]
    if "search" in lower:
        return ["Perplexity", "秘塔 AI 搜索", "Kimi", "ChatGPT Search"]
    if "project management" in lower:
        return ["Linear", "Jira", "Asana", "Monday.com", "ClickUp AI", "Trello"]
    if "crm" in lower:
        return ["Salesforce", "HubSpot", "Zoho CRM", "Pipedrive", "Intercom", "Zendesk"]
    if "knowledge" in lower:
        return ["Notion AI", "Glean", "Guru", "Confluence", "SharePoint", "飞书"]
    return []


def source_query(competitor: str, source_type: str, industry: str) -> str:
    lower = industry.lower()
    if "laptop" in lower or "notebook" in lower or "笔记本" in industry or "电脑" in industry:
        suffix = {
            "official": "官方 参数 配置 价格",
            "pricing": "6000元 价格 京东 天猫 促销",
            "docs": "CPU 显卡 屏幕 续航 重量 接口 参数",
            "review": "评测 优缺点 用户评价 散热 噪音",
            "news": "新品 发布 2026 笔记本",
            "changelog": "型号 更新 迭代 版本",
            "github": "拆机 跑分 benchmark review",
        }[source_type]
        return f"{competitor} {industry} {suffix}"

    suffix = {
        "official": "official product positioning features",
        "pricing": "pricing business model fees",
        "docs": "docs API security integrations merchant rules",
        "review": "user reviews pros cons complaints",
        "news": "recent updates launch partnerships market signals",
        "changelog": "changelog release notes latest product updates",
        "github": "GitHub stars forks issues releases open source activity",
    }[source_type]
    return f"{competitor} {industry} {suffix}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def content_quality(text: str) -> str:
    if len(text) > 450:
        return "rich"
    if len(text) > 120:
        return "usable"
    return "thin"


def confidence_from_evidence(ids: list[str]) -> float:
    if not ids:
        return 0.1
    return min(0.88, 0.5 + 0.1 * len(ids))


def flatten_ids(items: list[Any]) -> list[str]:
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict):
            ids.extend(item.get("evidence_ids", []))
    return sorted(set(ids))


def finding(agent: str, claim_type: str, subject: str, claim: str, evidence_ids: list[str], confidence: float, risk_level: str) -> dict:
    return {
        "claim_id": stable_id("finding", agent, subject, claim),
        "claim_type": claim_type,
        "subject": subject,
        "claim": claim,
        "evidence_ids": evidence_ids,
        "confidence": round(confidence, 2),
        "risk_level": risk_level,
        "created_by_agent": agent,
    }


def semantic_support_score(claim_text: str, quote: str, summary: str) -> float:
    claim_units = text_units(claim_text)
    evidence_units = text_units(f"{quote} {summary}")
    if not claim_units or not evidence_units:
        return 0.0
    overlap = claim_units & evidence_units
    return len(overlap) / max(1, min(len(claim_units), len(evidence_units)))


def text_units(text: str) -> set[str]:
    lowered = text.lower()
    ascii_tokens = {token for token in re.findall(r"[a-z0-9][a-z0-9.+_-]{1,}", lowered) if token not in STOPWORDS}
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    chinese_bigrams = {"".join(chinese[index : index + 2]) for index in range(max(0, len(chinese) - 1))}
    return ascii_tokens | chinese_bigrams


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "unknown",
    "current",
    "evidence",
    "signal",
    "signals",
    "analysis",
    "competitor",
}


def compute_relevance(intent: dict, competitors: list[Competitor]) -> dict:
    requested = [normalize_name(name) for name in intent.get("target_companies", []) if name]
    output = [normalize_name(competitor.name) for competitor in competitors]
    matched = []
    missing = []
    for original, normalized in zip(intent.get("target_companies", []), requested, strict=False):
        if any(names_match(normalized, candidate) for candidate in output):
            matched.append(original)
        else:
            missing.append(original)
    off_topic = []
    if requested:
        for competitor in competitors:
            normalized = normalize_name(competitor.name)
            if not any(names_match(normalized, requested_name) for requested_name in requested):
                off_topic.append(competitor.name)
    requested_count = len(requested)
    return {
        "requested_count": requested_count,
        "matched_count": len(matched),
        "match_ratio": round(len(matched) / max(1, requested_count), 2) if requested_count else 1.0,
        "missing_requested": missing,
        "off_topic_competitors": off_topic,
    }


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", name.lower())


def names_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or left in right or right in left


def positioning_sentence(name: str, profile: dict, features: list[str]) -> str:
    if not features:
        return "当前资料不足，差异化定位为 unknown"
    target = ", ".join(profile.get("target_users", ["unknown"]))
    return f"面向 {target} 聚焦 {', '.join(features[:3])}"


def maturity_from_signal_count(count: int) -> str:
    if count >= 4:
        return "high"
    if count >= 2:
        return "medium-high"
    if count == 1:
        return "medium"
    return "unknown"


def gtm_signals(profile: dict) -> list[str]:
    signals = []
    business_model = profile.get("business_model", [])
    if "freemium" in business_model:
        signals.append("free tier / PLG")
    if "enterprise" in business_model:
        signals.append("enterprise sales")
    if "marketplace" in business_model:
        signals.append("merchant ecosystem")
    if "advertising" in business_model:
        signals.append("traffic monetization")
    if "logistics_service" in business_model:
        signals.append("fulfillment service")
    if profile.get("integrations"):
        signals.append("integration ecosystem")
    return signals or ["unknown"]


def strategy_from_profile(profile: dict) -> str:
    models = set(profile.get("business_model", []))
    if {"marketplace", "advertising"} & models:
        return "platform ecosystem + traffic monetization"
    if "logistics_service" in models:
        return "retail supply chain + fulfillment moat"
    if "freemium" in models:
        return "product-led growth with paid expansion"
    if "enterprise" in models:
        return "enterprise sales with custom packaging"
    return "unknown"


def opportunity_from_profile(profile: dict) -> str:
    category = profile.get("product_category", "unknown")
    if "e-commerce" in category:
        return "围绕细分人群、履约体验、商家工具或信任机制寻找差异化切入。"
    if "AI productivity" in category:
        return "围绕隐私优先、垂直场景模板、深度工作流自动化寻找差异化。"
    return "优先补充证据后再判断机会点。"


def extract_warnings(agent_key: str, payload: dict) -> list[str]:
    warnings = []
    if agent_key == "fact_check":
        for issue in payload.get("fact_check_result", {}).get("issues", []):
            warnings.append(f"FactCheck {issue.get('severity')}: {issue.get('message')}")
    if agent_key == "citation_check":
        for check in payload.get("citation_checks", []):
            if check.get("status") != "supported":
                warnings.append(f"CitationCheck {check.get('status')}: {check.get('claim_id')}")
    if agent_key == "consistency_check":
        for issue in payload.get("consistency_issues", []):
            warnings.append(f"Consistency: {issue.get('message')}")
    if agent_key == "bias_detection":
        for item in payload.get("bias_report", []):
            warnings.append(f"Bias: {item.get('description')}")
    if agent_key == "red_team":
        for item in payload.get("red_team_challenges", []):
            warnings.append(f"RedTeam {item.get('severity')}: {item.get('challenge')}")
    return warnings


def compute_quality_score(competitors: list[Competitor], evidence: list[Evidence], claims: list[Claim], warnings: list[str], relevance: dict | None = None) -> dict:
    competitor_count = max(1, len(competitors))
    source_types = {item.source_type for item in evidence}
    verified_evidence = [item for item in evidence if item.source_type not in {"unverified", "crawl_failed"} and item.credibility_score >= 0.35]
    verified_ids = {item.id for item in verified_evidence}
    coverage_ratio = min(1.0, len(verified_evidence) / (competitor_count * 4))
    source_diversity = min(1.0, len(source_types - {"unverified", "crawl_failed"}) / 5)
    verified_source_ratio = len(verified_evidence) / max(1, len(evidence))
    verified_claim_ratio = sum(
        1 for claim in claims if claim.claim_type == "unknown" or any(evidence_id in verified_ids for evidence_id in claim.evidence_ids)
    ) / max(1, len(claims))
    avg_credibility = sum(item.credibility_score for item in verified_evidence) / max(1, len(verified_evidence))
    warning_penalty = min(14, len(warnings) * 2)
    relevance_ratio = (relevance or {}).get("match_ratio", 1.0)
    relevance_penalty = 0 if relevance_ratio >= 0.8 else round((0.8 - relevance_ratio) * 20)
    score = {
        "coverage": max(0, round((12 * coverage_ratio + 4 * source_diversity + 4 * verified_source_ratio) * relevance_ratio)),
        "evidence_strength": round(14 * verified_claim_ratio + 6 * avg_credibility),
        "citation_accuracy": max(0, 15 - warning_penalty // 2 - relevance_penalty // 2),
        "analysis_depth": max(3, min(15, round((6 + len(claims) / max(1, competitor_count)) * max(0.35, verified_source_ratio)))),
        "structure": 10,
        "consistency": max(5, 10 - warning_penalty // 3),
        "readability": 5,
        "novelty": 4 if verified_source_ratio >= 0.5 else 2,
    }
    score["total"] = sum(score.values())
    return score
