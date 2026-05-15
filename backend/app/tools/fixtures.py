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
    "京东": [
        {
            "url": "offline://jd/product",
            "title": "京东平台能力 fixture",
            "source_type": "official",
            "content": (
                "京东是中国综合电商与供应链服务平台，公开定位通常围绕自营零售、3C 家电、物流履约、即时零售和企业采购。"
                "平台能力信号包括京东物流、仓配一体、品质保障、会员体系和商家开放平台。"
            ),
        },
        {
            "url": "offline://jd/pricing",
            "title": "京东商业模式 fixture",
            "source_type": "third_party",
            "content": (
                "商业模式信号包括自营零售差价、平台佣金、广告营销、物流服务、企业服务和会员权益。"
                "具体佣金、广告价格和履约成本需要以当前官方招商与商家规则为准。"
            ),
        },
    ],
    "阿里巴巴": [
        {
            "url": "offline://alibaba/product",
            "title": "阿里巴巴电商生态 fixture",
            "source_type": "official",
            "content": (
                "阿里巴巴电商生态覆盖淘宝、天猫、1688、跨境电商、本地生活与商家服务等场景。"
                "公开能力信号包括平台流量、商家工具、营销体系、支付与云基础设施生态。"
            ),
        },
        {
            "url": "offline://alibaba/merchant",
            "title": "阿里巴巴商家服务 fixture",
            "source_type": "docs",
            "content": (
                "商家服务信号包括店铺经营、广告投放、会员运营、数据分析、直播内容和品牌旗舰店能力。"
                "平台规则与费用需根据当前招商文档和商家后台信息刷新。"
            ),
        },
    ],
    "拼多多": [
        {
            "url": "offline://pinduoduo/product",
            "title": "拼多多平台定位 fixture",
            "source_type": "official",
            "content": (
                "拼多多是以高性价比商品、社交裂变、农产品上行和平台补贴心智著称的电商平台。"
                "能力信号包括低价供给、推荐分发、多人团购、百亿补贴和商家生态。"
            ),
        },
        {
            "url": "offline://pinduoduo/user-voice",
            "title": "拼多多用户心智 fixture",
            "source_type": "review",
            "content": (
                "用户反馈信号常围绕价格吸引力、商品丰富度、履约体验、售后体验和品质感知差异展开。"
                "这些评价需要结合第三方评论和近期用户调研验证。"
            ),
        },
    ],
    "唯品会": [
        {
            "url": "offline://vip/product",
            "title": "唯品会平台定位 fixture",
            "source_type": "official",
            "content": (
                "唯品会公开定位偏向品牌特卖、折扣零售和服饰美妆等垂类消费场景。"
                "平台能力信号包括品牌折扣供应、限时特卖、会员运营、正品保障和垂类用户心智。"
            ),
        },
        {
            "url": "offline://vip/business",
            "title": "唯品会商业模式 fixture",
            "source_type": "third_party",
            "content": (
                "商业模式信号包括品牌特卖、自营与平台结合、营销活动和会员复购。"
                "具体品牌合作和费用信息需要以最新公开财报、招商材料或官方页面为准。"
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
