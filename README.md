# CompeteScope AI

CompeteScope AI 是一个前后端分离的 AI 驱动竞品分析 Agent 协作系统。MVP 已实现：

- FastAPI 后端、SQLAlchemy 数据模型、PostgreSQL/Redis/Qdrant Docker 依赖
- `BaseAgent`、`BaseTool`、Tool Registry、DAG Orchestrator
- 24 个题目要求 Agent 注册，其中 MVP 跑通 `IntentAgent → PlannerAgent → WebSearchAgent → WebCrawlerAgent → SchemaExtractionAgent → EvidenceBuilderAgent → AnalysisAgent → ReportWriterAgent`
- 证据链、claim/evidence 绑定、Markdown/HTML/JSON 报告、质量评分
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

打开 `http://localhost:3000`。默认 `COMPETESCOPE_OFFLINE_MODE=true`，系统使用离线公开资料 fixture，方便稳定测试；生产采集可关闭该开关并接入合规搜索 API。爬虫工具已包含 robots.txt 检查、域名级限速和访问控制边界，不绕过登录、验证码或付费墙。

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

测试会完整验证：创建项目、运行 DAG、生成竞品知识库、构建 evidence、输出 Markdown/HTML/JSON 报告和 Agent 日志。
