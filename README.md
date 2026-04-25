# AI 创意工作流（FastAPI + LiteLLM）

目标：把多个“起号”内容生产小项目做成可扩展的 **Agent 集合**，统一由一个 FastAPI 服务对外提供接口；同时支持 **随时切换模型、切换提示词版本、未来扩展发布到抖音/小红书等平台**。

## 项目结构（仓库根目录）

```
server/                 # FastAPI 主服务 + 共享能力（LLM、Prompt、发布器）
deeplegacy/             # 早安历史（你已创建的历史 agent 文件夹）
morning_radio/          # 早安电台 agent
book_recommendation/    # 书单推荐 agent
travel_planner/         # 旅游规划 agent
```

## 快速开始（uv）

1. 复制环境变量：
```bash
cp .env.example .env
```

2. 启动 PostgreSQL（推荐 docker-compose）：
```bash
docker compose up -d
```

3. 安装依赖（uv）：
```bash
uv sync
```

4. 启动服务：
```bash
uv run uvicorn server.main:app --reload
```

打开：`http://127.0.0.1:8000/docs`

## 管理后台（Vue3 + Naive UI）

管理后台位于 `admin/`，前后端分离运行（开发模式通过 Vite proxy 访问后端）。

启动：
```bash
cd admin
npm install
npm run dev
```

访问：`http://127.0.0.1:5173`

首次初始化管理员（仅当数据库里没有任何用户时可执行一次）：
```bash
curl -X POST http://127.0.0.1:8000/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"change-me"}'
```

## 设计要点

- **模型切换**：统一走 LiteLLM（`server/llm/client.py`），只改 `.env` 的 `LLM_MODEL_DEFAULT` 或某个 agent 的 `*_MODEL` 即可。
- **提示词切换**：每个 agent 都有 `prompts/<version>/`，可通过 `.env` 的 `*_PROMPT_VERSION` 切换。
- **Skills（能力插件）**：每个 agent 都通过 `server/skills/*` 调用能力（prompt_render / llm_generate / image_generate / video_generate ...），未来接生图/生视频只需替换对应 skill。
- **工作流可视化**：每个 agent 都有 `workflow.py`（nodes/edges），后台页面可视化关键节点；API：`GET /api/workflows`。
- **发布到平台**：先做成“工作流最后一步的 Publisher 插件”（导出文本/结构化数据），后续再按平台能力选择：
  - 官方 API（若可用）；
  - 或 Playwright 自动化“辅助发布”（不建议爬虫/逆向，避免账号风险）。

## 数据库迁移提示

当前开发阶段默认使用 `SQLModel.metadata.create_all` 自动建表。**如果你新增了字段/表结构**：
- 开发环境可直接删库/删表重建；
- 需要正式迁移时，已预留 `alembic` 依赖（后续我可以帮你补全迁移脚手架与版本管理）。
