# noctua → ai-workflows：Marketing 模块集成（需求提炼 & 数据库设计草案）

> 说明：此文档是“在还未读取 noctua 代码前”的 **优化提炼版需求与 DB 草案**。  
> 你挂载 `noctua` 文件夹后，我会对照现有实现（fronted/views/noctua 下的 marketing 逻辑）做差异分析与调整，并输出最终落地 schema + 迁移版本。

## 1. 总体目标（你想要的能力）

把“内容生产（agents）”与“自媒体运营（登录/采集/指标/发布）”做成一个可扩展系统：

1) **账号体系**：统一管理多个平台账号（小红书/抖音优先），可查看登录状态、会话有效期、风控状态。  
2) **数据采集**：对“自有账号”与“竞品账号/关键词结果”采集内容列表与指标。  
3) **指标体系**：沉淀“账号维度”与“内容维度”的时序指标（快照），用于看板、对比、归因与复盘。  
4) **任务调度**：采集任务可配置频率（例如每小时/每日），可重试、可追踪运行日志。  
5) **工作流可视化**：每条链路关键节点可见（登录→采集→清洗→入库→导出/发布）。  
6) **未来扩展**：生图/生视频（封面图、口播视频）与一键发布（先导出文案，后接半自动/官方 API）。

## 2. 需求提炼（不要照抄、只保留“系统必需的抽象”）

### 2.1 登录（重点：小红书 & 抖音）

**核心结论**：登录不应作为“前端页面逻辑”散落在各处，应上收为后端的“平台适配器 + 会话管理”。

建议拆成 3 层：

- **Platform Adapter（平台适配器）**：实现具体平台的登录/刷新/校验/抓取。  
  - xhs：扫码/验证码/账号密码（以你现有实现为准），最终落到 cookies/localStorage/token  
  - douyin：扫码/短信/账号密码（以你现有实现为准）
- **Session Manager（会话管理）**：统一保存会话、判断过期、刷新、风控标记。
- **Admin UI（后台）**：只负责触发/展示（开始登录、展示二维码、展示状态、手工标记失效）。

登录“最小可用”闭环（MVP）：
1) 触发登录 → 2) 拿到可复用会话（cookies 等）→ 3) 校验会话有效 → 4) 入库 → 5) 可用于采集

### 2.2 指标采集（重点：账号与内容数据，且可扩展）

以“快照”为中心建模，避免一开始就强绑定某个平台字段：

- **账号快照**：followers/following/获赞/作品数/曝光（如可得）等
- **内容快照**：播放/点赞/收藏/评论/分享（按平台可得字段）
- **榜单/关键词结果**：关键词→结果列表（排名、内容/作者 id、当时指标摘要）

### 2.3 竞品/行业监测

竞品本质上也是 “profile（平台账号/作者）”，不必单独做一套表结构：
- 只要能把“自有账号”和“竞品账号”都映射到同一种 profile 模型即可。

### 2.4 投放/转化类（你选了要做，但建议拆阶段）

投放/转化通常来自外部系统（表单/CRM/电商），平台侧未必能直接爬到。

建议抽象为：
- **Attribution Source**：来源系统
- **Conversion Event**：线索/订单/GMV 等事件（按 source 字段扩展）

### 2.5 合规与风控（强烈建议作为“一等公民”）

必须持久化：
- 登录失败原因/频率
- 风控状态（captcha/禁言/限制/需要验证）
- 代理/指纹/UA 策略（如确实要做）

## 3. 数据库设计（PostgreSQL + Alembic，建议 JSONB + 关键字段结构化）

### 3.1 核心实体关系（简化版 ER）

```
users
  └─ organizations (可选)
       └─ platform_profiles (自有/竞品统一)
            ├─ platform_sessions (仅自有账号需要)
            ├─ contents
            │    └─ content_metric_snapshots (时序)
            └─ profile_metric_snapshots (时序)

crawl_jobs (定时/手动)
  └─ crawl_runs (每次执行)
       └─ crawl_artifacts (可选：原始HTML/截图/调试文件元数据)

keywords
  └─ keyword_result_snapshots (时序)

conversion_sources
  └─ conversion_events (时序)
```

### 3.2 表结构建议（字段草案）

> 命名仅草案，最终以你现有 noctua 逻辑与字段为准做裁剪。

#### A) platform_profiles（统一“平台账号/作者”，包含自有与竞品）
- id (pk)
- platform (xhs/douyin/…)
- profile_type (owned/competitor)
- platform_profile_id（平台侧 uid）
- nickname
- profile_url
- avatar_url
- status（active/disabled）
- risk_status（normal/captcha/limited/banned/unknown）
- meta_json (JSONB)（平台差异字段兜底）
- created_at / updated_at

#### B) platform_sessions（仅 owned 需要：保存 cookies/token）
- id (pk)
- profile_id (fk → platform_profiles.id)
- session_type（cookies/local_storage/token）
- session_json (JSONB)（建议应用层加密后再存；至少不要明文密码）
- expires_at / refreshed_at / last_validated_at
- status（valid/expired/invalid）
- created_at / updated_at

#### C) contents（平台内容：笔记/视频）
- id (pk)
- platform (冗余，方便索引)
- profile_id (fk)
- platform_content_id
- content_type（note/video/live…）
- title
- content_url
- published_at
- raw_json (JSONB)（原始字段兜底）
- created_at / updated_at

#### D) content_metric_snapshots（内容指标快照，时序表）
- id (pk)
- content_id (fk)
- captured_at (timestamp)
- views / likes / comments / favorites / shares（可为空）
- metrics_json (JSONB)（平台差异字段兜底）
- unique(content_id, captured_at)

#### E) profile_metric_snapshots（账号指标快照，时序表）
- id (pk)
- profile_id (fk)
- captured_at
- followers / following / likes_total / posts_total（可为空）
- metrics_json (JSONB)
- unique(profile_id, captured_at)

#### F) crawl_jobs（采集任务定义）
- id (pk)
- name
- platform
- job_type（profile_contents/profile_metrics/content_metrics/keyword_search/…）
- target_profile_id（可空：keyword job）
- params_json (JSONB)（如：关键词、分页、时间窗）
- cron（可空：手动）
- enabled (bool)
- created_by (user_id)
- created_at / updated_at

#### G) crawl_runs（每次采集执行记录）
- id (pk)
- job_id (fk)
- status（running/success/failed）
- started_at / finished_at
- error_text
- stats_json (JSONB)（抓取条数/耗时/重试次数）

#### H) keyword_result_snapshots（关键词结果时序）
- id (pk)
- platform
- keyword
- captured_at
- results_json (JSONB)（列表：rank/content_id/profile_id/摘要指标）

#### I) conversion_events（转化事件：线索/订单/GMV）
- id (pk)
- source（crm/form/shop/…）
- occurred_at
- profile_id/content_id（可空，用于归因）
- amount/qty/status（可空）
- payload_json (JSONB)

### 3.3 与当前 ai-workflows 表的关系

你现在已有：
- users
- agent_runs（内容生成记录）
- media_accounts（占位）

建议演进方式：
1) `media_accounts` 逐步退役/合并进 `platform_profiles + platform_sessions` 的结构；  
2) `agent_runs.assets_json` 未来可放：封面图路径、视频路径、发布任务 id；  
3) 新增 “publish_jobs/publish_runs” 两张表（如果要做真正自动发布）。

## 4. 迁移落地策略（MVP → 完整）

### MVP（最快落地）
1) owned 账号登录（xhs/douyin 任选其一优先）  
2) 账号信息/内容列表采集（入库 contents + profile 快照）  
3) 内容指标快照（定时采集）  
4) 后台：登录状态 + 采集任务 + 指标列表/趋势

### 扩展
- 竞品/关键词监测
- 风控/代理池
- 生图（封面）→ 生视频（口播）→ 发布（半自动/官方 API）

