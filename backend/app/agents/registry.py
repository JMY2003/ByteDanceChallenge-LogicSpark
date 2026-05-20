from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.mvp_agents import (
    AnalysisAgent,
    EvidenceBuilderAgent,
    IntentAgent,
    PlannerAgent,
    ReportWriterAgent,
    SchemaExtractionAgent,
    WebCrawlerAgent,
    WebSearchAgent,
)
from app.agents.specialized_agents import (
    BiasDetectionAgent,
    CitationCheckAgent,
    CompetitorDiscoveryAgent,
    ConsistencyCheckAgent,
    FactCheckAgent,
    FeatureMatrixAgent,
    GTMAgent,
    PricingAnalysisAgent,
    ProductPositioningAgent,
    QualityGateAgent,
    RedTeamAgent,
    SourcePlanningAgent,
    SWOTAgent,
    StrategicInsightAgent,
    TechnologyIntelligenceAgent,
    UserVoiceAgent,
)


def build_agent_registry() -> dict[str, BaseAgent]:
    agents: list[BaseAgent] = [
        IntentAgent(),
        PlannerAgent(),
        CompetitorDiscoveryAgent(),
        SourcePlanningAgent(),
        WebSearchAgent(),
        WebCrawlerAgent(),
        SchemaExtractionAgent(),
        EvidenceBuilderAgent(),
        AnalysisAgent(),
        ProductPositioningAgent(),
        FeatureMatrixAgent(),
        PricingAnalysisAgent(),
        UserVoiceAgent(),
        TechnologyIntelligenceAgent(),
        GTMAgent(),
        SWOTAgent(),
        StrategicInsightAgent(),
        FactCheckAgent(),
        CitationCheckAgent(),
        ConsistencyCheckAgent(),
        BiasDetectionAgent(),
        RedTeamAgent(),
        ReportWriterAgent(),
        QualityGateAgent(),
    ]
    return {agent.name: agent for agent in agents}
