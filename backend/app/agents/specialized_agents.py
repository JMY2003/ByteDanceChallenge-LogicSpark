from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import GenericAgentOutput


class GenericSpecializedAgent(BaseAgent):
    output_model = GenericAgentOutput
    name = "GenericSpecializedAgent"
    description = "Specialized non-MVP agent placeholder with schema-valid output."

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        return {
            "agent": self.name,
            "status": "available_not_in_mvp_dag",
            "summary": (
                f"{self.name} is registered and can be added to a DAG. "
                "The current MVP path focuses on query-to-report automation."
            ),
            "evidence_ids": [],
            "payload": {"input_keys": sorted(input_data.keys())},
        }


def make_agent_class(class_name: str, description: str) -> type[GenericSpecializedAgent]:
    return type(class_name, (GenericSpecializedAgent,), {"name": class_name, "description": description})


CompetitorDiscoveryAgent = make_agent_class(
    "CompetitorDiscoveryAgent",
    "Discover direct, indirect, substitute and emerging competitors.",
)
SourcePlanningAgent = make_agent_class(
    "SourcePlanningAgent",
    "Plan official, pricing, docs, review, news, social, GitHub and hiring sources.",
)
DocumentCleanerAgent = make_agent_class(
    "DocumentCleanerAgent",
    "Clean documents, preserve quote locations, chunk content and prepare embeddings.",
)
ProductPositioningAgent = make_agent_class(
    "ProductPositioningAgent",
    "Analyze target users, use cases, value proposition and positioning differences.",
)
FeatureMatrixAgent = make_agent_class(
    "FeatureMatrixAgent",
    "Build horizontal feature matrices with evidence-bound support status.",
)
PricingAnalysisAgent = make_agent_class(
    "PricingAnalysisAgent",
    "Analyze free tiers, paid plans, enterprise pricing and AI charging models.",
)
UserVoiceAgent = make_agent_class(
    "UserVoiceAgent",
    "Mine reviews and community discussions for pros, cons, pain points and sentiment.",
)
TechnologyIntelligenceAgent = make_agent_class(
    "TechnologyIntelligenceAgent",
    "Analyze technology, API, RAG, agent, SDK, infrastructure and security signals.",
)
GTMAgent = make_agent_class(
    "GTMAgent",
    "Analyze go-to-market strategy, channels, partnerships and customer cases.",
)
SWOTAgent = make_agent_class(
    "SWOTAgent",
    "Generate evidence-bound strengths, weaknesses, opportunities and threats.",
)
StrategicInsightAgent = make_agent_class(
    "StrategicInsightAgent",
    "Generate strategic opportunities, risks, differentiators and recommendations.",
)
FactCheckAgent = make_agent_class(
    "FactCheckAgent",
    "Check fact claims for evidence support, freshness and hallucination risk.",
)
CitationCheckAgent = make_agent_class(
    "CitationCheckAgent",
    "Check whether each citation supports its linked claim.",
)
ConsistencyCheckAgent = make_agent_class(
    "ConsistencyCheckAgent",
    "Detect contradictions across pricing, feature, SWOT and recommendation sections.",
)
BiasDetectionAgent = make_agent_class(
    "BiasDetectionAgent",
    "Detect source, competitor, region, segment and over-interpretation bias.",
)
RedTeamAgent = make_agent_class(
    "RedTeamAgent",
    "Challenge evidence sufficiency, omitted competitors and overconfident conclusions.",
)
QualityGateAgent = make_agent_class(
    "QualityGateAgent",
    "Decide whether the report can ship and calculate final delivery warnings.",
)

