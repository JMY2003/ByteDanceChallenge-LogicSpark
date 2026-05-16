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
    "LlamaIndex": [
        {
            "url": "offline://llamaindex/product",
            "title": "LlamaIndex framework fixture",
            "source_type": "official",
            "content": "LlamaIndex is positioned around data frameworks for LLM applications, with retrieval, indexing, agents, workflows and connectors for private or enterprise data.",
        },
        {
            "url": "offline://llamaindex/github",
            "title": "LlamaIndex open-source fixture",
            "source_type": "github",
            "content": "Open-source signals include GitHub repository activity, integrations, examples, releases and community usage. Live stars, forks and release cadence should be refreshed.",
        },
    ],
    "Flowise": [
        {
            "url": "offline://flowise/product",
            "title": "Flowise product fixture",
            "source_type": "official",
            "content": "Flowise is a low-code visual builder for LLM flows, chatbots, agent workflows and RAG applications. It targets teams that want drag-and-drop orchestration.",
        },
        {
            "url": "offline://flowise/github",
            "title": "Flowise open-source fixture",
            "source_type": "github",
            "content": "Open-source signals include self-hosting interest, community templates, integrations and release activity. Exact GitHub metrics require live verification.",
        },
    ],
    "CrewAI": [
        {
            "url": "offline://crewai/product",
            "title": "CrewAI agent orchestration fixture",
            "source_type": "official",
            "content": "CrewAI is positioned as a framework and platform for multi-agent collaboration, role-based agents, tasks, tools and process orchestration.",
        },
        {
            "url": "offline://crewai/github",
            "title": "CrewAI open-source fixture",
            "source_type": "github",
            "content": "Open-source signals include GitHub repository activity, examples, issues and release cadence. Live community metrics should be refreshed before investment-grade claims.",
        },
    ],
    "AutoGen": [
        {
            "url": "offline://autogen/product",
            "title": "AutoGen agent framework fixture",
            "source_type": "official",
            "content": "AutoGen is associated with multi-agent conversation patterns, agent orchestration, tool use and research-to-production experimentation for LLM applications.",
        },
        {
            "url": "offline://autogen/github",
            "title": "AutoGen open-source fixture",
            "source_type": "github",
            "content": "Open-source signals include examples, releases, community discussion and repository activity. Current metrics require live GitHub verification.",
        },
    ],
    "Linear": [
        {
            "url": "offline://linear/product",
            "title": "Linear product fixture",
            "source_type": "official",
            "content": "Linear is positioned as project management and issue tracking software for product and engineering teams, with roadmap, cycles, workflow automation and integrations.",
        },
        {
            "url": "offline://linear/pricing",
            "title": "Linear pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include free or starter packaging, paid team plans and enterprise controls. Current seat prices and AI packaging require live verification.",
        },
        {
            "url": "offline://linear/reviews",
            "title": "Linear user voice fixture",
            "source_type": "review",
            "content": "Review signals often praise speed, design quality and engineering workflow fit. Possible concerns include fit for non-technical teams and advanced portfolio needs.",
        },
    ],
    "Jira": [
        {
            "url": "offline://jira/product",
            "title": "Jira product fixture",
            "source_type": "official",
            "content": "Jira is positioned as work management and issue tracking for agile software teams, with sprints, boards, automation, reporting, permissions and ecosystem integrations.",
        },
        {
            "url": "offline://jira/pricing",
            "title": "Jira pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include free, standard, premium and enterprise-style tiers. Exact prices, user limits and cloud/data-center packaging require live verification.",
        },
        {
            "url": "offline://jira/reviews",
            "title": "Jira user voice fixture",
            "source_type": "review",
            "content": "Review signals often praise configurability and enterprise fit. Negative themes can include complexity, administration overhead and workflow sprawl.",
        },
    ],
    "Asana": [
        {
            "url": "offline://asana/product",
            "title": "Asana product fixture",
            "source_type": "official",
            "content": "Asana is positioned as work management software for cross-functional teams, with projects, goals, portfolios, automation, timelines and collaboration views.",
        },
        {
            "url": "offline://asana/pricing",
            "title": "Asana pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include free and paid team tiers plus enterprise packaging. Exact feature gates and AI-related packaging require current verification.",
        },
        {
            "url": "offline://asana/reviews",
            "title": "Asana user voice fixture",
            "source_type": "review",
            "content": "Review signals often praise usability and cross-team visibility. Concerns can include pricing at scale and limits for deep engineering issue workflows.",
        },
    ],
    "Monday.com": [
        {
            "url": "offline://monday/product",
            "title": "Monday.com product fixture",
            "source_type": "official",
            "content": "Monday.com is positioned as a flexible work operating system for project management, CRM-style workflows, automation, dashboards and team collaboration.",
        },
        {
            "url": "offline://monday/pricing",
            "title": "Monday.com pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include multiple paid tiers and enterprise packaging. Seat minimums, automation limits and AI features require live verification.",
        },
        {
            "url": "offline://monday/reviews",
            "title": "Monday.com user voice fixture",
            "source_type": "review",
            "content": "Review signals often praise flexibility, dashboards and visual workflow setup. Concerns can include configuration effort and cost as teams scale.",
        },
    ],
    "Runway": [
        {
            "url": "offline://runway/product",
            "title": "Runway AI video fixture",
            "source_type": "official",
            "content": "Runway is positioned as an AI creative platform for video generation, editing, image-to-video, text-to-video workflows and professional creative production.",
        },
        {
            "url": "offline://runway/pricing",
            "title": "Runway pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include credit or usage-based creative generation tiers, paid creator plans and team/enterprise options. Live credit rules require verification.",
        },
        {
            "url": "offline://runway/reviews",
            "title": "Runway user voice fixture",
            "source_type": "review",
            "content": "User voice signals often focus on generation quality, creative control, workflow speed, output consistency and cost per usable clip.",
        },
    ],
    "Pika": [
        {
            "url": "offline://pika/product",
            "title": "Pika AI video fixture",
            "source_type": "official",
            "content": "Pika is positioned around accessible AI video generation, prompt-driven video creation, image animation and social-friendly creative workflows.",
        },
        {
            "url": "offline://pika/pricing",
            "title": "Pika pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include free or trial usage, paid creator tiers and usage credits. Exact model access and generation limits require live verification.",
        },
        {
            "url": "offline://pika/reviews",
            "title": "Pika user voice fixture",
            "source_type": "review",
            "content": "User voice signals often discuss ease of use, playful effects, motion quality, wait time, watermarking and credit consumption.",
        },
    ],
    "Kling": [
        {
            "url": "offline://kling/product",
            "title": "Kling AI video fixture",
            "source_type": "official",
            "content": "Kling is positioned as an AI video generation product with text-to-video, image-to-video and high-motion creative generation signals.",
        },
        {
            "url": "offline://kling/pricing",
            "title": "Kling pricing fixture",
            "source_type": "pricing",
            "content": "Pricing and access signals may involve credits, membership tiers, waitlists or regional availability. Exact plan terms require live verification.",
        },
        {
            "url": "offline://kling/reviews",
            "title": "Kling user voice fixture",
            "source_type": "review",
            "content": "User voice signals often focus on video realism, motion coherence, prompt adherence, queue speed and access availability.",
        },
    ],
    "Luma": [
        {
            "url": "offline://luma/product",
            "title": "Luma Dream Machine fixture",
            "source_type": "official",
            "content": "Luma is associated with AI video generation and 3D/creative tooling, with Dream Machine-style text-to-video and image-to-video workflows.",
        },
        {
            "url": "offline://luma/pricing",
            "title": "Luma pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include free generation capacity, paid plans or priority usage. Exact credit rules and commercial terms require live verification.",
        },
        {
            "url": "offline://luma/reviews",
            "title": "Luma user voice fixture",
            "source_type": "review",
            "content": "User voice signals often discuss cinematic motion, realism, waiting time, generation limits and output control.",
        },
    ],
    "Perplexity": [
        {
            "url": "offline://perplexity/product",
            "title": "Perplexity AI search fixture",
            "source_type": "official",
            "content": "Perplexity is positioned as an AI answer engine and search product that returns sourced answers, follow-up exploration and research workflows.",
        },
        {
            "url": "offline://perplexity/pricing",
            "title": "Perplexity pricing fixture",
            "source_type": "pricing",
            "content": "Pricing signals include free access and Pro-style paid tiers with advanced model access or higher usage. Current plan limits require live verification.",
        },
        {
            "url": "offline://perplexity/reviews",
            "title": "Perplexity user voice fixture",
            "source_type": "review",
            "content": "User voice signals often praise concise sourced answers and research speed. Concerns may include source quality, hallucination risk and subscription value.",
        },
    ],
    "秘塔 AI 搜索": [
        {
            "url": "offline://metaso/product",
            "title": "秘塔 AI 搜索 fixture",
            "source_type": "official",
            "content": "秘塔 AI 搜索定位于中文 AI 搜索和答案生成，常见能力信号包括联网搜索、资料整合、引用来源和长文档理解。",
        },
        {
            "url": "offline://metaso/pricing",
            "title": "秘塔 AI 搜索价格 fixture",
            "source_type": "pricing",
            "content": "价格和会员权益需要以当前公开页面为准，尤其是搜索次数、模型能力、文件处理和高级功能限制。",
        },
        {
            "url": "offline://metaso/reviews",
            "title": "秘塔 AI 搜索用户声音 fixture",
            "source_type": "review",
            "content": "用户声音常围绕中文搜索体验、引用可查性、资料汇总效率、答案准确性和实时性展开。",
        },
    ],
    "Kimi": [
        {
            "url": "offline://kimi/product",
            "title": "Kimi product fixture",
            "source_type": "official",
            "content": "Kimi is associated with long-context AI assistant and search-style research workflows, including document reading, web information use and Chinese user scenarios.",
        },
        {
            "url": "offline://kimi/pricing",
            "title": "Kimi pricing fixture",
            "source_type": "pricing",
            "content": "Pricing or membership signals need current verification, including model access, usage quotas, long-context limits and advanced features.",
        },
        {
            "url": "offline://kimi/reviews",
            "title": "Kimi user voice fixture",
            "source_type": "review",
            "content": "User voice signals often discuss long-document handling, Chinese writing, search usefulness, latency and model quality stability.",
        },
    ],
    "ChatGPT Search": [
        {
            "url": "offline://chatgpt-search/product",
            "title": "ChatGPT Search fixture",
            "source_type": "official",
            "content": "ChatGPT Search is positioned around conversational AI search with web results, source links, follow-up questions and integration into the ChatGPT assistant experience.",
        },
        {
            "url": "offline://chatgpt-search/pricing",
            "title": "ChatGPT Search pricing fixture",
            "source_type": "pricing",
            "content": "Access and packaging may depend on ChatGPT plan, region and product rollout. Current availability and plan limits require live verification.",
        },
        {
            "url": "offline://chatgpt-search/reviews",
            "title": "ChatGPT Search user voice fixture",
            "source_type": "review",
            "content": "User voice signals often compare answer quality, source freshness, assistant integration, citation usefulness and trust with traditional search.",
        },
    ],
}


def fixture_results_for(competitor: str) -> list[dict]:
    return OFFLINE_SOURCE_FIXTURES.get(competitor, [])


def generic_fixture_results_for(competitor: str, query: str = "") -> list[dict]:
    """Return low-confidence, query-scoped offline scaffolds for unknown competitors.

    These fixtures deliberately avoid pretending to know facts about the product.
    They keep the pipeline relevant to the requested competitor while making QA
    surface that live source collection is still required.
    """

    slug = competitor.replace(" ", "-").replace("/", "-").lower()
    scoped_query = query or f"{competitor} competitive analysis"
    return [
        {
            "url": f"offline://generic/{slug}/source-plan",
            "title": f"{competitor} live-source collection required",
            "source_type": "unverified",
            "content": (
                f"{competitor} was explicitly requested for the task: {scoped_query}. "
                "No bundled public-source fixture exists for this competitor. Product positioning, pricing, "
                "user voice, recent updates, and technical claims must be verified with live official pages, "
                "third-party reviews, documentation, news, or repository data before making strong conclusions."
            ),
        },
        {
            "url": f"offline://generic/{slug}/pricing-gap",
            "title": f"{competitor} pricing evidence gap",
            "source_type": "unverified",
            "content": (
                f"The current offline knowledge base does not contain verified pricing evidence for {competitor}. "
                "Any pricing comparison should be marked unknown or low confidence until the latest pricing page, "
                "plan packaging, usage limits, and enterprise terms are collected."
            ),
        },
        {
            "url": f"offline://generic/{slug}/review-gap",
            "title": f"{competitor} user-review evidence gap",
            "source_type": "unverified",
            "content": (
                f"The current offline knowledge base does not contain independent user-review evidence for {competitor}. "
                "User satisfaction, pain points, adoption barriers, and switching reasons need external review, "
                "community, app-store, or customer-case sources."
            ),
        },
    ]


def fixture_by_url(url: str) -> dict | None:
    for items in OFFLINE_SOURCE_FIXTURES.values():
        for item in items:
            if item["url"] == url:
                return item
    if url.startswith("offline://generic/"):
        parts = url.removeprefix("offline://generic/").split("/")
        competitor = parts[0].replace("-", " ").strip() or "unknown competitor"
        for item in generic_fixture_results_for(competitor):
            if item["url"] == url:
                return item
    return None
