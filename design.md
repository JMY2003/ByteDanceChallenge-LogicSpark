下面是一份**可直接喂给 AI Coding 工具的完整需求说明**。它不是简单做一个“竞品分析报告生成器”，而是设计成一个**多 Agent 协作、DAG 任务编排、可溯源、可观测、可审计、可持续迭代的竞品情报分析系统**。

你可以把下面整段当作项目需求 Prompt 使用。

---

# AI 驱动的竞品分析 Agent 协作系统需求说明

## 1. 项目名称

**CompeteScope AI：AI 驱动的竞品分析 Agent 协作系统**

## 2. 项目背景

在企业产品研发、市场战略、投融资分析和行业洞察场景中，竞品分析通常存在以下问题：

1. 信息源高度分散，包括官网、产品文档、价格页、新闻稿、社交媒体、招聘信息、用户评论、应用商店、融资信息、技术博客、论文、开源仓库等。
2. 分析流程重复且耗时，需要人工搜索、整理、比对、归纳、撰写报告。
3. 结论强依赖个人经验，不同分析人员输出质量不稳定。
4. 分析结果缺乏可追溯性，无法清楚说明某个判断来自哪个信息源。
5. 竞品报告往往是一次性文档，难以持续更新、复盘和版本管理。
6. 多人协作时缺少结构化知识 Schema，导致信息重复、遗漏和口径不一致。
7. 使用大模型生成报告时容易出现幻觉、引用不准确、证据不足等问题。

本项目目标是构建一个**AI 驱动的竞品分析 Agent 协作系统**，模拟真实的数字调研小组，通过多个专职 Agent 的协同，自动完成从公开信息采集、证据整理、结构化建模、竞品分析、交叉审查、报告生成到可视化输出的全链路工作。

---

# 3. 总体目标

系统应支持用户输入一个分析主题，例如：

> “帮我分析 Notion AI、ClickUp AI、Coda AI、飞书妙记在 AI 办公协作领域的竞争格局。”

系统需要自动完成：

1. 识别目标行业、核心竞品、分析维度和报告目标。
2. 基于公开信息源自动采集竞品资料。
3. 将采集内容清洗、去重、切片、嵌入并存入知识库。
4. 按自定义竞品知识 Schema 抽取结构化信息。
5. 多 Agent 分工分析不同维度，包括产品、功能、价格、技术、用户反馈、市场定位、商业模式、增长策略等。
6. 对所有分析结论建立证据链，要求每条结论可追溯到具体来源。
7. 通过审查 Agent 进行事实核查、逻辑校验、引用校验和风险提示。
8. 通过 DAG 式任务流转实现 Agent 协作、失败重试、人工介入和反馈闭环。
9. 生成结构化竞品报告，包括 Markdown、HTML、PDF、PPT 大纲、JSON 数据等形式。
10. 在前端展示 Agent 执行过程、中间产物、证据来源、任务图谱和分析结果。

---

# 4. 核心产品定位

该系统不是普通的聊天机器人，而是一个具备以下能力的**Agentic Research Operating System**：

1. **多 Agent 协作**

   * 每个 Agent 有独立角色、目标、输入、输出和评价标准。
   * Agent 之间通过任务图和共享知识库协作。

2. **DAG 任务编排**

   * 每个分析任务被拆解成多个节点。
   * 节点之间存在依赖关系。
   * 支持并行、串行、条件分支、失败重试和人工确认。

3. **结构化竞品知识 Schema**

   * 所有竞品信息都映射到统一 Schema。
   * 支持跨竞品横向对比。

4. **强溯源**

   * 每条结论必须绑定证据来源。
   * 支持查看原文、摘要、引用片段、置信度和 Agent 推理过程摘要。

5. **可观测性**

   * 记录每个 Agent 的输入、输出、工具调用、耗时、Token 消耗、失败原因和置信度。
   * 提供任务运行 Trace 页面。

6. **质量控制**

   * 引入 Critic Agent、Fact-check Agent、Citation-check Agent、Risk Agent 等进行交叉审查。

7. **持续更新**

   * 支持定时刷新竞品信息。
   * 支持历史版本对比。
   * 支持“本周竞品动态报告”。

---

# 5. 目标用户

系统主要面向：

1. 产品经理
2. 市场分析师
3. 战略研究员
4. 创业公司创始人
5. 投资分析师
6. 咨询顾问
7. ToB 企业研发团队
8. AI 产品团队
9. 高校和研究机构的技术趋势研究人员

---

# 6. 典型使用场景

## 6.1 产品经理做竞品调研

用户输入：

> 我们准备做一个 AI 知识库产品，请分析 Notion、Mem、Reflect、Tana、Obsidian、飞书知识库的竞争格局。

系统输出：

1. 核心竞品列表
2. 产品定位对比
3. 功能矩阵
4. 价格策略对比
5. 用户痛点总结
6. 机会点分析
7. 差异化建议
8. 可溯源报告

---

## 6.2 投资人做行业初筛

用户输入：

> 分析 AI Agent 基础设施领域的核心玩家，包括 LangChain、LlamaIndex、CrewAI、AutoGen、Dify、Flowise。

系统输出：

1. 公司/项目背景
2. 产品形态
3. 开源活跃度
4. 商业化进展
5. 技术壁垒
6. 社区增长
7. 风险因素
8. 投资观察建议

---

## 6.3 企业内部做定期竞品监控

用户设置：

> 每周一早上生成一次“AI CRM 领域竞品动态报告”。

系统自动输出：

1. 本周竞品新功能
2. 价格变化
3. 新融资/合作/收购信息
4. 新用户评价
5. 招聘方向变化
6. GitHub 或技术博客动态
7. 风险预警

---

# 7. 系统总体架构

系统分为以下几层：

```text
用户输入层
  ↓
任务规划层 Planner
  ↓
DAG 编排层 Orchestrator
  ↓
多 Agent 协作层
  ├── 采集类 Agent
  ├── 清洗类 Agent
  ├── 抽取类 Agent
  ├── 分析类 Agent
  ├── 撰写类 Agent
  └── 审查类 Agent
  ↓
工具层 Tools
  ├── Web Search
  ├── Web Crawler
  ├── Browser Agent
  ├── Document Parser
  ├── Vector Search
  ├── Database Query
  ├── Code Interpreter
  └── Report Renderer
  ↓
知识层 Knowledge Base
  ├── 原始网页库
  ├── 文档切片库
  ├── 向量库
  ├── 结构化竞品库
  ├── 证据库
  └── 任务运行日志库
  ↓
质量控制层 QA
  ├── Fact Check
  ├── Citation Check
  ├── Consistency Check
  ├── Hallucination Detection
  └── Risk Review
  ↓
报告输出层
  ├── Markdown
  ├── HTML
  ├── PDF
  ├── PPT 大纲
  ├── JSON
  └── Dashboard
```

---

# 8. 多 Agent 角色设计

系统至少需要包含以下 Agent。

---

## 8.1 User Intent Agent：用户意图理解 Agent

### 职责

解析用户输入，识别：

1. 分析对象
2. 行业范围
3. 目标竞品
4. 分析深度
5. 输出格式
6. 时间范围
7. 语言要求
8. 是否需要定期监控
9. 是否需要投资视角、产品视角或技术视角

### 输入

```json
{
  "user_query": "分析 Notion AI、ClickUp AI、Coda AI 的竞品格局",
  "language": "zh-CN"
}
```

### 输出

```json
{
  "analysis_topic": "AI 办公协作工具竞品分析",
  "target_companies": ["Notion AI", "ClickUp AI", "Coda AI"],
  "industry": "AI productivity / collaboration software",
  "analysis_depth": "deep",
  "report_type": "competitive_analysis",
  "required_dimensions": [
    "product_positioning",
    "features",
    "pricing",
    "user_feedback",
    "market_strategy",
    "technical_capability",
    "risk",
    "opportunity"
  ],
  "output_formats": ["markdown", "html", "json"],
  "needs_source_citation": true
}
```

---

## 8.2 Planner Agent：任务规划 Agent

### 职责

将用户意图拆解为 DAG 任务图。

需要生成：

1. 任务节点
2. 节点依赖关系
3. 每个节点所需 Agent
4. 每个节点输入输出 Schema
5. 优先级
6. 可并行任务
7. 失败重试策略
8. 是否需要人工确认

### 输出示例

```json
{
  "dag": {
    "nodes": [
      {
        "id": "discover_competitors",
        "agent": "CompetitorDiscoveryAgent",
        "depends_on": [],
        "priority": 1
      },
      {
        "id": "collect_official_sources",
        "agent": "OfficialSourceCollectorAgent",
        "depends_on": ["discover_competitors"],
        "priority": 2
      },
      {
        "id": "collect_reviews",
        "agent": "UserReviewCollectorAgent",
        "depends_on": ["discover_competitors"],
        "priority": 2
      },
      {
        "id": "extract_product_schema",
        "agent": "SchemaExtractionAgent",
        "depends_on": ["collect_official_sources", "collect_reviews"],
        "priority": 3
      },
      {
        "id": "analyze_feature_matrix",
        "agent": "FeatureAnalysisAgent",
        "depends_on": ["extract_product_schema"],
        "priority": 4
      },
      {
        "id": "fact_check",
        "agent": "FactCheckAgent",
        "depends_on": ["analyze_feature_matrix"],
        "priority": 5
      },
      {
        "id": "write_report",
        "agent": "ReportWriterAgent",
        "depends_on": ["fact_check"],
        "priority": 6
      }
    ]
  }
}
```

---

## 8.3 Competitor Discovery Agent：竞品发现 Agent

### 职责

当用户只给出行业或产品方向时，自动发现核心竞品。

例如用户输入：

> 帮我分析 AI 知识库产品市场。

系统需要自动找出：

1. 直接竞品
2. 间接竞品
3. 替代方案
4. 开源方案
5. 新兴创业公司
6. 大厂内部产品

### 发现维度

1. 搜索引擎结果
2. 行业榜单
3. G2 / Capterra / Product Hunt / GitHub / App Store 等
4. 新闻报道
5. 投融资数据库
6. 社交媒体热度
7. 开源社区活跃度

### 输出

```json
{
  "competitors": [
    {
      "name": "Notion AI",
      "type": "direct",
      "confidence": 0.95,
      "reason": "AI workspace product with document, database and assistant features",
      "evidence_ids": ["ev_001", "ev_002"]
    },
    {
      "name": "Obsidian",
      "type": "indirect",
      "confidence": 0.72,
      "reason": "Personal knowledge management tool with AI plugin ecosystem",
      "evidence_ids": ["ev_003"]
    }
  ]
}
```

---

## 8.4 Source Planning Agent：信息源规划 Agent

### 职责

为每个竞品规划需要采集的信息源。

每个竞品至少需要覆盖：

1. 官网首页
2. 产品功能页
3. Pricing 页面
4. Docs / API 文档
5. Blog / Changelog
6. Help Center
7. 用户评价网站
8. 社交媒体
9. 新闻报道
10. 招聘页面
11. GitHub / 开源仓库
12. App Store / Chrome Store / 插件市场
13. YouTube / Demo 视频
14. 融资 / 公司数据库
15. 论文 / 技术报告

### 输出

```json
{
  "source_plan": [
    {
      "competitor": "Notion AI",
      "source_type": "official_website",
      "query": "Notion AI official features pricing",
      "priority": "high"
    },
    {
      "competitor": "Notion AI",
      "source_type": "user_review",
      "query": "Notion AI user reviews pros cons",
      "priority": "medium"
    }
  ]
}
```

---

## 8.5 Web Search Agent：公开信息搜索 Agent

### 职责

根据 Source Planning Agent 的信息源规划，调用搜索工具获取候选链接。

要求：

1. 支持多关键词搜索。
2. 支持按语言搜索。
3. 支持按时间范围搜索。
4. 支持搜索结果去重。
5. 支持结果可信度初筛。
6. 支持记录搜索 Query、返回链接、排序和时间戳。

### 输出

```json
{
  "search_results": [
    {
      "url": "https://example.com/pricing",
      "title": "Product Pricing",
      "snippet": "Pricing plans for ...",
      "source_type": "pricing",
      "rank": 1,
      "query": "xxx pricing",
      "retrieved_at": "2026-05-15T10:00:00Z"
    }
  ]
}
```

---

## 8.6 Web Crawler Agent：网页采集 Agent

### 职责

采集网页正文内容。

要求：

1. 尊重 robots.txt、网站条款和合理访问频率。
2. 不绕过登录、验证码、付费墙和访问限制。
3. 支持静态网页抓取。
4. 支持动态网页渲染。
5. 支持正文抽取。
6. 支持标题、发布时间、作者、网站名、URL、正文、截图等元信息。
7. 支持失败重试。
8. 支持网页快照存储。
9. 支持内容 Hash 去重。

### 输出

```json
{
  "document": {
    "doc_id": "doc_001",
    "url": "https://example.com/pricing",
    "title": "Pricing",
    "content": "Full extracted text...",
    "html_snapshot_path": "...",
    "screenshot_path": "...",
    "content_hash": "sha256...",
    "source_type": "pricing",
    "retrieved_at": "2026-05-15T10:02:00Z"
  }
}
```

---

## 8.7 Document Cleaner Agent：文档清洗 Agent

### 职责

清洗采集到的网页和文档内容。

需要完成：

1. 去除导航栏、页脚、广告、Cookie 提示。
2. 提取正文。
3. 提取表格。
4. 提取 FAQ。
5. 提取价格信息。
6. 提取产品功能描述。
7. 保留原始引用位置。
8. 对内容进行分段切片。
9. 为每个 chunk 生成 chunk_id。
10. 存入向量数据库。

### 输出

```json
{
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "doc_id": "doc_001",
      "text": "The Pro plan costs ...",
      "section_title": "Pricing",
      "start_char": 120,
      "end_char": 480,
      "source_url": "https://example.com/pricing"
    }
  ]
}
```

---

## 8.8 Schema Extraction Agent：结构化抽取 Agent

### 职责

从文档 chunk 中抽取符合竞品知识 Schema 的结构化信息。

需要抽取：

1. 公司基础信息
2. 产品信息
3. 功能信息
4. 价格信息
5. 用户群体
6. 商业模式
7. 技术能力
8. 集成能力
9. 安全合规
10. 用户反馈
11. 增长动态
12. 风险信息
13. 最新动态

### 输出

```json
{
  "competitor_profile": {
    "name": "Example Product",
    "company": "Example Inc.",
    "website": "https://example.com",
    "positioning": {
      "summary": "AI productivity platform for teams",
      "evidence_ids": ["ev_001"]
    },
    "features": [
      {
        "name": "AI writing assistant",
        "description": "Helps users generate and edit documents",
        "maturity": "high",
        "evidence_ids": ["ev_002", "ev_003"]
      }
    ],
    "pricing": [
      {
        "plan_name": "Pro",
        "price": "$20/user/month",
        "billing_cycle": "monthly",
        "evidence_ids": ["ev_004"]
      }
    ]
  }
}
```

---

## 8.9 Evidence Builder Agent：证据链构建 Agent

### 职责

为系统中所有结构化信息和分析结论建立证据链。

每条证据需要包含：

1. evidence_id
2. 原始 URL
3. 文档 ID
4. chunk ID
5. 原文片段
6. 摘要
7. 来源类型
8. 来源可信度
9. 采集时间
10. 是否为一手来源
11. 是否可能过期
12. 支持的结论 ID

### 输出

```json
{
  "evidence": {
    "evidence_id": "ev_001",
    "url": "https://example.com/pricing",
    "source_type": "official_pricing_page",
    "quote": "The Pro plan starts at $20 per user per month.",
    "summary": "Official pricing page states Pro plan price.",
    "retrieved_at": "2026-05-15T10:10:00Z",
    "credibility_score": 0.95,
    "freshness_score": 0.9,
    "supports_claims": ["claim_001"]
  }
}
```

---

# 9. 分析类 Agent 设计

---

## 9.1 Product Positioning Agent：产品定位分析 Agent

分析每个竞品：

1. 目标用户是谁
2. 核心使用场景是什么
3. 价值主张是什么
4. 主要卖点是什么
5. 和其他竞品的定位差异
6. 是平台型、工具型、插件型还是服务型产品
7. 是 ToB、ToC 还是开发者工具

输出：

```json
{
  "positioning_analysis": [
    {
      "competitor": "Notion AI",
      "target_users": ["knowledge workers", "teams", "students"],
      "core_value": "AI-powered workspace",
      "differentiation": "Combines docs, databases, wiki and AI assistant",
      "confidence": 0.87,
      "evidence_ids": ["ev_001", "ev_002"]
    }
  ]
}
```

---

## 9.2 Feature Matrix Agent：功能矩阵分析 Agent

### 职责

构建横向功能矩阵。

功能维度包括：

1. 核心功能
2. AI 功能
3. 协作功能
4. 搜索功能
5. 自动化能力
6. API 能力
7. 权限管理
8. 企业安全
9. 数据导入导出
10. 第三方集成
11. 移动端能力
12. 多语言能力
13. 私有化部署
14. 插件生态
15. 模板生态

输出：

```json
{
  "feature_matrix": {
    "features": [
      "AI writing",
      "Knowledge base",
      "Database",
      "Workflow automation",
      "API",
      "Enterprise SSO"
    ],
    "competitors": [
      {
        "name": "Notion AI",
        "values": {
          "AI writing": {
            "support": true,
            "maturity": "high",
            "evidence_ids": ["ev_001"]
          },
          "Workflow automation": {
            "support": true,
            "maturity": "medium",
            "evidence_ids": ["ev_002"]
          }
        }
      }
    ]
  }
}
```

---

## 9.3 Pricing Analysis Agent：价格策略分析 Agent

分析：

1. 免费版能力
2. 付费版价格
3. 企业版是否定制报价
4. 计费方式
5. AI 功能是否单独收费
6. 是否按用户数收费
7. 是否按调用量收费
8. 是否存在隐藏成本
9. 和竞品的价格差异
10. 适合哪类客户

输出：

```json
{
  "pricing_analysis": {
    "summary": "Notion AI uses per-seat pricing while some competitors bundle AI into premium plans.",
    "pricing_table": [
      {
        "competitor": "Notion AI",
        "free_plan": true,
        "paid_starting_price": "$x/user/month",
        "enterprise_plan": true,
        "ai_pricing_model": "add-on",
        "evidence_ids": ["ev_001"]
      }
    ],
    "insights": [
      {
        "claim": "AI add-on pricing may increase adoption friction for small teams.",
        "confidence": 0.72,
        "evidence_ids": ["ev_002", "ev_003"]
      }
    ]
  }
}
```

---

## 9.4 User Voice Agent：用户反馈分析 Agent

### 职责

分析用户评论、社区讨论、产品评价。

来源包括：

1. G2
2. Capterra
3. Product Hunt
4. Reddit
5. X / Twitter
6. App Store
7. Chrome Store
8. GitHub Issues
9. 知乎
10. 小红书
11. B 站评论
12. 用户博客

分析内容：

1. 高频好评点
2. 高频差评点
3. 用户痛点
4. 用户需求
5. 用户流失原因
6. 竞品替换原因
7. 情绪倾向
8. 用户画像

输出：

```json
{
  "user_voice_summary": [
    {
      "competitor": "Example Product",
      "pros": [
        {
          "theme": "easy to use",
          "frequency": 28,
          "evidence_ids": ["ev_001", "ev_002"]
        }
      ],
      "cons": [
        {
          "theme": "pricing is expensive",
          "frequency": 15,
          "evidence_ids": ["ev_003"]
        }
      ],
      "sentiment_score": 0.68
    }
  ]
}
```

---

## 9.5 Technology Intelligence Agent：技术情报分析 Agent

### 职责

分析竞品背后的技术能力。

信息来源：

1. 技术博客
2. API 文档
3. SDK 文档
4. GitHub 仓库
5. 招聘 JD
6. 专利
7. 论文
8. 工程团队访谈
9. Changelog
10. 系统状态页

分析维度：

1. 是否自研模型
2. 是否调用第三方模型
3. 模型能力
4. RAG 能力
5. Agent 能力
6. 工作流自动化能力
7. 多模态能力
8. API / SDK 能力
9. 数据安全架构
10. 私有化部署能力
11. 企业集成能力
12. 基础设施成熟度

输出：

```json
{
  "technology_analysis": [
    {
      "competitor": "Example AI",
      "tech_stack_signals": [
        {
          "signal": "Provides public API and SDK",
          "confidence": 0.9,
          "evidence_ids": ["ev_001"]
        },
        {
          "signal": "Likely uses retrieval-augmented generation",
          "confidence": 0.65,
          "evidence_ids": ["ev_002"]
        }
      ],
      "technical_maturity": "medium-high"
    }
  ]
}
```

---

## 9.6 Go-To-Market Agent：市场与增长策略 Agent

分析：

1. 产品进入市场的方式
2. 定价策略
3. 免费试用策略
4. 开发者生态
5. 渠道策略
6. 内容营销
7. 合作伙伴
8. 企业客户案例
9. 社区运营
10. 国际化策略
11. 大客户销售策略

输出：

```json
{
  "gtm_analysis": [
    {
      "competitor": "Example",
      "strategy": "Product-led growth with enterprise upsell",
      "signals": [
        "free tier",
        "template community",
        "enterprise case studies"
      ],
      "confidence": 0.8,
      "evidence_ids": ["ev_001", "ev_002"]
    }
  ]
}
```

---

## 9.7 SWOT Agent：SWOT 分析 Agent

为每个竞品生成：

1. Strengths
2. Weaknesses
3. Opportunities
4. Threats

每个条目必须绑定 evidence_ids。

输出：

```json
{
  "swot": {
    "Notion AI": {
      "strengths": [
        {
          "point": "Strong workspace integration",
          "evidence_ids": ["ev_001"],
          "confidence": 0.86
        }
      ],
      "weaknesses": [],
      "opportunities": [],
      "threats": []
    }
  }
}
```

---

## 9.8 Strategic Insight Agent：战略洞察 Agent

这是高级创新 Agent，不只是总结事实，而是生成战略判断。

需要输出：

1. 市场空白点
2. 用户未被满足的需求
3. 竞品防御壁垒
4. 可能的技术突破口
5. 产品差异化建议
6. 新产品切入点
7. 定价建议
8. MVP 建议
9. 风险规避建议
10. 未来 6-12 个月趋势判断

要求：

1. 每个战略判断必须说明依据。
2. 区分事实、推断和建议。
3. 每个建议需要置信度。
4. 高风险推断必须标记。

输出：

```json
{
  "strategic_insights": [
    {
      "type": "opportunity",
      "claim": "There is an opportunity for a privacy-first AI knowledge base for regulated industries.",
      "basis": "Several competitors lack clear private deployment messaging while enterprise security concerns appear frequently in reviews.",
      "evidence_ids": ["ev_001", "ev_002", "ev_003"],
      "confidence": 0.74,
      "risk_level": "medium"
    }
  ]
}
```

---

# 10. 审查类 Agent 设计

---

## 10.1 Fact Check Agent：事实核查 Agent

### 职责

检查所有事实性陈述是否有证据支持。

检查项：

1. 公司名称是否正确
2. 产品名称是否正确
3. 价格是否正确
4. 功能是否真实存在
5. 时间是否准确
6. 是否引用过期信息
7. 是否混淆不同产品
8. 是否有大模型幻觉

输出：

```json
{
  "fact_check_result": {
    "passed": false,
    "issues": [
      {
        "claim_id": "claim_001",
        "issue_type": "missing_evidence",
        "message": "Claim has no supporting evidence.",
        "severity": "high"
      }
    ]
  }
}
```

---

## 10.2 Citation Check Agent：引用校验 Agent

### 职责

检查所有引用是否真实支持对应结论。

检查项：

1. 引用 URL 是否存在
2. 引用内容是否与结论一致
3. 是否过度解读
4. 是否张冠李戴
5. 是否引用低可信来源支撑强结论
6. 是否需要更多证据

输出：

```json
{
  "citation_check": {
    "claim_id": "claim_001",
    "status": "weak_support",
    "reason": "Evidence only mentions AI assistant but does not prove enterprise-grade capability.",
    "recommended_action": "downgrade confidence or add more evidence"
  }
}
```

---

## 10.3 Consistency Check Agent：一致性检查 Agent

### 职责

检查报告内部是否自相矛盾。

例如：

1. 前文说某产品没有 API，后文却说其 API 生态成熟。
2. 价格表和文字描述不一致。
3. 功能矩阵和 SWOT 中的结论不一致。
4. 用户反馈和战略建议矛盾。

输出：

```json
{
  "consistency_issues": [
    {
      "type": "pricing_conflict",
      "location_a": "pricing_table",
      "location_b": "summary_section",
      "message": "Pricing value differs between table and summary."
    }
  ]
}
```

---

## 10.4 Bias Detection Agent：偏见检测 Agent

### 职责

检测分析是否存在：

1. 过度偏向某个竞品
2. 只引用官方资料导致过度正面
3. 只引用用户评论导致过度负面
4. 忽略区域差异
5. 忽略客户规模差异
6. 将推测当作事实

输出：

```json
{
  "bias_report": [
    {
      "bias_type": "source_bias",
      "description": "Most evidence comes from official websites.",
      "impact": "May overestimate product maturity.",
      "recommendation": "Collect more user reviews and third-party sources."
    }
  ]
}
```

---

## 10.5 Red Team Agent：红队挑战 Agent

### 职责

模拟严苛评审者，对报告提出挑战。

需要从以下角度攻击报告：

1. 证据是否充分？
2. 有没有遗漏重要竞品？
3. 结论是否太武断？
4. 是否存在过期信息？
5. 是否有替代解释？
6. 战略建议是否可执行？
7. 是否忽略商业现实？
8. 是否忽略技术门槛？

输出：

```json
{
  "red_team_challenges": [
    {
      "challenge": "The report claims Product A has weak enterprise capability, but only uses user reviews as evidence.",
      "severity": "medium",
      "suggested_fix": "Add official security documentation and enterprise customer evidence."
    }
  ]
}
```

---

## 10.6 Final Quality Gate Agent：最终质检 Agent

### 职责

决定报告是否可以交付。

检查：

1. 所有核心结论是否有证据
2. 所有引用是否有效
3. 报告是否覆盖用户需求
4. 是否存在高风险幻觉
5. 是否有未解决的红队问题
6. 是否满足输出格式要求

输出：

```json
{
  "quality_gate": {
    "status": "pass_with_warnings",
    "score": 86,
    "warnings": [
      "Some technology maturity conclusions are inference-based."
    ],
    "required_fixes": []
  }
}
```

---

# 11. 撰写类 Agent 设计

---

## 11.1 Report Writer Agent：报告撰写 Agent

### 职责

根据结构化分析结果生成完整报告。

报告结构至少包括：

1. 标题
2. 执行摘要
3. 分析范围
4. 竞品列表
5. 信息来源说明
6. 市场背景
7. 竞品定位对比
8. 功能矩阵
9. 价格策略分析
10. 用户反馈分析
11. 技术能力分析
12. 商业模式分析
13. SWOT 分析
14. 差异化机会
15. 战略建议
16. 风险提示
17. 结论
18. 引用来源附录
19. Agent 执行日志摘要

---

## 11.2 Executive Summary Agent：高管摘要 Agent

输出适合老板快速阅读的一页摘要：

1. 这个市场的核心结论是什么？
2. 最强竞品是谁？
3. 最大机会在哪里？
4. 最大风险是什么？
5. 我们应该怎么做？
6. 哪些事情需要立即行动？

---

## 11.3 Slide Outline Agent：PPT 大纲 Agent

将报告转换为 PPT 大纲。

每页包括：

1. 页面标题
2. 核心观点
3. 图表建议
4. 页面讲稿
5. 证据来源

示例：

```json
{
  "slides": [
    {
      "page": 1,
      "title": "AI 办公协作市场竞争格局",
      "key_message": "市场正在从单点 AI 助手走向全流程工作空间智能化。",
      "visual": "2x2 positioning map",
      "speaker_notes": "本页介绍整体市场背景...",
      "evidence_ids": ["ev_001", "ev_002"]
    }
  ]
}
```

---

# 12. 竞品知识 Schema 设计

系统必须定义统一的竞品知识 Schema。

## 12.1 Competitor Schema

```json
{
  "competitor_id": "string",
  "name": "string",
  "aliases": ["string"],
  "company_name": "string",
  "website": "string",
  "founded_year": "number|null",
  "headquarters": "string|null",
  "company_stage": "startup|growth|public|enterprise|open_source|unknown",
  "product_category": "string",
  "target_users": ["string"],
  "target_industries": ["string"],
  "regions": ["string"],
  "business_model": ["subscription", "usage_based", "freemium", "enterprise", "open_source", "marketplace"],
  "positioning": {
    "short_summary": "string",
    "long_summary": "string",
    "evidence_ids": ["string"]
  },
  "features": [
    {
      "feature_id": "string",
      "name": "string",
      "category": "string",
      "description": "string",
      "support_status": "yes|partial|no|unknown",
      "maturity": "low|medium|high|unknown",
      "evidence_ids": ["string"]
    }
  ],
  "pricing": [
    {
      "plan_name": "string",
      "price": "string",
      "currency": "string|null",
      "billing_cycle": "monthly|yearly|usage|custom|unknown",
      "target_segment": "individual|team|enterprise|developer|unknown",
      "included_features": ["string"],
      "limitations": ["string"],
      "evidence_ids": ["string"]
    }
  ],
  "integrations": [
    {
      "name": "string",
      "type": "api|plugin|native|zapier|browser_extension|unknown",
      "evidence_ids": ["string"]
    }
  ],
  "security_compliance": [
    {
      "item": "SOC2|GDPR|HIPAA|SSO|SAML|SCIM|data_residency|private_deployment|unknown",
      "status": "yes|partial|unknown",
      "evidence_ids": ["string"]
    }
  ],
  "user_feedback": {
    "pros": [
      {
        "theme": "string",
        "summary": "string",
        "frequency": "number|null",
        "sentiment": "positive|neutral|negative",
        "evidence_ids": ["string"]
      }
    ],
    "cons": [
      {
        "theme": "string",
        "summary": "string",
        "frequency": "number|null",
        "sentiment": "positive|neutral|negative",
        "evidence_ids": ["string"]
      }
    ]
  },
  "market_signals": [
    {
      "signal_type": "funding|hiring|partnership|launch|customer_case|community_growth|media_coverage",
      "description": "string",
      "date": "string|null",
      "evidence_ids": ["string"]
    }
  ],
  "technical_signals": [
    {
      "signal_type": "api|model|rag|agent|workflow|sdk|open_source|infrastructure|security",
      "description": "string",
      "confidence": "number",
      "evidence_ids": ["string"]
    }
  ],
  "swot": {
    "strengths": [],
    "weaknesses": [],
    "opportunities": [],
    "threats": []
  },
  "last_updated": "string"
}
```

---

## 12.2 Evidence Schema

```json
{
  "evidence_id": "string",
  "source_url": "string",
  "source_title": "string",
  "source_type": "official|third_party|review|news|social|github|docs|pricing|job|paper|unknown",
  "publisher": "string|null",
  "published_at": "string|null",
  "retrieved_at": "string",
  "doc_id": "string",
  "chunk_id": "string",
  "quote": "string",
  "summary": "string",
  "credibility_score": "number",
  "freshness_score": "number",
  "is_primary_source": "boolean",
  "is_potentially_outdated": "boolean",
  "supports_claim_ids": ["string"]
}
```

---

## 12.3 Claim Schema

```json
{
  "claim_id": "string",
  "claim_text": "string",
  "claim_type": "fact|inference|recommendation|risk|opportunity",
  "subject": "string",
  "confidence": "number",
  "risk_level": "low|medium|high",
  "evidence_ids": ["string"],
  "created_by_agent": "string",
  "review_status": "pending|approved|rejected|needs_revision",
  "review_comments": ["string"]
}
```

---

## 12.4 Agent Run Schema

```json
{
  "run_id": "string",
  "task_id": "string",
  "agent_name": "string",
  "status": "pending|running|success|failed|skipped",
  "input": {},
  "output": {},
  "tool_calls": [
    {
      "tool_name": "string",
      "input": {},
      "output_summary": "string",
      "started_at": "string",
      "ended_at": "string",
      "status": "success|failed"
    }
  ],
  "model": "string",
  "token_usage": {
    "input_tokens": "number",
    "output_tokens": "number"
  },
  "cost_estimate": "number|null",
  "started_at": "string",
  "ended_at": "string",
  "duration_ms": "number",
  "error": "string|null"
}
```

---

# 13. DAG 任务流设计

## 13.1 基础 DAG

```text
User Query
  ↓
Intent Parsing
  ↓
Task Planning
  ↓
Competitor Discovery
  ↓
Source Planning
  ↓
Parallel Collection
  ├── Official Website Collection
  ├── Pricing Collection
  ├── Docs Collection
  ├── Review Collection
  ├── News Collection
  ├── Social Collection
  ├── GitHub Collection
  └── Hiring Signal Collection
  ↓
Document Cleaning
  ↓
Chunking & Embedding
  ↓
Schema Extraction
  ↓
Evidence Building
  ↓
Parallel Analysis
  ├── Product Positioning Analysis
  ├── Feature Matrix Analysis
  ├── Pricing Analysis
  ├── User Voice Analysis
  ├── Technology Analysis
  ├── GTM Analysis
  └── SWOT Analysis
  ↓
Strategic Insight Generation
  ↓
Quality Review
  ├── Fact Check
  ├── Citation Check
  ├── Consistency Check
  ├── Bias Check
  └── Red Team Review
  ↓
Revision Loop
  ↓
Final Report Writing
  ↓
Final Quality Gate
  ↓
Export
```

---

## 13.2 反馈闭环

当审查 Agent 发现问题时，系统不能直接输出报告，而是进入修正流程：

```text
Review Issue Detected
  ↓
Issue Classifier
  ↓
Route to Responsible Agent
  ├── Missing Evidence → Source Planning Agent
  ├── Weak Citation → Evidence Builder Agent
  ├── Contradiction → Analysis Agent
  ├── Poor Writing → Report Writer Agent
  └── Missing Competitor → Competitor Discovery Agent
  ↓
Re-run Partial DAG
  ↓
Re-check
  ↓
Final Output
```

---

# 14. 前端功能要求

需要实现一个 Web 前端，建议使用 React / Next.js。

## 14.1 首页

功能：

1. 输入竞品分析任务。
2. 选择分析模式：

   * 快速分析
   * 深度分析
   * 投资视角
   * 产品经理视角
   * 技术视角
   * 市场营销视角
3. 选择输出格式：

   * Markdown
   * HTML
   * PDF
   * JSON
   * PPT 大纲
4. 设置竞品数量上限。
5. 设置时间范围。
6. 设置语言。
7. 是否启用深度审查。
8. 是否启用定期监控。

---

## 14.2 任务运行页面

需要展示：

1. DAG 图
2. 当前运行节点
3. 已完成节点
4. 失败节点
5. 等待节点
6. 每个 Agent 的状态
7. 运行时间
8. Token 消耗
9. 工具调用记录
10. 中间产物预览

建议使用图形化 DAG：

```text
[Intent] → [Planner] → [Discovery] → [Source Planning]
                                      ↓
           [Official] [Pricing] [Reviews] [Docs] [News]
                                      ↓
                            [Schema Extraction]
                                      ↓
                              [Analysis Agents]
                                      ↓
                              [QA Agents]
                                      ↓
                               [Report Writer]
```

---

## 14.3 竞品知识库页面

展示结构化竞品信息：

1. 公司基础信息
2. 产品定位
3. 功能列表
4. 价格表
5. 用户反馈
6. 技术信号
7. 市场信号
8. SWOT
9. 证据来源
10. 更新时间

---

## 14.4 报告页面

展示最终报告。

要求：

1. 支持 Markdown 渲染。
2. 支持引用点击跳转。
3. 每个结论旁边显示证据数量。
4. 鼠标悬浮显示证据摘要。
5. 点击证据可查看原文片段。
6. 支持一键导出。
7. 支持重新运行某个章节。
8. 支持人工编辑报告。
9. 支持保存版本。

---

## 14.5 可观测性页面

展示：

1. 每个 Agent 的运行日志
2. 输入输出
3. 工具调用
4. Token 使用
5. 模型成本
6. 失败率
7. 平均耗时
8. 证据覆盖率
9. 引用通过率
10. 质量评分趋势

---

# 15. 后端功能要求

建议使用 FastAPI / Node.js / NestJS 均可。推荐 FastAPI。

## 15.1 核心 API

### 创建分析任务

```http
POST /api/projects
```

请求：

```json
{
  "query": "分析 AI 知识库产品的竞品格局",
  "mode": "deep",
  "language": "zh-CN",
  "output_formats": ["markdown", "html", "json"],
  "max_competitors": 8,
  "enable_deep_review": true
}
```

返回：

```json
{
  "project_id": "proj_001",
  "status": "created"
}
```

---

### 启动任务

```http
POST /api/projects/{project_id}/run
```

---

### 获取任务状态

```http
GET /api/projects/{project_id}/status
```

---

### 获取 DAG

```http
GET /api/projects/{project_id}/dag
```

---

### 获取 Agent 日志

```http
GET /api/projects/{project_id}/agent-runs
```

---

### 获取竞品结构化数据

```http
GET /api/projects/{project_id}/competitors
```

---

### 获取证据列表

```http
GET /api/projects/{project_id}/evidence
```

---

### 获取最终报告

```http
GET /api/projects/{project_id}/report
```

---

### 导出报告

```http
POST /api/projects/{project_id}/export
```

---

## 15.2 Agent 执行接口

每个 Agent 需要统一接口。

```python
class BaseAgent:
    name: str
    description: str
    input_schema: dict
    output_schema: dict

    async def run(self, input_data: dict, context: AgentContext) -> dict:
        pass
```

AgentContext 需要包含：

```python
class AgentContext:
    project_id: str
    task_id: str
    memory: MemoryStore
    vector_store: VectorStore
    db: Database
    tools: ToolRegistry
    logger: AgentLogger
    config: RuntimeConfig
```

---

# 16. 数据库设计

建议使用：

1. PostgreSQL：存储项目、任务、Agent 日志、结构化竞品数据。
2. Qdrant / Milvus / Weaviate / pgvector：存储文档向量。
3. Redis：任务队列、缓存、锁。
4. MinIO / S3：存储网页快照、截图、导出文件。

---

## 16.1 表结构建议

### projects

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  query TEXT NOT NULL,
  mode TEXT NOT NULL,
  language TEXT DEFAULT 'zh-CN',
  status TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

### tasks

```sql
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  status TEXT NOT NULL,
  depends_on JSONB,
  input JSONB,
  output JSONB,
  error TEXT,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL
);
```

### documents

```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  url TEXT,
  title TEXT,
  source_type TEXT,
  content_hash TEXT,
  content TEXT,
  retrieved_at TIMESTAMP,
  metadata JSONB
);
```

### chunks

```sql
CREATE TABLE chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  text TEXT NOT NULL,
  section_title TEXT,
  start_char INT,
  end_char INT,
  metadata JSONB
);
```

### competitors

```sql
CREATE TABLE competitors (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  website TEXT,
  profile JSONB,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

### evidence

```sql
CREATE TABLE evidence (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  document_id TEXT,
  chunk_id TEXT,
  source_url TEXT,
  quote TEXT,
  summary TEXT,
  credibility_score FLOAT,
  freshness_score FLOAT,
  metadata JSONB,
  created_at TIMESTAMP NOT NULL
);
```

### claims

```sql
CREATE TABLE claims (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  claim_text TEXT NOT NULL,
  claim_type TEXT,
  confidence FLOAT,
  risk_level TEXT,
  evidence_ids JSONB,
  created_by_agent TEXT,
  review_status TEXT,
  metadata JSONB,
  created_at TIMESTAMP NOT NULL
);
```

### agent_runs

```sql
CREATE TABLE agent_runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  status TEXT NOT NULL,
  input JSONB,
  output JSONB,
  tool_calls JSONB,
  model TEXT,
  token_usage JSONB,
  cost_estimate FLOAT,
  error TEXT,
  started_at TIMESTAMP,
  ended_at TIMESTAMP
);
```

---

# 17. 工具系统要求

需要实现 Tool Registry，所有 Agent 通过统一工具接口调用工具。

## 17.1 工具接口

```python
class BaseTool:
    name: str
    description: str

    async def call(self, input_data: dict) -> dict:
        pass
```

## 17.2 必需工具

### WebSearchTool

用于搜索公开网页。

### WebCrawlerTool

用于抓取网页正文。

### BrowserRenderTool

用于动态网页渲染和截图。

### DocumentParserTool

用于解析 PDF、HTML、Markdown、DOCX。

### VectorSearchTool

用于从知识库中检索相关证据。

### DatabaseTool

用于读写结构化数据。

### CitationTool

用于管理 claim 和 evidence 的映射关系。

### ReportRenderTool

用于导出 Markdown、HTML、PDF。

### ChartTool

用于生成竞品矩阵、雷达图、2x2 定位图。

### GitHubSignalTool

用于分析开源项目的 Star、Fork、Issue、Release、Commit 活跃度。

### PricingTableExtractorTool

专门抽取价格页中的价格表。

### ReviewMiningTool

专门分析用户评论主题和情绪。

---

# 18. LLM 调用策略

系统需要支持多模型配置。

## 18.1 模型分工

建议：

1. 小模型用于简单分类、清洗、摘要。
2. 中等模型用于结构化抽取。
3. 强模型用于战略分析、报告撰写、红队审查。
4. Embedding 模型用于向量检索。
5. Reranker 模型用于证据重排。

## 18.2 Prompt 管理

需要实现 Prompt Template 管理系统。

每个 Agent 的 Prompt 需要包含：

1. 角色说明
2. 任务目标
3. 输入格式
4. 输出 JSON Schema
5. 质量要求
6. 禁止事项
7. 示例
8. 自检步骤

## 18.3 防幻觉要求

所有 Agent 必须遵守：

1. 不得编造事实。
2. 没有证据时输出 unknown。
3. 推断必须标记为 inference。
4. 建议必须标记为 recommendation。
5. 强事实结论必须绑定 evidence_ids。
6. 对不确定内容必须给出 confidence。

---

# 19. 创新功能要求

为了让系统更复杂、更创新，建议加入以下高级功能。

---

## 19.1 Agent Debate 机制

对于重要战略结论，系统启动多个 Agent 辩论：

1. Pro Agent：支持该结论。
2. Con Agent：反驳该结论。
3. Judge Agent：综合判断。

输出：

```json
{
  "debate": {
    "claim": "Product A has the strongest enterprise moat.",
    "pro_arguments": [],
    "con_arguments": [],
    "judge_result": {
      "final_position": "partially_supported",
      "confidence": 0.68
    }
  }
}
```

---

## 19.2 Market Map 自动生成

自动生成市场地图：

1. 横轴：产品复杂度
2. 纵轴：企业级能力
3. 气泡大小：市场热度
4. 颜色：商业模式

输出为：

1. JSON 图表数据
2. 前端可视化
3. 报告中的图表说明

---

## 19.3 竞品雷达图

为每个竞品计算评分：

1. 功能完整度
2. 易用性
3. 企业能力
4. AI 能力
5. 生态能力
6. 价格竞争力
7. 技术成熟度
8. 用户满意度

评分必须有依据，不能凭空打分。

---

## 19.4 Weak Signal Detection 弱信号检测

从招聘、博客、GitHub、Changelog 中发现早期信号：

1. 是否正在研发新功能？
2. 是否加大 AI 投入？
3. 是否进入新行业？
4. 是否扩张企业销售团队？
5. 是否可能推出 API / SDK？
6. 是否可能私有化部署？

---

## 19.5 Competitive War Room 竞争作战室

对重点竞品生成作战建议：

1. 我方应该避开哪些正面竞争？
2. 哪些用户群体可以优先切入？
3. 哪些功能是必须补齐的？
4. 哪些功能可以差异化？
5. 哪些营销叙事可以反制？
6. 哪些价格策略可以攻击竞品？

---

## 19.6 Continuous Monitoring 持续监控

支持用户设置：

1. 每日监控
2. 每周报告
3. 重大变化告警
4. 价格变动告警
5. 新功能发布告警
6. 新融资告警
7. 用户差评激增告警

---

## 19.7 Evidence Heatmap 证据热力图

展示不同结论的证据强度：

1. 绿色：证据充分
2. 黄色：证据一般
3. 红色：证据不足
4. 灰色：无证据或未知

---

## 19.8 Confidence-aware Report 置信度感知报告

报告中每个核心判断旁显示：

1. 置信度
2. 证据数量
3. 证据类型
4. 风险等级
5. 是否为推断

示例：

```text
结论：A 产品在企业级权限管理方面强于 B 产品。
置信度：0.82
证据数量：5
证据类型：官方文档 2 条、用户评价 2 条、第三方评测 1 条
风险等级：低
```

---

## 19.9 Human-in-the-loop 人工介入机制

用户可以在以下环节介入：

1. 确认竞品列表。
2. 删除不相关信息源。
3. 手动添加私有资料。
4. 修改分析维度。
5. 对 Agent 结论打分。
6. 要求重跑某个 Agent。
7. 锁定某条结论不再修改。
8. 人工批准最终报告。

---

# 20. 输出报告格式要求

最终报告需要支持以下格式。

## 20.1 Markdown 报告

包含完整引用。

```markdown
# AI 办公协作竞品分析报告

## 执行摘要

...

## 核心结论

1. xxx [证据: ev_001, ev_002]

## 竞品功能矩阵

| 功能 | A | B | C |
|---|---|---|---|

## 引用来源

- ev_001: https://...
```

---

## 20.2 JSON 报告

用于 API 或下游系统消费。

```json
{
  "project_id": "proj_001",
  "summary": "...",
  "competitors": [],
  "feature_matrix": {},
  "pricing_analysis": {},
  "strategic_insights": [],
  "claims": [],
  "evidence": []
}
```

---

## 20.3 HTML 报告

要求：

1. 支持目录导航。
2. 支持引用点击。
3. 支持图表。
4. 支持高亮证据。
5. 支持导出 PDF。

---

## 20.4 PPT 大纲

要求：

1. 10-20 页。
2. 每页一个核心观点。
3. 包含讲稿。
4. 包含图表建议。
5. 包含证据 ID。

---

# 21. 质量评分体系

系统需要为每份报告生成质量评分。

## 21.1 总分 100 分

评分维度：

1. 信息覆盖度：20 分
2. 证据充分性：20 分
3. 引用准确性：15 分
4. 分析深度：15 分
5. 结构化程度：10 分
6. 逻辑一致性：10 分
7. 可读性：5 分
8. 新颖洞察：5 分

输出：

```json
{
  "quality_score": {
    "total": 87,
    "coverage": 18,
    "evidence_strength": 17,
    "citation_accuracy": 14,
    "analysis_depth": 13,
    "structure": 9,
    "consistency": 9,
    "readability": 4,
    "novelty": 4
  }
}
```

---

# 22. 非功能性要求

## 22.1 性能要求

1. 快速模式：5-10 分钟内完成基础报告。
2. 深度模式：允许更长时间，但需要展示实时进度。
3. 支持至少 10 个竞品并行分析。
4. 支持任务断点续跑。
5. 支持失败节点单独重跑。

---

## 22.2 可扩展性要求

1. Agent 可以插件化添加。
2. Tool 可以插件化添加。
3. Schema 可以配置扩展。
4. 支持多语言。
5. 支持多模型。
6. 支持不同报告模板。

---

## 22.3 安全与合规要求

1. 只采集公开可访问的信息。
2. 不绕过登录、验证码、付费墙或访问控制。
3. 支持 robots.txt 检查。
4. 支持速率限制。
5. 支持用户数据隔离。
6. 支持 API Key 加密存储。
7. 支持操作审计日志。
8. 支持删除项目数据。
9. 不在报告中泄露用户私有输入。
10. 对不确定信息做明确标注。

---

## 22.4 可观测性要求

必须记录：

1. 每个任务节点状态。
2. 每个 Agent 输入输出。
3. 每次工具调用。
4. 每次 LLM 调用。
5. Token 使用量。
6. 成本估算。
7. 错误日志。
8. 重试记录。
9. 证据覆盖率。
10. 报告质量评分。

---

# 23. 推荐技术栈

## 23.1 前端

1. Next.js
2. React
3. TypeScript
4. Tailwind CSS
5. Shadcn UI
6. React Flow：展示 DAG
7. Recharts / ECharts：图表
8. Zustand / Redux：状态管理

## 23.2 后端

1. Python FastAPI
2. Pydantic
3. SQLAlchemy
4. Celery / Dramatiq / Temporal
5. Redis
6. PostgreSQL
7. Qdrant / pgvector
8. Playwright
9. BeautifulSoup / Trafilatura
10. LangGraph / 自研 DAG Orchestrator

## 23.3 AI 层

1. OpenAI / Claude / Gemini / Qwen / DeepSeek 可配置
2. Embedding 模型
3. Reranker 模型
4. Prompt Template Manager
5. Tool Calling
6. JSON Schema Validation

---

# 24. 项目目录结构建议

```text
competescope-ai/
  frontend/
    app/
    components/
    components/dag/
    components/report/
    components/evidence/
    components/agent-trace/
    lib/
    stores/
    types/
  backend/
    app/
      main.py
      config.py
      api/
        projects.py
        tasks.py
        agents.py
        reports.py
        evidence.py
      agents/
        base.py
        intent_agent.py
        planner_agent.py
        competitor_discovery_agent.py
        source_planning_agent.py
        web_search_agent.py
        web_crawler_agent.py
        document_cleaner_agent.py
        schema_extraction_agent.py
        evidence_builder_agent.py
        product_positioning_agent.py
        feature_matrix_agent.py
        pricing_analysis_agent.py
        user_voice_agent.py
        technology_agent.py
        gtm_agent.py
        swot_agent.py
        strategic_insight_agent.py
        fact_check_agent.py
        citation_check_agent.py
        consistency_check_agent.py
        bias_detection_agent.py
        red_team_agent.py
        report_writer_agent.py
        quality_gate_agent.py
      orchestrator/
        dag.py
        executor.py
        scheduler.py
        retry.py
      tools/
        base.py
        web_search.py
        crawler.py
        browser.py
        document_parser.py
        vector_search.py
        database.py
        citation.py
        report_renderer.py
        chart.py
      schemas/
        competitor.py
        evidence.py
        claim.py
        task.py
        report.py
      services/
        llm_service.py
        embedding_service.py
        vector_store.py
        storage_service.py
        cost_tracker.py
        observability.py
      db/
        models.py
        migrations/
      prompts/
        intent_agent.md
        planner_agent.md
        extraction_agent.md
        report_writer_agent.md
        fact_check_agent.md
      tests/
  docker-compose.yml
  README.md
```

---

# 25. MVP 版本要求

如果先做 MVP，至少完成以下功能。

## 25.1 MVP 必须实现

1. 用户输入竞品分析主题。
2. Planner Agent 拆解任务。
3. 至少支持 5 个 Agent：

   * Intent Agent
   * Web Search Agent
   * Schema Extraction Agent
   * Analysis Agent
   * Report Writer Agent
4. 支持网页信息采集。
5. 支持结构化竞品 Schema。
6. 支持证据 ID。
7. 支持 Markdown 报告。
8. 支持任务状态展示。
9. 支持基础日志。
10. 支持引用来源列表。

---

## 25.2 MVP 后增强

第二阶段加入：

1. DAG 可视化
2. 多 Agent 并行
3. Fact Check Agent
4. Citation Check Agent
5. 向量数据库
6. HTML 报告
7. 竞品功能矩阵
8. 价格分析
9. 用户反馈分析
10. 可观测性 Dashboard

---

## 25.3 高级版本

第三阶段加入：

1. Red Team Agent
2. Agent Debate
3. 持续监控
4. 市场地图
5. 雷达图
6. 定期报告
7. 人工介入
8. 版本管理
9. 多项目知识库
10. 企业级权限系统

---

# 26. 验收标准

系统完成后，需要满足以下验收标准。

## 26.1 功能验收

1. 用户可以创建一个竞品分析项目。
2. 系统可以自动识别或发现竞品。
3. 系统可以采集公开信息。
4. 系统可以生成结构化竞品数据。
5. 系统可以生成至少一份 Markdown 报告。
6. 报告中的核心结论带有 evidence_ids。
7. 用户可以查看每条 evidence 的来源 URL 和原文片段。
8. 用户可以查看每个 Agent 的运行状态。
9. 用户可以看到 DAG 任务流。
10. 用户可以导出报告。

---

## 26.2 质量验收

1. 报告核心结论中，至少 80% 有证据支持。
2. 每个竞品至少有 3 类信息源。
3. 每个竞品至少覆盖产品定位、功能、价格、用户反馈四类信息。
4. 不允许出现无证据的强事实断言。
5. 引用必须与结论相关。
6. 对不确定信息必须标记 confidence。
7. 失败任务必须有错误日志。
8. Agent 输出必须符合 JSON Schema。

---

# 27. 示例用户任务

系统需要能处理以下任务。

## 示例 1

```text
请分析 AI 办公协作领域的竞品，包括 Notion AI、ClickUp AI、Coda AI、飞书、钉钉，并生成产品经理视角的深度竞品报告。
```

## 示例 2

```text
我想做一个面向企业内部知识库的 AI Agent 产品，请帮我分析国内外竞品，找出差异化机会。
```

## 示例 3

```text
分析 LangChain、LlamaIndex、Dify、Flowise、CrewAI、AutoGen 在 AI Agent 开发平台领域的竞争格局，重点关注开源活跃度、商业化、技术能力和生态。
```

## 示例 4

```text
每周帮我监控 Cursor、Windsurf、GitHub Copilot、Codeium、Tabnine 的产品更新和价格变化。
```

---

# 28. 最终交付物

开发完成后需要提供：

1. 前端 Web 应用
2. 后端 API 服务
3. Agent 编排系统
4. 工具调用系统
5. 数据库 Schema
6. 竞品知识 Schema
7. Prompt 模板
8. 报告模板
9. Docker Compose 部署文件
10. README 文档
11. 示例分析项目
12. 测试用例
13. API 文档
14. 演示视频或运行截图

---

# 29. 给 AI Coding 工具的核心实现指令

可以直接复制下面这段给 AI Coding 工具：

```text
请从零实现一个名为 CompeteScope AI 的 AI 驱动竞品分析 Agent 协作系统。

系统目标：
构建一个多 Agent 协作平台，用于自动完成竞品分析。用户输入一个行业、产品方向或竞品列表后，系统需要自动进行任务规划、公开信息采集、文档清洗、结构化信息抽取、竞品分析、证据链构建、事实核查、引用校验、报告撰写和导出。

核心要求：
1. 使用前后端分离架构。
2. 前端使用 Next.js + TypeScript + Tailwind CSS + React Flow。
3. 后端使用 FastAPI + PostgreSQL + Redis + Qdrant 或 pgvector。
4. 实现 Agent 抽象基类 BaseAgent。
5. 实现 Tool 抽象基类 BaseTool。
6. 实现 DAG Orchestrator，支持任务依赖、并行执行、失败重试、节点状态追踪。
7. 实现以下 Agent：
   - IntentAgent
   - PlannerAgent
   - CompetitorDiscoveryAgent
   - SourcePlanningAgent
   - WebSearchAgent
   - WebCrawlerAgent
   - DocumentCleanerAgent
   - SchemaExtractionAgent
   - EvidenceBuilderAgent
   - ProductPositioningAgent
   - FeatureMatrixAgent
   - PricingAnalysisAgent
   - UserVoiceAgent
   - TechnologyIntelligenceAgent
   - GTMAgent
   - SWOTAgent
   - StrategicInsightAgent
   - FactCheckAgent
   - CitationCheckAgent
   - ConsistencyCheckAgent
   - BiasDetectionAgent
   - RedTeamAgent
   - ReportWriterAgent
   - QualityGateAgent
8. 实现以下工具：
   - WebSearchTool
   - WebCrawlerTool
   - BrowserRenderTool
   - DocumentParserTool
   - VectorSearchTool
   - DatabaseTool
   - CitationTool
   - ReportRenderTool
   - ChartTool
9. 所有 Agent 输出必须符合 JSON Schema。
10. 所有分析结论必须绑定 evidence_ids。
11. 每个 evidence 必须包含 source_url、quote、summary、retrieved_at、credibility_score 和 freshness_score。
12. 报告中的事实、推断、建议必须明确区分。
13. 没有证据时不能编造结论，必须输出 unknown 或 low confidence。
14. 前端需要展示：
    - 项目创建页
    - DAG 任务运行图
    - Agent 执行日志
    - 竞品知识库
    - 证据详情页
    - 最终报告页
    - 可观测性 Dashboard
15. 后端需要提供：
    - 创建项目 API
    - 启动任务 API
    - 获取任务状态 API
    - 获取 DAG API
    - 获取 Agent Run API
    - 获取竞品数据 API
    - 获取证据 API
    - 获取报告 API
    - 导出报告 API
16. 支持 Markdown、HTML、JSON 三种报告输出。
17. 实现基础质量评分，包括信息覆盖度、证据充分性、引用准确性、分析深度、逻辑一致性和可读性。
18. 实现人工介入机制，允许用户确认竞品列表、重跑某个 Agent、编辑报告内容。
19. 实现完整日志、错误处理、失败重试和任务断点续跑。
20. 所有公开信息采集必须遵守 robots.txt、速率限制和合规要求，不得绕过登录、验证码、付费墙或访问控制。

请先生成完整项目结构、数据库模型、核心 Agent 基类、Tool 基类、DAG 编排器、主要 API，然后实现 MVP 流程：用户输入 query → IntentAgent → PlannerAgent → WebSearchAgent → WebCrawlerAgent → SchemaExtractionAgent → EvidenceBuilderAgent → AnalysisAgent → ReportWriterAgent → 输出 Markdown 报告。
```

---

# 30. 建议优先级

真正开发时，不要一开始就做所有 Agent。建议按以下顺序推进：

```text
第一优先级：
用户输入 → 任务规划 → 网页采集 → 结构化抽取 → 证据链 → Markdown 报告

第二优先级：
DAG 可视化 → Agent 日志 → 引用校验 → 质量评分

第三优先级：
功能矩阵 → 价格分析 → 用户反馈分析 → 技术分析

第四优先级：
Red Team → Debate → 持续监控 → 市场地图 → 作战室
```

这个需求已经足够复杂，可以作为一个完整的 AI Agent 系统项目来开发。
