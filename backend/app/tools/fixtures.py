from __future__ import annotations

OFFLINE_SOURCE_FIXTURES: dict[str, list[dict]] = {
    "Notion AI": [
        {
            "url": "offline://notion-ai/product",
            "title": "Notion AI product overview fixture",
            "source_type": "official",
            "content": (
                "Notion AI is positioned as an AI assistant inside a connected workspace. "
                "The product message emphasizes writing assistance, summarization, Q&A over workspace content, "
                "and helping teams move from blank page to useful documents. "
                "Notion combines docs, wikis, databases, projects and AI in one workspace."
            ),
        },
        {
            "url": "offline://notion-ai/pricing",
            "title": "Notion pricing fixture",
            "source_type": "pricing",
            "content": (
                "The fixture pricing page describes a free plan, paid workspace plans, and an AI add-on or AI included "
                "in selected tiers depending on packaging. Enterprise terms are handled by sales. "
                "This pricing signal should be treated as a sample and refreshed against the live pricing page before delivery."
            ),
        },
        {
            "url": "offline://notion-ai/security",
            "title": "Notion security fixture",
            "source_type": "docs",
            "content": (
                "Security and enterprise administration signals include SSO, permission controls, audit-style governance, "
                "and workspace-level controls for larger organizations. Exact certifications require current verification."
            ),
        },
    ],
    "ClickUp AI": [
        {
            "url": "offline://clickup-ai/product",
            "title": "ClickUp AI product overview fixture",
            "source_type": "official",
            "content": (
                "ClickUp AI is framed around productivity, project management, documents, tasks, whiteboards and workflow automation. "
                "AI features support writing, summarizing, extracting action items, and assisting work across project artifacts."
            ),
        },
        {
            "url": "offline://clickup-ai/pricing",
            "title": "ClickUp pricing fixture",
            "source_type": "pricing",
            "content": (
                "The fixture pricing page indicates a free tier, paid team plans, and enterprise custom pricing. "
                "AI capabilities may be bundled or available as a paid capability, so live pricing needs verification."
            ),
        },
        {
            "url": "offline://clickup-ai/reviews",
            "title": "ClickUp user voice fixture",
            "source_type": "review",
            "content": (
                "User-review signals in this fixture praise breadth of features and project-management depth. "
                "Common negative themes are onboarding complexity, configuration overhead, and notification noise."
            ),
        },
    ],
    "Coda AI": [
        {
            "url": "offline://coda-ai/product",
            "title": "Coda AI product overview fixture",
            "source_type": "official",
            "content": (
                "Coda AI is presented as AI in a doc that can combine documents, tables, automation and app-like workflows. "
                "The positioning focuses on teams that want flexible documents that behave like lightweight applications."
            ),
        },
        {
            "url": "offline://coda-ai/pricing",
            "title": "Coda pricing fixture",
            "source_type": "pricing",
            "content": (
                "The fixture pricing signal highlights maker-oriented paid plans, team tiers, enterprise sales, and AI usage controls. "
                "The exact per-user or per-maker price should be verified from the live pricing page."
            ),
        },
        {
            "url": "offline://coda-ai/docs",
            "title": "Coda docs fixture",
            "source_type": "docs",
            "content": (
                "Docs and integration signals include tables, packs, automations, formulas and API-style extensibility. "
                "These signals support a differentiated app-building document positioning."
            ),
        },
    ],
    "飞书": [
        {
            "url": "offline://feishu/product",
            "title": "飞书产品概览 fixture",
            "source_type": "official",
            "content": (
                "飞书在协同办公场景中覆盖即时沟通、文档、知识库、日历、视频会议、审批和开放平台。"
                "AI 能力常被放在会议纪要、知识问答、内容生成和办公自动化等场景中理解。"
            ),
        },
        {
            "url": "offline://feishu/pricing",
            "title": "飞书价格与企业版 fixture",
            "source_type": "pricing",
            "content": (
                "飞书通常区分免费版、商业版和企业定制方案。企业客户关注权限、数据安全、管理后台和生态集成。"
                "具体价格和 AI 权益需要以当前公开价格页为准。"
            ),
        },
    ],
    "钉钉": [
        {
            "url": "offline://dingtalk/product",
            "title": "钉钉产品概览 fixture",
            "source_type": "official",
            "content": (
                "钉钉覆盖组织通讯、协同办公、低代码应用、审批、项目协作和企业服务生态。"
                "AI 相关能力可围绕智能助理、组织知识、会议与流程自动化分析。"
            ),
        },
        {
            "url": "offline://dingtalk/ecosystem",
            "title": "钉钉生态 fixture",
            "source_type": "third_party",
            "content": (
                "生态信号包括开放平台、低代码能力、行业解决方案和服务商网络。"
                "这些信号支持其面向中国企业组织数字化的市场定位。"
            ),
        },
    ],
    "LangChain": [
        {
            "url": "offline://langchain/product",
            "title": "LangChain platform fixture",
            "source_type": "official",
            "content": (
                "LangChain is an AI application development framework and platform. "
                "Signals include orchestration, agents, retrieval workflows, observability and deployment tooling."
            ),
        },
        {
            "url": "offline://langchain/github",
            "title": "LangChain open-source fixture",
            "source_type": "github",
            "content": (
                "Open-source ecosystem signals include a broad integration surface, community packages, examples, issues and releases. "
                "Live GitHub activity should be refreshed before making an investment-grade claim."
            ),
        },
    ],
    "Dify": [
        {
            "url": "offline://dify/product",
            "title": "Dify product fixture",
            "source_type": "official",
            "content": (
                "Dify is positioned as an LLM application development platform with workflow, agent, RAG and operations features. "
                "It targets teams building AI-native applications with visual orchestration and model-provider flexibility."
            ),
        },
        {
            "url": "offline://dify/github",
            "title": "Dify open-source fixture",
            "source_type": "github",
            "content": (
                "Open-source signals include self-hosting interest, community contribution, integrations and release activity. "
                "Exact repository metrics should be fetched live for a current report."
            ),
        },
    ],
}


def fixture_results_for(competitor: str) -> list[dict]:
    return OFFLINE_SOURCE_FIXTURES.get(competitor, [])


def fixture_by_url(url: str) -> dict | None:
    for items in OFFLINE_SOURCE_FIXTURES.values():
        for item in items:
            if item["url"] == url:
                return item
    return None

