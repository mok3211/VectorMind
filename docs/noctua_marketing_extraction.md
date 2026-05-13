# noctua Marketing 逻辑抽取（面向 ai-workflows 集成）

> 结论先行：noctua 的 marketing 业务核心不是“页面”，而是 **(1) 平台登录会话管理** + **(2) 采集任务编排/调度** + **(3) 账号/内容/评论的指标持久化**。  
> 集成到 ai-workflows 时不建议照抄 `crawl_* / track_*` 的表与字段，而应提炼为可扩展的“平台适配器 + 会话 + 任务 + 指标快照”四件套。

---

## 0. 我已定位到的关键代码位置

### 前端（noctua）

- 媒体账号登录与管理  
  `noctua/frontend/src/views/noctua/media/account/*`
- Marketing 业务页（KOL/资源/监控/评论等）  
  `noctua/frontend/src/views/noctua/marketing/*`
  - `tracker/`：数据跟踪（TrackMedia/TrackComment 视角）
  - `video-monitor/`：内容监控（定时更新内容指标）
  - `video-comment/`：评论监控/评论运营（需要评论列表采集与回复能力）

前端调用后端方式：Wails bridge（`frontend/src/api/wails/*.ts`）  
包含：获取媒体账号列表/启动登录/启动采集任务/查询任务/导出等。

### 后端（noctua, Go）

- 登录（小红书/抖音）  
  - 小红书：`internal/media/xhs/web.go`
  - 抖音：`internal/media/douyin/web.go`（同时需要 device_info / verify params / a_bogus）
  - 会话存储：`internal/model/media_account.go`
- 采集与任务编排（对前端暴露的业务入口）  
  `backend/crawl/*.go`（例如 `media.go / tracker.go / task.go`）
- 采集器（执行真实抓取逻辑）  
  `kernel/crawls/{xiaohongshu,douyin}/*`
- 持久化模型（现有表结构）  
  `internal/model/*`（`crawl_task/crawl_media/crawl_user/crawl_comment/track_media/track_comment`）
- 调度器（队列/worker/QPS/重试）  
  `internal/scheduler/scheduler.go`

### 后端（noctua_api, Python）

你这次的重点是集成 noctua 的 marketing 逻辑，所以 noctua_api 我建议先把它当作“可选爬虫实现/补充数据源”，后面再决定接入点：  
（1）直接迁移到 ai-workflows；或（2）作为独立服务由 ai-workflows 调度调用。

---

## 1. 小红书/抖音登录：现有实现抽象

### 1.1 小红书登录（xhs）

现状要点：
- 通过浏览器自动化打开登录页：`https://www.xiaohongshu.com/explore`
- 监听 cookies，判断是否登录成功
- 以 `MediaAccount` 存储：`media_code=xiaohongshu`、`cookie`、`user_agent` 等

抽象成 ai-workflows 的能力：
1) `start_login(platform)`：返回一个“登录会话”（可能包含二维码/跳转链接/指引）
2) `poll_login_status(session_id)`：直到成功/失败/超时
3) `upsert_platform_session(profile_id, cookies, user_agent, ...)`
4) `validate_session(profile_id)`：定期校验会话是否失效

### 1.2 抖音登录（douyin）

现状要点：
- 同样走浏览器自动化，但抖音请求签名更敏感：需要
  - `user_agent`
  - `device_info`
  - verify 参数（webid / msToken / verifyFp / fp）
  - 某些接口还要 `a_bogus`
- 会话仍落 `MediaAccount`，同时存 `device_info`

抽象成 ai-workflows 的能力：
- 账户会话不仅是 cookies，还包含 “设备指纹/UA/verify 参数” 的组合体  
  因此 session 表需要 JSONB/加密字段容纳这些差异。

---

## 2. 指标采集（爬虫）现有形态：你真正需要的“数据面”

从 `crawl_* / track_*` 模型与 marketing 页面字段可以总结出：

### 2.1 账号维度（profile）

noctua 抓取并展示的典型字段（以 `crawl_user` 为主）：
- 用户标识：`sec_uid`（核心）、`uid/user_unique_id/short_user_id`（平台差异）
- `user_link`（主页链接，能直接打开）
- 昵称/头像/签名/地区/性别
- 指标：`fans/follows/interaction/videos_count`
- 认证：`verify_type/verify_name`
- 来源：kol/media/track（用于区分采集来源）

提炼建议：把这些字段拆成
- Profile 主表（稳定字段）
- Profile 指标快照表（时序）

### 2.2 内容维度（content）

noctua 抓取并展示的典型字段（以 `crawl_media`、`track_media` 为主）：
- 内容标识：`media_id`（平台内容 id）
- 标题/描述/发布时间 `create_time`、url
- 指标：`liked/comment/collected/share`（有的平台还会有播放/曝光）
- tags_ids / source（来源关键词）
- 原始 raw_data（用于兜底与排查）

提炼建议：内容主表 + 内容指标快照表（时序）。

### 2.3 评论维度（comment）

noctua 抓取并展示的典型字段（以 `crawl_comment`、`track_comment` 为主）：
- comment_id、parent_comment_id
- 关联 media_id
- 评论内容、图片、地区、发布时间
- like_count、sub_comment_count

提炼建议：评论表 + （可选）评论指标快照（如果要跟踪评论点赞变化）。

---

## 3. Marketing 业务“优化提炼”的需求（集成到 ai-workflows）

> 目标：把当前分散的“采集/跟踪/导出”做成一个可扩展的工作流模块。

### 3.1 核心闭环（MVP）

1) 平台账号登录（小红书/抖音）→ 会话入库（可校验、可失效）  
2) 新建采集任务：
   - 账号内容列表采集（按关键词/按达人/按链接）
   - 内容指标采集（定时刷新）
3) 数据入库：
   - profiles / contents / metric_snapshots
4) 后台看板：
   - 账号列表 + 登录状态
   - 采集任务列表 + 最近运行
   - 内容列表 + 指标趋势/最新值

### 3.2 重要扩展（你提到的“竞品/榜单/转化”）

- 竞品监控：把 competitor 当作 profile_type=competitor，采集同样的内容与快照
- 关键词/榜单：关键词结果快照（时序），用于排名变化/热点追踪
- 转化/投放：建议作为独立 source 接入（CRM/表单/电商），通过 profile_id/content_id 做归因映射

### 3.3 风控/合规（必须纳入 DB 设计）

建议至少记录：
- login_event（每次登录尝试/失败原因）
- session_status（valid/expired/invalid）
- risk_status（captcha/blocked/limited）
- proxy/ua/device 的使用情况（必要时）

---

## 4. 数据库设计（最终以 Postgres + Alembic 落地）

我建议在 ai-workflows 中新增一套“marketing 前缀”的表，避免与现有表（users/agent_runs/media_accounts）冲突，后续再做迁移合并。

### 4.1 表清单（建议）

- `mkt_platform_profiles`：平台账号/作者（自有/竞品统一）
- `mkt_platform_sessions`：登录会话（cookies + ua + device_info + verify params…）
- `mkt_contents`：内容主表（笔记/视频）
- `mkt_content_metric_snapshots`：内容指标快照（时序）
- `mkt_profile_metric_snapshots`：账号指标快照（时序）
- `mkt_comments`：评论（必要时）
- `mkt_jobs`：采集任务定义（类型/参数/计划）
- `mkt_job_runs`：采集任务运行记录（状态/错误/统计）
- `mkt_keyword_result_snapshots`：关键词结果快照（时序，竞品/行业榜单）
- （可选）`mkt_login_events`：登录事件与风控记录

下一步我会把它转成 **ai-workflows 的 Alembic 迁移**（0002 或更高版本），并同步生成对应 SQLModel models。

### 4.2 我已在 ai-workflows 中落地的迁移与模型

- SQLModel models：`server/marketing/models.py`
- Alembic revision：`alembic/versions/0002_marketing.py`

应用迁移：
```bash
uv run alembic upgrade head
```
