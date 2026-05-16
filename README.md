# CompeteScope AI

CompeteScope AI 是一个前后端分离的 AI 驱动竞品分析 Agent 协作系统。MVP 已实现：

- FastAPI 后端、SQLAlchemy 数据模型、PostgreSQL/Redis/Qdrant Docker 依赖
- `BaseAgent`、`BaseTool`、Tool Registry、DAG Orchestrator
- 25 节点深度 DAG：`Intent → Planner → CompetitorDiscovery → SourcePlanning → WebSearch → WebCrawler → DocumentCleaner → SchemaExtraction → EvidenceBuilder → 并行分析 Agent → QA/RedTeam → QualityGate → ReportWriter`
- 竞品发现、信息源规划、定位分析、功能矩阵、价格分析、用户声音、技术情报、GTM、SWOT、战略洞察、事实核查、引用校验、一致性检查、偏差检测和红队挑战
- 证据链、claim/evidence 绑定、Markdown/HTML/JSON 深度报告、质量评分和风险提示
- Next.js + TypeScript + Tailwind CSS + React Flow 前端页面
- 人工确认竞品、重跑任务、编辑报告的 API

## 本地运行

后端：

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000`。默认 `SIMULATIVE=True`，系统使用内置 fixture 做稳定模拟演示；在 `backend/app/config.py` 中把 `SIMULATIVE` 改为 `False` 后，系统会启用真实 API：LLM 读取 `COMPETESCOPE_LLM_API_KEY`，搜索优先读取 `COMPETESCOPE_SERPER_API_KEY` / `COMPETESCOPE_BRAVE_SEARCH_API_KEY`，未配置搜索 key 时会尝试轻量公开搜索 fallback。爬虫工具已包含 robots.txt 检查、域名级限速和访问控制边界，不绕过登录、验证码或付费墙。

LLM 接口使用 OpenAI-compatible `/chat/completions` 协议，模型名在代码中固定配置为 `gpt-4o-mini`。如需切换兼容网关，可设置 `COMPETESCOPE_LLM_BASE_URL`。

macOS 上可把 API key 写入 `~/.zshrc` 后重启终端或执行 `source ~/.zshrc`：

```bash
export COMPETESCOPE_LLM_API_KEY="your-llm-api-key"
export COMPETESCOPE_SERPER_API_KEY="your-serper-api-key"
# export COMPETESCOPE_BRAVE_SEARCH_API_KEY="your-brave-search-api-key"
```

## Docker Compose

```bash
docker compose up
```

服务：

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Qdrant: `localhost:6333`

## 关键 API

- `POST /api/projects`
- `POST /api/projects/{project_id}/run`
- `GET /api/projects/{project_id}/status`
- `GET /api/projects/{project_id}/dag`
- `GET /api/projects/{project_id}/agent-runs`
- `GET /api/projects/{project_id}/competitors`
- `GET /api/projects/{project_id}/evidence`
- `GET /api/projects/{project_id}/report`
- `POST /api/projects/{project_id}/export`
- `POST /api/projects/{project_id}/human/confirm-competitors`
- `POST /api/projects/{project_id}/tasks/{task_id}/rerun`
- `PATCH /api/projects/{project_id}/report`

## 测试

```bash
cd backend
uv run pytest
```

测试会完整验证：创建项目、运行深度 DAG、生成竞品知识库、构建 evidence、输出 Markdown/HTML/JSON 报告、QA 结果和 Agent 日志。
