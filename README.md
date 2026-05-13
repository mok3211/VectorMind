# AI 创意工作流（FastAPI + LangChain）

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

4. 初始化/升级数据库（Alembic）：

```bash
uv run alembic upgrade head
```

5. 启动服务：

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

- **模型切换**：统一走 LangChain（`server/llm/client.py` + ChatNVIDIA），只改 `.env` 的 `LLM_MODEL_DEFAULT` 或某个 agent 的 `*_MODEL` 即可。
- **提示词切换**：每个 agent 都有 `prompts/<version>/`，可通过 `.env` 的 `*_PROMPT_VERSION` 切换。
- **Skills（能力插件）**：每个 agent 都通过 `server/skills/*` 调用能力（prompt_render / langchain_generate / image_generate / video_generate ...），未来接生图/生视频只需替换对应 skill。
- **工作流可视化**：每个 agent 都有 `workflow.py`（nodes/edges），后台页面可视化关键节点；API：`GET /api/workflows`。
- **发布到平台**：先做成“工作流最后一步的 Publisher 插件”（导出文本/结构化数据），后续再按平台能力选择：
  - 官方 API（若可用）；
  - 或 Playwright 自动化“辅助发布”（不建议爬虫/逆向，避免账号风险）。
- **自动发布（新增）**：新增 `server/new_media/*`，支持小红书/抖音扫码登录、持久化浏览器指纹（profile）和自动发布（失败会回退到人工确认模式）。

## 数据库迁移（Alembic）

本项目使用 **Alembic** 管理表结构（不再自动 create_all）。

常用命令：

```bash
# 生成迁移（推荐：修改 models 后执行）
uv run alembic revision --autogenerate -m "your message"

# 应用迁移
uv run alembic upgrade head
```

## Prompt 迭代（可在后台可视化/编辑）

- 后端接口：
  - `GET /api/prompts`：列出所有 agent 的 prompt 版本
  - `GET /api/prompts/{agent}/{version}`：读取 system/user
  - `PUT /api/prompts/{agent}/{version}`：保存 system/user
- 后台页面：菜单 **Prompts**（支持选择 agent + 版本，在线编辑保存）

建议工作流：

1. 复制 `v1` 为 `v2`（新增文件夹）
2. 在后台编辑 `v2` 的 system/user

## Marketing（小红书/抖音登录、采集、指标）

### 数据库

已增加营销侧表结构（`mkt_*`），对应 Alembic 迁移版本：`0002_marketing`：
```bash
uv run alembic upgrade head
```

已补齐 noctua 核心的“监控池/互动审计”表结构（对应 Alembic：`0003_marketing_track_interactions`）：
- `mkt_track_media`：内容监控池（对齐 noctua track_media）
- `mkt_track_comments`：评论监控池（对齐 noctua track_comment）
- `mkt_interaction_records`：互动审计（对齐 noctua interaction_record）

### 后端接口（管理员权限）

基础管理：
- `GET /api/marketing/profiles` / `POST /api/marketing/profiles`
- `GET /api/marketing/sessions` / `POST /api/marketing/sessions/import`
- `GET /api/marketing/jobs` / `POST /api/marketing/jobs`
- `POST /api/marketing/jobs/{id}/run`（触发执行，当前 crawler 为 stub）
- `GET /api/marketing/job-runs`

监控池/互动审计：
- `GET /api/marketing/track-media` / `POST /api/marketing/track-media`
- `PUT /api/marketing/track-media/{id}/toggle-comment`
- `GET /api/marketing/track-comments` / `POST /api/marketing/track-comments` / `DELETE /api/marketing/track-comments/{id}`
- `GET /api/marketing/interaction-records`

### 管理后台

菜单 **Marketing**：账号 / 会话导入 / 任务与运行记录 / 监控 / 互动记录。

## 登录（内置管理员）

默认在服务启动时会自动创建一个管理员账号（仅当数据库里没有任何用户时）：
- 账号：`zhangchi`
- 密码：`zhangchi2026`

可通过环境变量覆盖（见 `.env.example`）：`BOOTSTRAP_ADMIN_*`

## 角色与权限（RBAC）与套餐（订阅/VIP）

系统内置三类角色（可在后台调整权限/新增角色）：
- `admin` 管理员：全权限（兼容旧字段 `is_admin`）
- `operator` 操作员：Marketing/媒体账号等业务操作权限
- `user` 普通用户：只读为主

权限模型：
- `roles`：角色
- `permissions`：权限点（如 `marketing.view` / `marketing.manage`）
- `user_roles` / `role_permissions`：多对多关联
- `menu_modules`：可分配菜单（每个菜单可绑定一个 permission_code）

套餐模型（先做配置与手工授予，不含支付对接）：
- `subscription_plans`：Free/Pro/VIP（支持月/季/年价格字段）
- `user_subscriptions`：用户订阅记录（active/expired/canceled）

初始化说明：
- 启动时会自动写入默认权限/角色/菜单/套餐（前提：已执行 `alembic upgrade head`）
- 后台路径：`/rbac`（用户/角色/菜单/套餐配置）

## 一键启动脚本（insta）

项目根目录提供 `./insta` 用于安装依赖与管理进程：
```bash
chmod +x ./insta
./insta install
./insta start all
./insta status
./insta restart api
./insta stop all
```

日志与 PID：
- 日志：`./logs/*.log`
- PID：`./.run/*.pid`

## 本地小助手（Local Agent）+ Chrome 插件（企业端执行器）

> 用途：在企业运营电脑上执行 Playwright（复用本机浏览器登录态），Server 只负责调度与入库。

### 1) Server：创建 Executor 并获取 token

1. 登录后台（管理员）
2. 调用接口创建 executor：`POST /api/executors`（body: `{ "name": "ops-mac-01" }`）
3. 响应里会返回 `token`，复制备用（Local Agent 要用）

### 2) 启动 Local Agent（运行在运营电脑）

环境变量（示例）：
```bash
export AGENT_SERVER_BASE_URL="http://127.0.0.1:8000"
export AGENT_EXECUTOR_TOKEN="复制上一步返回的 token"
export AGENT_USER_DATA_DIR="./.agent_profile"
export AGENT_HEADLESS=false
export AGENT_SLOW_MO_MS=200
export AGENT_CONCURRENCY=1
```

启动：
```bash
uv run uvicorn local_agent.main:app --host 127.0.0.1 --port 18765
```

第一次请确保安装浏览器：
```bash
uv run playwright install chromium
```

### 3) 安装 Chrome 插件（先兼容 Chrome）

1. 打开 `chrome://extensions`
2. 打开「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择项目里的 `extension/` 目录

然后打开小红书/抖音页面，点击插件按钮「采集当前页面指标」即可触发本机采集并回传 Server 入库。

### 4) 插件如何打包/安装（给客户测试/内部分发）

#### 开发/测试（推荐）
1. `chrome://extensions` 打开「开发者模式」
2. 「加载已解压的扩展程序」→ 选择项目里的 `extension/` 目录
3. 更新代码后：在扩展列表里点「重新加载」

#### 打包（zip）
用于内部传递（客户/同事拿到 zip 后仍然用“加载已解压”方式）：
1. 将 `extension/` 目录打包成 zip（压缩的是目录内容）
2. 解压到任意文件夹
3. 仍按“加载已解压的扩展程序”安装

> 说明：Chrome 正式商店/企业策略分发的流程不同（需要签名/政策推送），MVP 阶段先用“加载已解压”足够测试。

### 5) 采集产物（截图/录像）在哪里
Local Agent 会在本机生成：
- `./.agent_artifacts/screenshots/*.png`
- `./.agent_artifacts/videos/*`

并会将产物上传到 Server 的 `media_profile_root/executor_artifacts/<executor_id>/` 目录下（当前版本先落盘，后续可接对象存储）。

### 切换为真实抓取（Playwright，适用于 xhs & douyin）

> 说明：真实抓取依赖你导入的 cookie + UA，且需要你本机 Playwright 可启动浏览器；平台前端结构变化时可能需要你测试后我再修选择器。

1) 安装浏览器（首次需要）：
```bash
uv run playwright install chromium
```

2) `.env` 设置：
```bash
MARKETING_CRAWLER_MODE=playwright
MARKETING_PLAYWRIGHT_HEADLESS=true
MARKETING_PLAYWRIGHT_SLOW_MO_MS=0
```

3) 在 **监控** 里新增 track_media / track_comments 时，尽量填写 `URL`（Playwright 会直接打开页面解析指标/评论）。

4) 运行任务：
- `content_metrics`：会打开每个 URL 并解析点赞/评论/收藏/分享等数值，写入快照并回写监控池最新指标。
- `comment_sync`：会尝试从网络响应提取评论列表并落库到 `mkt_comments`（若平台改版导致抓不到，会在 run.error 中提示）。

### 真实评论发送（send_comment）

已提供接口与后台按钮（监控列表里每条内容可点“评论”）：
- API：`POST /api/marketing/send-comment`
- 后台：Marketing → 监控 → 内容监控列表 → 操作「评论」

注意：
- 平台风控/验证码出现时，发送会失败并在“互动记录”里留痕（`mkt_interaction_records`）。
- 建议测试阶段使用 `MARKETING_PLAYWRIGHT_HEADLESS=false` + `MARKETING_PLAYWRIGHT_SLOW_MO_MS=200` 观察浏览器行为。

### 会话导入格式（MarketingSession v1）

会话导入接口：`POST /api/marketing/sessions/import`

`session_data` 推荐使用自定义 **MarketingSession v1**（只要满足必填项即可）：
- `version`: 固定为 `1`
- `platform`: `xhs` 或 `douyin`（需与 profile.platform 一致）
- `auth.cookies`: cookie 数组，至少包含 `name/value`；`domain/path` 建议补齐
- `client.user_agent`: 建议填写（平台风控与签名通常依赖 UA）

## 关键环境变量

```env
# LangChain NVIDIA Key
NVIDIA_API_KEY=your_nvidia_api_key

# 默认模型（NVIDIA NIM）
LLM_MODEL_DEFAULT=meta/llama-3.1-70b-instruct

# 新媒体账号指纹存储目录（相对项目根目录）
MEDIA_PROFILE_ROOT=.media_profiles
```

## 新媒体自动发布 API

依赖安装后请先安装浏览器内核：

```bash
uv sync
uv run playwright install chromium
```

扫码登录（保存账号会话/指纹）：

```bash
POST /api/media-publish/accounts/{account_id}/connect
{
  "timeout_sec": 180,
  "headless": false
}
```

自动发布：

```bash
POST /api/media-publish/accounts/{account_id}/publish
{
  "title": "标题",
  "text": "正文",
  "tags": ["AI", "运营"],
  "dry_run": false
}
```
