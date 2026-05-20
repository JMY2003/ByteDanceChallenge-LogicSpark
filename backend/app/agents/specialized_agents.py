from __future__ import annotations

import re
import json
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent
from app.config import should_simulate
from app.core.ids import stable_id
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

    async def refine_with_llm(
        self,
        input_data: dict,
        context: AgentContext,
        focus: str,
        summary: str,
        payload: dict,
    ) -> tuple[str, dict]:
        if should_simulate(context.config):
            return summary, payload

        competitors = self.load_competitors(context)
        evidence = self.load_evidence(context)
        valid_evidence_ids = {item.id for item in evidence}
        review = await context.complete_json(
            specialist_review_prompt(
                agent_name=self.name,
                focus=focus,
                project=input_data.get("project", {}),
                upstream=collect_outputs(input_data),
                competitors=competitors,
                evidence=evidence,
                deterministic_payload=payload,
            ),
            SPECIALIST_REVIEW_SCHEMA,
            max_tokens=3000,
        )
        llm_findings = normalize_llm_specialist_findings(self.name, review.get("findings", []), valid_evidence_ids)
        if not llm_findings:
            raise ValueError(f"{self.name} LLM review produced no evidence-bound findings.")
        refined = dict(payload)
        refined["findings"] = merge_findings(payload.get("findings", []), llm_findings)
        refined["llm_specialist_review"] = {
            "used": True,
            "summary": str(review.get("summary") or summary),
            "warnings": [str(item) for item in review.get("warnings", []) if str(item).strip()],
        }
        return refined["llm_specialist_review"]["summary"], refined


class CompetitorDiscoveryAgent(DeepSpecializedAgent):
    name = "CompetitorDiscoveryAgent"
    description = "Discover direct, indirect, substitute and emerging competitors."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        intent = collect_outputs(input_data).get("intent", {})
        project = input_data.get("project", {})
        max_count = int(project.get("max_competitors") or 6)
        explicit_competitors = normalize_competitor_names(intent.get("target_companies") or [], max_count)
        llm_details: list[dict[str, Any]] = []

        if should_simulate(context.config):
            competitors = explicit_competitors
            if not competitors:
                competitors = normalize_competitor_names(default_competitors(intent.get("industry", "unknown")), max_count)
        elif explicit_competitors:
            llm_payload = await context.complete_json(
                explicit_competitor_validation_prompt(project, intent, explicit_competitors),
                COMPETITOR_DISCOVERY_SCHEMA,
                max_tokens=2400,
            )
            llm_details = normalize_competitor_details(llm_payload.get("competitor_details") or [], explicit_competitors)
            competitors = explicit_competitors
        else:
            live_market_context = await collect_live_market_context(context, project, intent, max_count)
            llm_payload = await context.complete_json(
                competitor_discovery_prompt(project, intent, max_count, live_market_context),
                COMPETITOR_DISCOVERY_SCHEMA,
                max_tokens=3000,
            )
            competitors = normalize_competitor_names(llm_payload.get("competitors") or [], max_count)
            llm_details = normalize_competitor_details(llm_payload.get("competitor_details") or [], competitors)
            if should_refine_to_product_level(project, intent, competitors):
                refined_payload = await context.complete_json(
                    product_level_refinement_prompt(project, intent, competitors, max_count, live_market_context),
                    COMPETITOR_DISCOVERY_SCHEMA,
                    max_tokens=3000,
                )
                refined_competitors = normalize_competitor_names(refined_payload.get("competitors") or [], max_count)
                if refined_competitors:
                    competitors = refined_competitors
                    llm_details = normalize_competitor_details(refined_payload.get("competitor_details") or [], competitors)
            if should_refine_for_currentness(project, intent, competitors):
                current_payload = await context.complete_json(
                    currentness_refinement_prompt(project, intent, competitors, max_count, live_market_context),
                    COMPETITOR_DISCOVERY_SCHEMA,
                    max_tokens=3000,
                )
                current_competitors = normalize_competitor_names(current_payload.get("competitors") or [], max_count)
                if current_competitors:
                    competitors = current_competitors
                    llm_details = normalize_competitor_details(current_payload.get("competitor_details") or [], competitors)
                if has_unreleased_or_unverified_currentness_signal(llm_details):
                    verified_payload = await context.complete_json(
                        verified_currentness_repair_prompt(project, intent, competitors, llm_details, max_count, live_market_context),
                        COMPETITOR_DISCOVERY_SCHEMA,
                        max_tokens=3000,
                    )
                    verified_competitors = normalize_competitor_names(verified_payload.get("competitors") or [], max_count)
                    if verified_competitors:
                        competitors = verified_competitors
                        llm_details = normalize_competitor_details(verified_payload.get("competitor_details") or [], competitors)
                if should_include_context_benchmark(project, intent, live_market_context, competitors):
                    benchmark_payload = await context.complete_json(
                        context_benchmark_repair_prompt(project, intent, competitors, llm_details, max_count, live_market_context),
                        COMPETITOR_DISCOVERY_SCHEMA,
                        max_tokens=3000,
                    )
                    benchmark_competitors = normalize_competitor_names(benchmark_payload.get("competitors") or [], max_count)
                    if benchmark_competitors:
                        competitors = benchmark_competitors
                        llm_details = normalize_competitor_details(benchmark_payload.get("competitor_details") or [], competitors)
            validate_discovered_competitors(project, intent, competitors, max_count)
            validate_currentness_details(project, intent, llm_details)

        if not competitors and should_simulate(context.config):
            competitors = normalize_competitor_names(default_competitors(intent.get("industry", "unknown")), max_count)
        if not competitors:
            raise ValueError("CompetitorDiscoveryAgent returned no competitors and deterministic fallback is disabled.")
        validate_competitor_names(competitors)

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
        if not competitors:
            raise ValueError("SourcePlanningAgent requires competitors from CompetitorDiscoveryAgent.")
        if not should_simulate(context.config):
            llm_payload = await context.complete_json(
                source_planning_prompt(input_data.get("project", {}), intent, competitors),
                SOURCE_PLANNING_SCHEMA,
                max_tokens=3400,
            )
            plan = normalize_source_plan(llm_payload.get("source_plan", []), competitors)
            validate_source_plan(plan, competitors)
            return self.pack(
                "success",
                f"Planned {len(plan)} public-source searches with LLM domain-aware queries.",
                [],
                {"source_plan": plan, "llm_used": True},
            )

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
        return self.pack("success", f"Planned {len(plan)} simulated public-source searches.", [], {"source_plan": plan, "llm_used": False})


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
        payload = {"positioning_analysis": analysis, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "positioning, target users, use cases, value proposition and category-specific differentiation",
            "Positioning analysis completed.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
        payload = {"feature_matrix": matrix, "scores": scores, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "category-specific feature and capability comparison, maturity differences, missing evidence and selection criteria",
            f"Feature matrix built with {len(all_features)} comparable dimensions.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
                "claim": "价格、套餐、渠道促销或商业化规则变化快，最终建议应在交付前刷新验证。",
                "confidence": 0.7,
                "evidence_ids": [item.id for item in evidence[:5]],
            }
        ]
        payload = {"pricing_table": table, "insights": insights, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "pricing, packaging, channel price, monetization model, price-value risk and evidence freshness",
            "Pricing analysis completed with live-verification flags.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
        payload = {"user_voice_summary": summaries, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "user reviews, community feedback, pros and cons, adoption blockers, satisfaction and evidence gaps",
            "User voice analysis completed with evidence-gap flags.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
        payload = {"technology_analysis": analysis, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "technology, product architecture, integration, ecosystem, security, performance or other category-relevant capability signals",
            "Technology intelligence analysis completed.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
        payload = {"gtm_analysis": analysis, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "go-to-market strategy, channels, partnerships, target segments, sales motion and category-specific market access",
            "GTM analysis completed.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
        payload = {"swot": swot, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "evidence-bound strengths, weaknesses, opportunities and threats across all competitors",
            "SWOT analysis completed and written back to competitor profiles.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)), payload)


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
        payload = {"strategic_insights": insights, "findings": findings}
        summary, payload = await self.refine_with_llm(
            input_data,
            context,
            "strategic opportunities, risks, differentiators, product recommendations and next research priorities",
            "Strategic insight generation completed.",
            payload,
        )
        return self.pack("success", summary, flatten_ids(payload.get("findings", findings)) or all_ids, payload)


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
            pricing = competitor.profile.get("pricing", [])
            has_price_signal = any(
                item.get("price") and item.get("price") not in {"unknown", "needs live price verification"}
                for item in pricing
                if isinstance(item, dict)
            )
            if not has_price_signal and "pricing" not in source_types and "third_party" not in source_types:
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
        for repair in outputs.get("evidence_builder", {}).get("coverage_repairs", []):
            if isinstance(repair, dict):
                warnings.append(
                    f"Evidence medium: {repair.get('competitor', 'unknown')} needed coverage repair from a real source chunk; verify this evidence manually."
                )
        analysis = outputs.get("analysis", {})
        for gap in analysis.get("evidence_gaps", []):
            severity = gap.get("severity", "medium")
            if severity in {"high", "medium"}:
                warnings.append(f"Evidence {severity}: {gap.get('competitor', 'unknown')} - {gap.get('gap', 'unknown')}")
        if not analysis.get("feature_matrix"):
            warnings.append("Analysis high: feature/capability matrix is empty.")
        if not analysis.get("competitor_cards"):
            warnings.append("Analysis high: competitor summary cards are empty.")

        grouped = self.evidence_by_competitor(evidence)
        for competitor in competitors:
            items = grouped.get(competitor.name, [])
            usable = [
                item
                for item in items
                if item.source_type != "crawl_failed" and item.credibility_score >= 0.35 and "Crawl failed for" not in item.quote
            ]
            if len(usable) < 2:
                warnings.append(f"Evidence high: {competitor.name} has fewer than 2 usable evidence items.")
            if items and {item.source_type for item in items} <= {"search_snippet", "unverified", "crawl_failed"}:
                warnings.append(f"Evidence high: {competitor.name} relies only on weak search snippets or unverified fallbacks.")
        relevance = compute_relevance(outputs.get("intent", {}), competitors)
        for missing in relevance["missing_requested"]:
            warnings.append(f"Relevance high: requested competitor not represented in output: {missing}")
        for extra in relevance["off_topic_competitors"]:
            warnings.append(f"Relevance medium: output competitor may be off-scope: {extra}")
        if relevance["requested_count"] and relevance["match_ratio"] < 0.8:
            warnings.append(f"Relevance high: only {relevance['matched_count']}/{relevance['requested_count']} requested competitors matched.")
        if evidence and all(item.source_type in {"unverified", "crawl_failed"} for item in evidence):
            warnings.append("Evidence high: no verified public-source content was collected; report must stay low-confidence.")
        runtime_fallback_warnings: list[str] = []
        if not should_simulate(context.config):
            runtime_fallback_warnings = collect_runtime_fallback_warnings(outputs, competitors)
            for warning in runtime_fallback_warnings:
                if warning not in warnings:
                    warnings.append(warning)
        ai_review = {"used": False, "error": None}
        if not should_simulate(context.config):
            review = await context.complete_json(
                quality_review_prompt(input_data.get("project", {}), outputs.get("intent", {}), competitors, analysis, warnings),
                QUALITY_REVIEW_SCHEMA,
                max_tokens=2400,
            )
            ai_review = review | {"used": True, "error": None}
            for warning in review.get("warnings", []):
                if warning not in warnings:
                    warnings.append(warning)
            if review.get("domain_mismatch"):
                warnings.append("Domain high: profile dimensions do not match the user's requested category.")
        quality_score = compute_quality_score(competitors, evidence, claims, warnings, relevance)
        status = "pass" if quality_score["total"] >= 88 and not warnings else "pass_with_warnings"
        if quality_score["total"] < 70:
            status = "needs_revision"
        if any(str(warning).startswith(("Evidence high", "Relevance high", "Domain high")) for warning in warnings):
            status = "needs_revision"
        if ai_review.get("suggested_status") == "needs_revision":
            status = "needs_revision"
        if runtime_fallback_warnings:
            status = "needs_revision"
        required_fixes = ai_review.get("required_fixes", []) if isinstance(ai_review.get("required_fixes"), list) else []
        if status == "needs_revision" and not required_fixes:
            required_fixes = warnings[:5]
        if runtime_fallback_warnings:
            fallback_fix = "重新运行失败的 LLM 环节；fallback 结果只能用于调试，不能作为正式竞品分析报告。"
            if fallback_fix not in required_fixes:
                required_fixes.insert(0, fallback_fix)
        if not should_simulate(context.config):
            critical_failures = critical_quality_failures(input_data.get("project", {}), competitors, evidence, claims, quality_score, warnings, ai_review)
            if critical_failures:
                raise ValueError("QualityGateAgent blocked report generation: " + " | ".join(critical_failures[:8]))
        return self.pack(
            "success",
            "Quality gate completed.",
            [],
            {
                "quality_gate": {
                    "status": status,
                    "score": quality_score["total"],
                    "warnings": warnings,
                    "required_fixes": required_fixes,
                    "relevance": relevance,
                    "ai_review": ai_review,
                    "runtime_fallback_warnings": runtime_fallback_warnings,
                },
                "quality_score": quality_score,
                "warnings": warnings,
                "status": status,
                "runtime_fallback_warnings": runtime_fallback_warnings,
            },
        )


def collect_outputs(input_data: dict) -> dict:
    outputs = dict(input_data.get("memory", {}))
    outputs.update(input_data.get("dependency_outputs", {}))
    return outputs


SPECIALIST_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_type": {"type": "string"},
                    "subject": {"type": "string"},
                    "claim": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "risk_level": {"type": "string"},
                },
                "required": ["claim_type", "subject", "claim", "evidence_ids", "confidence", "risk_level"],
                "additionalProperties": False,
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "findings", "warnings"],
    "additionalProperties": False,
}


def specialist_review_prompt(
    agent_name: str,
    focus: str,
    project: dict,
    upstream: dict,
    competitors: list[Competitor],
    evidence: list[Evidence],
    deterministic_payload: dict,
) -> str:
    profiles = [
        {
            "name": competitor.name,
            "product_category": competitor.profile.get("product_category"),
            "target_users": competitor.profile.get("target_users", [])[:6],
            "business_model": competitor.profile.get("business_model", [])[:6],
            "positioning": competitor.profile.get("positioning", {}),
            "features": competitor.profile.get("features", [])[:8],
            "pricing": competitor.profile.get("pricing", [])[:4],
            "source_coverage": competitor.profile.get("source_coverage", []),
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
            "quote": item.quote[:360],
            "summary": item.summary[:260],
            "credibility_score": item.credibility_score,
        }
        for item in evidence[:36]
    ]
    upstream_summary = {
        "intent": upstream.get("intent", {}),
        "planner": upstream.get("planner", {}).get("research_plan", {}),
        "competitor_discovery": upstream.get("competitor_discovery", {}).get("payload", {}),
    }
    return f"""
You are {agent_name}, one specialist in a general-purpose competitive-intelligence multi-agent system.

Specialist focus:
{focus}

Project:
{json.dumps(project, ensure_ascii=False)}

Upstream context:
{json.dumps(upstream_summary, ensure_ascii=False)}

Competitor profiles:
{json.dumps(profiles, ensure_ascii=False)}

Evidence, with the only evidence IDs you may cite:
{json.dumps(evidence_payload, ensure_ascii=False)}

Deterministic draft from local structured extraction:
{json.dumps(deterministic_payload, ensure_ascii=False, default=str)[:7000]}

Rules:
- Return 4 to 8 concise findings that are useful for a product manager or market researcher.
- Adapt dimensions to the user's category; do not reuse software/SaaS dimensions for hardware, retail, consumer goods, finance, education, or other categories unless the task actually asks for them.
- Use only the provided competitors and evidence IDs.
- Do not invent facts, exact prices, benchmarks, market share, dates, or user sentiment.
- If evidence is weak or missing, write an "unknown" finding with low confidence and say what should be verified next.
- claim_type must be one of: fact, inference, recommendation, opportunity, unknown.
- risk_level must be one of: low, medium, high.
- Return JSON only.
"""


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


SOURCE_PLANNING_SCHEMA = {
    "type": "object",
    "properties": {
        "source_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "competitor": {"type": "string"},
                    "source_type": {"type": "string"},
                    "query": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["competitor", "source_type", "query"],
                "additionalProperties": True,
            },
        }
    },
    "required": ["source_plan"],
    "additionalProperties": False,
}


def analysis_current_date() -> str:
    return date.today().isoformat()


def analysis_years() -> tuple[int, int]:
    current_year = date.today().year
    return current_year, current_year - 1


def source_planning_prompt(project: dict, intent: dict, competitors: list[str]) -> str:
    current_year, previous_year = analysis_years()
    return f"""
Plan web searches for a competitive intelligence task.

Current date:
{analysis_current_date()}

Project:
{project}

Parsed intent:
{intent}

Competitors:
{competitors}

Rules:
- Return 4 to 6 searches per competitor.
- Queries must be domain-specific and search-friendly.
- Include official product/spec pages, current price/channel pages, third-party reviews/comparisons, user feedback, and recent news/update sources when appropriate.
- For fast-moving product categories, every query should prefer currently sold products and fresh sources. Include terms such as latest/current/在售/现售/{current_year}/{previous_year}/到手价/现价 when relevant.
- For price-band tasks, search current street/channel price, not launch price.
- source_type must be one of: official, pricing, docs, review, news, changelog, github, mixed.
- For phones, use terms like 最新 在售 {current_year} {previous_year} 官方 参数 现价 到手价 影像 续航 评测 用户评价 系统生态.
- For laptops, use terms like 最新 在售 {current_year} {previous_year} 官方 参数 配置 现价 屏幕 续航 散热 评测.
- For software/SaaS, use official product, pricing, docs, reviews, changelog, security/integration queries.
- Do not use irrelevant software words for hardware categories.
"""


def normalize_source_plan(values: list[Any], competitors: list[str]) -> list[dict[str, Any]]:
    competitor_names = {name.casefold(): name for name in competitors}
    plan: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        competitor = competitor_names.get(str(value.get("competitor", "")).casefold())
        query = normalize_text(str(value.get("query", "")))
        if not competitor or not query:
            continue
        key = (competitor.casefold(), query.casefold())
        if key in seen:
            continue
        seen.add(key)
        plan.append(
            {
                "competitor": competitor,
                "source_type": normalize_source_type(str(value.get("source_type", "mixed"))),
                "query": query[:240],
                "priority": str(value.get("priority", "medium")) if value.get("priority") else "medium",
            }
        )
    return plan[: max(1, len(competitors)) * 6]


def normalize_source_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "spec": "docs",
        "specs": "docs",
        "specification": "docs",
        "specifications": "docs",
        "official_spec": "official",
        "official_specs": "official",
        "official_page": "official",
        "official_product": "official",
        "official_spec_pricing": "official",
        "official_specs_pricing": "official",
        "official_price": "pricing",
        "product_page": "official",
        "official": "official",
        "price": "pricing",
        "pricing": "pricing",
        "pricing_channel": "pricing",
        "channel_pricing": "pricing",
        "current_pricing_channel": "pricing",
        "latest_pricing_channel": "pricing",
        "commerce": "pricing",
        "ecommerce": "pricing",
        "review": "review",
        "reviews": "review",
        "comparison": "review",
        "third_party_review": "review",
        "third_party_reviews": "review",
        "user_review": "review",
        "user_reviews": "review",
        "news": "news",
        "market_news": "news",
        "media_news": "news",
        "update": "changelog",
        "updates": "changelog",
        "changelog": "changelog",
        "forum": "review",
        "user_feedback": "review",
        "social": "review",
        "community": "review",
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
    return normalized or "mixed"


async def collect_live_market_context(context: AgentContext, project: dict, intent: dict, max_count: int) -> list[dict[str, Any]]:
    if should_simulate(context.config) or is_historical_task(project, intent):
        return []
    merged_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for query in market_discovery_queries(project, intent)[:4]:
        result = await context.call_tool(
            "web_search",
            {
                "query": query,
                "competitor": "market_discovery",
                "source_type": "mixed",
                "max_results": max(6, min(10, max_count + 3)),
            },
        )
        for item in result.get("search_results", []):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            key = url or f"{item.get('title', '')}|{item.get('snippet', '')}"
            if key in seen_urls:
                continue
            seen_urls.add(key)
            merged_results.append(item)
    return compact_market_context(merged_results, extract_price_segment_hint(str(project.get("query") or "")))


def market_discovery_query(project: dict, intent: dict) -> str:
    return market_discovery_queries(project, intent)[0]


def market_discovery_queries(project: dict, intent: dict) -> list[str]:
    current_year, previous_year = analysis_years()
    current_month = date.today().month
    query = normalize_text(str(project.get("query") or ""))
    industry = normalize_text(str(intent.get("industry") or ""))
    category_hint = search_category_hint(project, intent)
    price_hint = extract_price_segment_hint(query)

    if is_recency_sensitive_product_task(project, intent):
        product_terms = recency_sensitive_search_terms(project, intent)
        queries = [
            f"{current_year}年{current_month}月 {price_hint} {category_hint} 推荐 最新在售 {product_terms} 到手价",
            f"{current_year}年 {price_hint} {category_hint} 选购攻略 新款 在售 旗舰 对比",
            f"{current_year} {previous_year} {category_hint} 最新发布 在售 价格 竞品 对比",
            f"{category_hint} {price_hint} 当前主流竞品 最新榜单 {current_year} {current_month}月",
        ]
    else:
        queries = [
            f"{category_hint} current latest {current_year} {previous_year} competitors alternatives market comparison",
            f"{query} current market competitors {current_year}",
        ]
    normalized: list[str] = []
    seen: set[str] = set()
    for value in queries:
        text = normalize_text(value)[:280]
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            normalized.append(text)
    return normalized or [normalize_text(f"{query} {industry} current competitors {current_year}")[:280]]


def search_category_hint(project: dict, intent: dict) -> str:
    text = f"{project.get('query', '')} {intent.get('industry', '')}"
    lower = text.casefold()
    if "smartphone" in lower or "phone" in lower or "手机" in text:
        return "手机"
    if "laptop" in lower or "notebook" in lower or "笔记本" in text or "电脑" in text:
        return "笔记本电脑"
    if "car" in lower or "ev" in lower or "汽车" in text or "新能源车" in text or "电动车" in text:
        return "新能源汽车"
    if "电视" in text or "tv" in lower:
        return "电视"
    if "耳机" in text or "headphone" in lower or "earbud" in lower:
        return "耳机"
    if "相机" in text or "camera" in lower:
        return "相机"
    if "平板" in text or "tablet" in lower:
        return "平板电脑"
    return normalize_text(str(intent.get("industry") or project.get("query") or "市场"))[:80]


def recency_sensitive_search_terms(project: dict, intent: dict) -> str:
    text = f"{project.get('query', '')} {intent.get('industry', '')}"
    lower = text.casefold()
    if "smartphone" in lower or "phone" in lower or "手机" in text:
        return "旗舰 Pro Ultra Max 影像 续航 性能"
    if "laptop" in lower or "notebook" in lower or "笔记本" in text or "电脑" in text:
        return "轻薄本 全能本 酷睿 锐龙 AI PC 屏幕 续航"
    if "car" in lower or "ev" in lower or "汽车" in text or "新能源车" in text or "电动车" in text:
        return "上市 续航 智驾 配置 价格 交付"
    return "新品 在售 旗舰 Pro Max Ultra 价格 评测"


def extract_price_segment_hint(text: str) -> str:
    normalized = normalize_text(text)
    range_match = re.search(r"([1-9]\d{3,4})\s*(?:-|~|—|–|到|至)\s*([1-9]\d{3,4})\s*(?:元|rmb|cny)?", normalized, flags=re.I)
    if range_match:
        low, high = sorted((int(range_match.group(1)), int(range_match.group(2))))
        return f"{low}-{high}元"
    band_match = re.search(r"([1-9]\d{3,4})\s*(?:元\s*)?(价位档|价位|档|预算|左右|上下|附近|元)", normalized)
    if band_match:
        center = int(band_match.group(1))
        if 1000 <= center <= 300000:
            step = 1000 if center < 20000 else 50000
            suffix = band_match.group(2)
            if suffix in {"价位档", "价位", "档"}:
                low = max(0, center - step)
                high = center
            else:
                low = max(0, center - step)
                high = center + step
            return f"{low}-{high}元 {center}元价位"
    return "主流价位"


def compact_market_context(results: list[Any], price_hint: str = "") -> list[dict[str, Any]]:
    context_items: list[dict[str, Any]] = []
    ranked_results = sorted(
        [item for item in results if isinstance(item, dict)],
        key=lambda item: market_context_score(item, price_hint),
        reverse=True,
    )
    for item in ranked_results[:14]:
        if not isinstance(item, dict):
            continue
        title = normalize_text(str(item.get("title") or ""))
        snippet = normalize_text(str(item.get("snippet") or ""))
        url = normalize_text(str(item.get("url") or ""))
        if not title and not snippet:
            continue
        context_items.append(
            {
                "title": title[:160],
                "snippet": snippet[:300],
                "url": url[:240],
                "source_type": normalize_source_type(str(item.get("source_type") or "mixed")),
                "query": normalize_text(str(item.get("query") or ""))[:180],
                "retrieved_at": item.get("retrieved_at"),
            }
        )
    return context_items


def market_context_score(item: dict[str, Any], price_hint: str = "") -> int:
    current_year, previous_year = analysis_years()
    text = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('url', '')}".casefold()
    score = 0
    for marker, weight in [
        (str(current_year), 8),
        (f"{current_year}年", 8),
        (str(previous_year), 4),
        ("最新", 5),
        ("在售", 5),
        ("现售", 5),
        ("到手价", 4),
        ("推荐", 3),
        ("选购", 3),
        ("6000", 3),
        ("5000", 2),
        ("pro max", 3),
        ("ultra", 3),
        ("旗舰", 3),
    ]:
        if marker in text:
            score += weight
    if re.search(r"(?:iphone|xiaomi|oppo|vivo|honor|huawei|samsung|oneplus|redmi|realme|小米|荣耀|华为|苹果|一加|真我|努比亚|红魔).{0,24}\d", text, re.I):
        score += 8
    if price_hint:
        range_match = re.search(r"(\d{3,6})-(\d{3,6})元", price_hint)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            exact_patterns = [
                f"{low}-{high}",
                f"{low}到{high}",
                f"{low}至{high}",
                f"{low} 至 {high}",
                f"{low} 到 {high}",
            ]
            if any(pattern in text for pattern in exact_patterns):
                score += 18
            for seen_low, seen_high in re.findall(r"([1-9]\d{3,4})\s*(?:-|~|—|–|到|至)\s*([1-9]\d{3,4})", text):
                source_low, source_high = sorted((int(seen_low), int(seen_high)))
                if source_low == low and source_high == high:
                    score += 10
                elif source_low >= high or source_high <= low:
                    score -= 8
    if re.search(r"(?:2020|2021|2022|2023)", text):
        score -= 6
    return score


def competitor_discovery_prompt(project: dict, intent: dict, max_count: int, market_context: list[dict[str, Any]] | None = None) -> str:
    current_year, previous_year = analysis_years()
    return f"""
Choose suitable competitors for a competitive-intelligence task.

Current date:
{analysis_current_date()}

Project:
{project}

Parsed intent:
{intent}

Live market/search context collected before selection:
{json.dumps(market_context or [], ensure_ascii=False)}

Rules:
- Return exactly {max_count} competitors when the market has enough credible options; otherwise return as many as are genuinely relevant.
- Choose real companies, brands, product lines, or platforms that users would actually compare in this category.
- If the category includes a price segment or geography, respect it.
- For hardware, consumer electronics, cars, appliances, phones, laptops, or other concrete products, prefer product-line or SKU-level competitors instead of umbrella brand names.
- For fast-moving product categories, choose models that are currently sold or commonly cross-shopped as of the current date. Prefer {current_year}/{previous_year} generation products unless the user explicitly asks for historical analysis.
- Do not select stale models when newer successor generations exist in the same brand/segment. Treat old launch-era flagships as invalid for current price-band analysis unless current market context proves they are still a mainstream cross-shop option.
- Do not select rumored, expected, upcoming, not-yet-launched, or merely "imminent" products. Every product competitor must be released and publicly purchasable or clearly sold in-market.
- If the user asks a price band, choose competitors that actually sit near that price band or are commonly cross-shopped after channel discounts. Avoid products clearly outside the band unless the reason explicitly explains why they are still a reference point.
- Use live market/search context above as a freshness signal; if it conflicts with model memory, trust the live context.
- For fast-moving product categories, strongly prefer product names explicitly appearing in the live context titles/snippets. If the context mentions newer-generation models than your initial memory, select the newer context-supported models.
- Prefer exact price-band current-month/current-year sources over adjacent higher/lower price-band sources.
- When the exact price-band context names a cross-ecosystem benchmark or platform leader that users commonly compare against, keep it in the set instead of selecting only one regional/vendor cluster.
- In competitor_details.reason, briefly mention currentness, price-band fit, and any uncertainty that needs live verification.
- Keep names concise and search-friendly. Chinese names are acceptable for Chinese-market products.
- Do not include generic categories, explanations, or invented brands in the competitors array.
"""


def explicit_competitor_validation_prompt(project: dict, intent: dict, competitors: list[str]) -> str:
    return f"""
Validate and enrich explicitly requested competitors for a competitive-intelligence task.

Project:
{project}

Parsed intent:
{intent}

Explicit competitors:
{competitors}

Rules:
- Keep the same competitor names; do not add or remove names.
- Return competitor_details with a concise reason explaining why each explicit competitor fits or what needs verification.
- If a name is too broad for a product-level hardware task, mention the product-level ambiguity in reason but do not replace the explicit user choice.
- Return JSON only.
"""


def product_level_refinement_prompt(
    project: dict,
    intent: dict,
    competitors: list[str],
    max_count: int,
    market_context: list[dict[str, Any]] | None = None,
) -> str:
    current_year, previous_year = analysis_years()
    return f"""
The previous competitor discovery returned overly broad brand/company names for a product-level competitive analysis.

Current date:
{analysis_current_date()}

Project:
{project}

Parsed intent:
{intent}

Previous competitors:
{competitors}

Live market/search context:
{json.dumps(market_context or [], ensure_ascii=False)}

Refine the competitors to product-line or SKU-level names that users would directly compare.

Rules:
- Return exactly {max_count} product-level competitors when possible.
- Keep the user's category, price band, geography and audience constraints.
- Prefer concrete product families/models, not umbrella brands.
- Prefer {current_year}/{previous_year} generation products for fast-moving product categories, and use live search context as the currentness anchor.
- Replace obsolete models with the current comparable generation in the same brand/segment when a successor exists.
- Do not replace an old model with an unreleased, rumored, expected, or merely upcoming successor.
- If a brand has multiple relevant models, choose the model line most commonly cross-shopped in the requested price band.
- Do not invent products. If exact current pricing is uncertain, choose models plausibly near the band and explain uncertainty in competitor_details.reason.
"""


def currentness_refinement_prompt(
    project: dict,
    intent: dict,
    competitors: list[str],
    max_count: int,
    market_context: list[dict[str, Any]] | None = None,
) -> str:
    current_year, previous_year = analysis_years()
    return f"""
The previous competitor list may contain stale or outdated product models.

Current date:
{analysis_current_date()}

Project:
{project}

Parsed intent:
{intent}

Previous competitors:
{competitors}

Live market/search context:
{json.dumps(market_context or [], ensure_ascii=False)}

Task:
Return a current, directly comparable competitor list for the user's category and price segment.

Rules:
- Return exactly {max_count} competitors when credible current options exist.
- Keep direct comparability more important than brand coverage.
- For fast-moving product categories, keep only products currently sold or commonly cross-shopped as of the current date.
- Prefer {current_year}/{previous_year} generation products unless the user explicitly asks for older or historical products.
- Replace stale models with newer successor generations in the same brand/segment when appropriate.
- Never include rumored, expected, upcoming, not-yet-launched, or merely "imminent" products. If the newest successor is not verifiably released and purchasable, choose the newest released model instead.
- For price-band tasks, reason from current channel/street price, not launch price.
- Use live market/search context as the freshness anchor; if uncertain, say what must be verified in competitor_details.reason.
- Strongly prefer product names explicitly present in live context titles/snippets, especially current-month buying guides, price pages, and product databases.
- Prefer exact price-band context over adjacent price-band context, and preserve one context-supported cross-ecosystem benchmark when it is directly comparable.
- Do not include umbrella brand names, generic categories, invented products, or products clearly outside the user scope.
"""


def verified_currentness_repair_prompt(
    project: dict,
    intent: dict,
    competitors: list[str],
    competitor_details: list[dict[str, Any]],
    max_count: int,
    market_context: list[dict[str, Any]] | None = None,
) -> str:
    current_year, previous_year = analysis_years()
    return f"""
The previous competitor list contained language suggesting some products may be expected, upcoming, rumored, imminent, or not fully verified as purchasable.

Current date:
{analysis_current_date()}

Project:
{project}

Parsed intent:
{intent}

Previous competitors:
{competitors}

Previous details:
{json.dumps(competitor_details, ensure_ascii=False)}

Live market/search context:
{json.dumps(market_context or [], ensure_ascii=False)}

Repair task:
Return a list of released, publicly purchasable, currently relevant competitors only.

Rules:
- Return exactly {max_count} competitors when credible current options exist.
- Every competitor must be already released and available for purchase or commonly sold in-market.
- Do not include products described as expected, upcoming, rumored, imminent, newly rumored, not-yet-launched, or only forecasted.
- Prefer {current_year}/{previous_year} generation products for fast-moving categories, but verified availability is more important than maximal recency.
- Replace any unverified successor with the newest verified released model in the same price/segment, or with another direct competitor if that brand has no verified current fit.
- In competitor_details.reason, state the current-market fit without using expected/upcoming/imminent language.
- Return JSON only.
"""


def context_benchmark_repair_prompt(
    project: dict,
    intent: dict,
    competitors: list[str],
    competitor_details: list[dict[str, Any]],
    max_count: int,
    market_context: list[dict[str, Any]] | None = None,
) -> str:
    return f"""
The previous competitor list omitted a benchmark product that appears in exact price-band live context.

Project:
{project}

Parsed intent:
{intent}

Previous competitors:
{competitors}

Previous details:
{json.dumps(competitor_details, ensure_ascii=False)}

Live market/search context:
{json.dumps(market_context or [], ensure_ascii=False)}

Repair task:
Return a balanced competitor set for the same category and price segment.

Rules:
- Return exactly {max_count} competitors when credible options exist.
- Keep only released and publicly purchasable products supported by the live context.
- For smartphone tasks, if an iPhone model appears in exact price-band live context and the user did not ask for Android-only analysis, include that iPhone model as the iOS ecosystem benchmark.
- Replace the weakest or least differentiated same-cluster product if needed to keep the requested count.
- Preserve the strongest exact-price-band current-generation products already selected.
- Do not include products from adjacent higher/lower price-band sources unless exact-band context supports them too.
- Return JSON only.
"""


def should_refine_to_product_level(project: dict, intent: dict, competitors: list[str]) -> bool:
    task_text = f"{project.get('query', '')} {intent.get('industry', '')}".casefold()
    if not any(term in task_text for term in RECENCY_SENSITIVE_PRODUCT_TERMS):
        return False
    if not competitors:
        return False
    generic_brands = {
        "apple",
        "苹果",
        "huawei",
        "华为",
        "xiaomi",
        "小米",
        "oppo",
        "vivo",
        "honor",
        "荣耀",
        "samsung",
        "三星",
        "lenovo",
        "联想",
        "asus",
        "华硕",
        "hp",
        "惠普",
        "dell",
        "戴尔",
        "acer",
        "宏碁",
        "sony",
        "索尼",
        "canon",
        "佳能",
        "nikon",
        "尼康",
        "byd",
        "比亚迪",
        "tesla",
        "特斯拉",
    }
    model_signal = re.compile(r"\d|pro|max|air|plus|ultra|mate|galaxy|thinkpad|thinkbook|macbook|ideapad|magic|find|reno|x\d|s\d", re.I)
    broad_count = 0
    for name in competitors:
        normalized = re.sub(r"\s+", " ", name.strip().casefold())
        if normalized in generic_brands:
            broad_count += 1
            continue
        compact = re.sub(r"[\s\-_]+", "", normalized)
        if compact in {re.sub(r"[\s\-_]+", "", item) for item in generic_brands}:
            broad_count += 1
            continue
        if len(normalized.split()) <= 1 and not model_signal.search(normalized):
            broad_count += 1
    return broad_count >= max(1, len(competitors) // 2)


RECENCY_SENSITIVE_PRODUCT_TERMS = [
    "手机",
    "智能手机",
    "android",
    "iphone",
    "phone",
    "smartphone",
    "笔记本",
    "轻薄本",
    "游戏本",
    "laptop",
    "notebook",
    "电脑",
    "consumer electronics",
    "hardware",
    "汽车",
    "新能源车",
    "电动车",
    "car",
    "ev",
    "家电",
    "电视",
    "耳机",
    "相机",
    "camera",
    "tablet",
    "平板",
    "watch",
    "手表",
    "显卡",
    "gpu",
]


HISTORICAL_TASK_TERMS = [
    "历史",
    "复盘",
    "过去",
    "老款",
    "旧款",
    "经典",
    "历代",
    "中古",
    "二手",
    "停产",
    "发布史",
    "retrospective",
    "historical",
    "legacy",
    "used",
]


def should_refine_for_currentness(project: dict, intent: dict, competitors: list[str]) -> bool:
    if not competitors:
        return False
    return is_recency_sensitive_product_task(project, intent) and not is_historical_task(project, intent)


def is_recency_sensitive_product_task(project: dict, intent: dict) -> bool:
    task_text = f"{project.get('query', '')} {intent.get('industry', '')}".casefold()
    return any(term.casefold() in task_text for term in RECENCY_SENSITIVE_PRODUCT_TERMS)


def is_historical_task(project: dict, intent: dict) -> bool:
    task_text = f"{project.get('query', '')} {intent.get('industry', '')}".casefold()
    if any(term.casefold() in task_text for term in HISTORICAL_TASK_TERMS):
        return True
    current_year = date.today().year
    years = [int(match.group(0)) for match in re.finditer(r"\b20\d{2}\b", task_text)]
    return any(year <= current_year - 2 for year in years)


def stale_year_mentions(values: list[str]) -> list[str]:
    current_year = date.today().year
    stale = []
    for value in values:
        years = [int(match.group(0)) for match in re.finditer(r"\b20\d{2}\b", value)]
        if any(year <= current_year - 2 for year in years):
            stale.append(value)
    return stale


UNRELEASED_OR_UNVERIFIED_MARKERS = [
    "expected",
    "upcoming",
    "imminent",
    "rumor",
    "rumour",
    "rumored",
    "rumoured",
    "not-yet-launched",
    "not yet launched",
    "forecast",
    "预计",
    "预期",
    "即将",
    "传闻",
    "爆料",
    "尚未发布",
    "未发布",
    "待发布",
    "可能发布",
    "预计发布",
]


def has_unreleased_or_unverified_currentness_signal(details: list[dict[str, Any]]) -> bool:
    text = json.dumps(details, ensure_ascii=False).casefold()
    return any(marker.casefold() in text for marker in UNRELEASED_OR_UNVERIFIED_MARKERS)


def validate_currentness_details(project: dict, intent: dict, details: list[dict[str, Any]]) -> None:
    if not details or not is_recency_sensitive_product_task(project, intent) or is_historical_task(project, intent):
        return
    if has_unreleased_or_unverified_currentness_signal(details):
        raise ValueError(
            "CompetitorDiscoveryAgent returned unverified upcoming/rumored product currentness language; "
            "rerun after live search confirms released and purchasable competitors."
        )


def should_include_context_benchmark(
    project: dict,
    intent: dict,
    market_context: list[dict[str, Any]],
    competitors: list[str],
) -> bool:
    task_text = f"{project.get('query', '')} {intent.get('industry', '')}"
    lower_task = task_text.casefold()
    if not ("smartphone" in lower_task or "phone" in lower_task or "手机" in task_text):
        return False
    if re.search(r"安卓阵营|只看安卓|仅安卓|android\s*only|不考虑苹果|排除苹果|不要苹果", task_text, re.I):
        return False
    context_text = json.dumps(market_context, ensure_ascii=False).casefold()
    if not re.search(r"\biphone\s*\d{1,2}\b|apple iphone|苹果\s*iphone", context_text, re.I):
        return False
    competitor_text = " ".join(competitors).casefold()
    return not re.search(r"\biphone\b|apple|苹果", competitor_text, re.I)


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


def validate_competitor_names(competitors: list[str]) -> None:
    invalid = [name for name in competitors if is_invalid_competitor_name(name)]
    if invalid:
        raise ValueError(f"Invalid competitor names from CompetitorDiscoveryAgent: {invalid}")


def validate_discovered_competitors(project: dict, intent: dict, competitors: list[str], max_count: int) -> None:
    validate_competitor_names(competitors)
    if not competitors:
        raise ValueError("CompetitorDiscoveryAgent returned no competitors.")
    if is_recency_sensitive_product_task(project, intent) and not is_historical_task(project, intent):
        stale_names = stale_year_mentions(competitors)
        if stale_names:
            raise ValueError(
                "CompetitorDiscoveryAgent returned product names with stale year markers for a current product task: "
                + ", ".join(stale_names[:6])
            )
    task_text = f"{project.get('query', '')} {intent.get('industry', '')}"
    auto_expected = bool(re.search(r"(?:自动|自行|AI|模型).*(?:选择|发现|推荐|找出).*竞品", task_text, flags=re.I))
    minimum = max_count if auto_expected and max_count >= 2 else min(2, max_count)
    if len(competitors) < minimum:
        raise ValueError(f"CompetitorDiscoveryAgent returned {len(competitors)} competitors, expected at least {minimum}.")
    if len({name.casefold() for name in competitors}) != len(competitors):
        raise ValueError("CompetitorDiscoveryAgent returned duplicate competitors.")


def validate_source_plan(plan: list[dict[str, Any]], competitors: list[str]) -> None:
    if not plan:
        raise ValueError("SourcePlanningAgent returned an empty source plan.")
    grouped = Counter(item.get("competitor") for item in plan)
    missing = [competitor for competitor in competitors if grouped[competitor] < 3]
    if missing:
        raise ValueError(f"SourcePlanningAgent returned fewer than 3 searches for competitors: {missing[:6]}")
    required = {"official", "pricing", "review"}
    weak = []
    for competitor in competitors:
        source_types = {str(item.get("source_type", "")) for item in plan if item.get("competitor") == competitor}
        if len(required & source_types) < 2:
            weak.append(competitor)
    if weak:
        raise ValueError(f"SourcePlanningAgent source mix is too weak for competitors: {weak[:6]}")


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
    if "smartphone" in lower or "phone" in lower or "手机" in industry:
        return ["iPhone 17", "小米 17 Pro Max", "OPPO Find X9 Pro", "vivo X300 Pro", "荣耀 Magic8 Pro", "华为 Mate 70 Pro"]
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
    current_year, previous_year = analysis_years()
    if "smartphone" in lower or "phone" in lower or "手机" in industry:
        suffix = {
            "official": f"最新 在售 {current_year} {previous_year} 官网 官方 参数 配置 价格",
            "pricing": f"最新 在售 现价 到手价 京东 天猫 官方商城 促销 {current_year} {previous_year}",
            "docs": "参数 芯片 影像 屏幕 续航 快充 系统",
            "review": f"最新 评测 优缺点 用户评价 影像 续航 性能 {current_year} {previous_year}",
            "news": f"新品 发布 {current_year} {previous_year} 手机",
            "changelog": "系统 更新 版本 OTA 新功能",
            "github": "评测 benchmark teardown",
        }[source_type]
        return f"{competitor} {industry} {suffix}"
    if "laptop" in lower or "notebook" in lower or "笔记本" in industry or "电脑" in industry:
        suffix = {
            "official": f"最新 在售 {current_year} {previous_year} 官方 参数 配置 价格",
            "pricing": f"最新 在售 现价 到手价 京东 天猫 促销 {current_year} {previous_year}",
            "docs": "CPU 显卡 屏幕 续航 重量 接口 参数",
            "review": f"最新 评测 优缺点 用户评价 散热 噪音 {current_year} {previous_year}",
            "news": f"新品 发布 {current_year} {previous_year} 笔记本",
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


def normalize_llm_specialist_findings(agent: str, values: object, valid_evidence_ids: set[str]) -> list[dict]:
    if not isinstance(values, list):
        return []
    findings: list[dict] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        claim = normalize_text(str(item.get("claim", "")))
        if not claim:
            continue
        evidence_ids = sanitize_evidence_ids(item.get("evidence_ids", []), valid_evidence_ids)
        claim_type = normalize_claim_type(str(item.get("claim_type", "inference")))
        if not evidence_ids and claim_type != "unknown":
            claim_type = "unknown"
        findings.append(
            finding(
                agent,
                claim_type,
                normalize_text(str(item.get("subject") or "overall"))[:120],
                claim[:520],
                evidence_ids[:5],
                clamp_float(item.get("confidence", 0.55), 0.1, 0.88 if evidence_ids else 0.35),
                normalize_risk_level(str(item.get("risk_level", "medium"))),
            )
        )
    return findings


def merge_findings(existing: object, llm_findings: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for item in [*(existing if isinstance(existing, list) else []), *llm_findings]:
        if not isinstance(item, dict):
            continue
        claim = normalize_text(str(item.get("claim", "")))
        if not claim:
            continue
        key = claim.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged[:14]


def sanitize_evidence_ids(values: object, valid_evidence_ids: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    ids: list[str] = []
    for value in values:
        text = str(value)
        if text in valid_evidence_ids and text not in ids:
            ids.append(text)
    return ids


def normalize_claim_type(value: str) -> str:
    value = value.strip().lower()
    if value in {"fact", "inference", "recommendation", "opportunity", "unknown"}:
        return value
    return "inference"


def normalize_risk_level(value: str) -> str:
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


QUALITY_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "fit_for_user_task": {"type": "boolean"},
        "domain_mismatch": {"type": "boolean"},
        "suggested_status": {"type": "string"},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "required_fixes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["fit_for_user_task", "domain_mismatch", "suggested_status", "warnings", "required_fixes"],
    "additionalProperties": True,
}


def quality_review_prompt(project: dict, intent: dict, competitors: list[Competitor], analysis: dict, warnings: list[str]) -> str:
    profiles = [
        {
            "name": competitor.name,
            "product_category": competitor.profile.get("product_category"),
            "features": [feature.get("name") for feature in competitor.profile.get("features", [])[:10]],
            "positioning": competitor.profile.get("positioning", {}).get("short_summary"),
            "source_assessment": competitor.profile.get("source_assessment", {}),
        }
        for competitor in competitors
    ]
    return f"""
Review whether this competitive intelligence run fits the user's requested task.

Project:
{json.dumps(project, ensure_ascii=False)}

Intent:
{json.dumps(intent, ensure_ascii=False)}

Competitor profiles:
{json.dumps(profiles, ensure_ascii=False)}

Analysis summary:
{json.dumps({key: analysis.get(key) for key in ["comparison_dimensions", "strategic_insights", "competitor_cards", "evidence_gaps"]}, ensure_ascii=False)}

Existing warnings:
{json.dumps(warnings, ensure_ascii=False)}

Rules:
- Mark domain_mismatch=true if the feature dimensions or product categories do not match the user's category.
- For example, a phone report containing SaaS dimensions like RAG, API, enterprise controls, project management, database tables is a severe mismatch unless the task explicitly asks for phone AI software services.
- Suggested status should be one of: pass, pass_with_warnings, needs_revision.
- Required fixes should be concrete implementation/report fixes, not generic advice.
"""


def critical_quality_failures(
    project: dict,
    competitors: list[Competitor],
    evidence: list[Evidence],
    claims: list[Claim],
    quality_score: dict,
    warnings: list[str],
    ai_review: dict,
) -> list[str]:
    failures: list[str] = []
    query = str(project.get("query", ""))
    expected_count = int(project.get("max_competitors") or 0)
    auto_discovery = bool(re.search(r"(?:自动|自行|AI|模型).*(?:选择|发现|推荐|找出).*竞品", query, flags=re.I))
    if auto_discovery and expected_count and len(competitors) < expected_count:
        failures.append(f"expected {expected_count} discovered competitors, got {len(competitors)}")
    if len(competitors) < 2:
        failures.append("fewer than 2 competitors")
    invalid = [competitor.name for competitor in competitors if is_invalid_competitor_name(competitor.name)]
    if invalid:
        failures.append(f"invalid competitor names: {invalid[:4]}")
    if not evidence:
        failures.append("no evidence was collected")
    if not claims:
        failures.append("no claims were produced")
    if ai_review.get("domain_mismatch"):
        failures.append("LLM quality review detected domain mismatch")
    if ai_review.get("fit_for_user_task") is False:
        failures.append("LLM quality review says report does not fit the user task")
    severe_warning_markers = ["Relevance high", "Domain high", "runtime fallback", "LLM fallback"]
    for warning in warnings:
        if any(marker.lower() in str(warning).lower() for marker in severe_warning_markers):
            failures.append(str(warning))
    return failures


def collect_runtime_fallback_warnings(outputs: dict, competitors: list[Competitor]) -> list[str]:
    warnings: list[str] = []
    discovery_payload = outputs.get("competitor_discovery", {}).get("payload", {})
    discovery_reason = discovery_payload.get("discovery_fallback_reason")
    if discovery_reason:
        warnings.append(f"LLM fallback high: CompetitorDiscoveryAgent failed and used deterministic competitors. Error: {discovery_reason}")

    source_payload = outputs.get("source_planning", {}).get("payload", {})
    if source_payload and source_payload.get("llm_used") is False:
        reason = source_payload.get("source_planning_fallback_reason") or "LLM source planning was not used."
        warnings.append(f"LLM fallback high: SourcePlanningAgent used deterministic source queries. Error: {reason}")

    analysis_source_mix = outputs.get("analysis", {}).get("source_mix", {})
    llm_synthesis = analysis_source_mix.get("llm_synthesis") if isinstance(analysis_source_mix, dict) else {}
    if isinstance(llm_synthesis, dict) and llm_synthesis.get("used") is False and llm_synthesis.get("error"):
        warnings.append(f"LLM fallback high: AnalysisAgent used deterministic synthesis. Error: {llm_synthesis.get('error')}")

    failed_profiles = []
    for competitor in competitors:
        extraction = competitor.profile.get("llm_extraction", {})
        if isinstance(extraction, dict) and extraction.get("used") is False:
            failed_profiles.append(f"{competitor.name}: {extraction.get('error') or 'unknown error'}")
    if failed_profiles:
        warnings.append("LLM fallback high: SchemaExtractionAgent failed for profiles: " + "; ".join(failed_profiles[:5]))
    return warnings


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
    category = profile.get("product_category", "")
    if "laptop" in category:
        if "direct sales" in business_model:
            signals.append("official/direct sales")
        if "channel retail" in business_model:
            signals.append("e-commerce/channel retail")
        if "enterprise procurement" in business_model:
            signals.append("business procurement")
        if profile.get("pricing"):
            signals.append("price-band competition")
        return signals or ["hardware retail"]
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
    if "laptop" in profile.get("product_category", ""):
        if "enterprise procurement" in models:
            return "hardware portfolio + business procurement channels"
        if "channel retail" in models:
            return "hardware retail through marketplace and official channels"
        return "consumer hardware product-line competition"
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
    if "laptop" in category:
        return "围绕明确价位段、性能释放、屏幕/续航体验、售后和渠道价格透明度寻找差异化。"
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
    weak_source_types = {"unverified", "crawl_failed"}
    high_confidence_source_types = source_types - weak_source_types - {"search_snippet"}
    verified_evidence = [item for item in evidence if item.source_type not in weak_source_types and item.credibility_score >= 0.35]
    high_confidence_evidence = [item for item in verified_evidence if item.source_type in high_confidence_source_types and item.credibility_score >= 0.55]
    verified_ids = {item.id for item in verified_evidence}
    weighted_coverage = len(high_confidence_evidence) + 0.45 * (len(verified_evidence) - len(high_confidence_evidence))
    coverage_ratio = min(1.0, weighted_coverage / (competitor_count * 4))
    source_diversity = min(1.0, len(source_types - weak_source_types - {"search_snippet"}) / 5)
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
