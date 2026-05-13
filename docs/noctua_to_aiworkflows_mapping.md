# noctua → ai-workflows（Python）功能对照与数据模型提炼

> 本文目标：把 noctua 的“真实业务”对齐到 ai-workflows 的 Python 模块中，避免仅停留在“采集指标”的误解。

## 1. noctua 的核心业务闭环（按运营动作）

1) **账号池/会话池**：多账号轮换（爬虫/评论/私信用途隔离），含 cookie/UA/device/verify 与在线时长等指标。  
2) **线索获取**：
   - 内容线索（视频/笔记搜索结果）：可筛选、可导出、可加入监控/评论维护。
   - 达人线索（KOL）：可筛选、可导出、可标记已建联。
3) **监控池（Track）**：
   - 内容监控：定期刷新互动指标；用于筛选“重要内容/可互动内容”。
   - 评论监控：对指定内容/评论入口周期性拉取评论明细，供运营处理。
4) **互动自动化**：
   - 评论：生成评论文案（LLM）→ 发送（HTTP/浏览器/实例执行器）→ 记录结果。
   - 私信/建联：实例执行器发送消息 → 记录结果。
5) **交付任务（KOL素材任务/外部任务服务）**：
   - 上传素材（视频/多图）+ 文案 + 品类/负责人/平台 → 分发给外部任务服务或内部工作流。
6) **审计与导出**：
   - 互动审计（成功/失败/原因）
   - 线索/任务/记录导出 Excel

## 2. ai-workflows（Python）需要覆盖的对象（对应表）

### 2.1 已有（0002_marketing）
- `mkt_platform_profiles`：自有账号/竞品账号统一
- `mkt_platform_sessions`：会话（MarketingSession v1）
- `mkt_contents`：内容主表
- `mkt_content_metric_snapshots`：内容指标快照（时序）
- `mkt_profile_metric_snapshots`：账号指标快照（时序）
- `mkt_comments`：评论明细
- `mkt_jobs` / `mkt_job_runs`：采集/刷新任务定义与运行记录

### 2.2 新增补齐（0003_marketing_track_interactions）
- `mkt_track_media`：内容监控池（对齐 noctua track_media）
- `mkt_track_comments`：评论监控池（对齐 noctua track_comment）
- `mkt_interaction_records`：互动审计（对齐 noctua interaction_record）

## 3. 关键差异：为什么要“Track 表”

noctua 的 `track_*` 不等于“抓取结果”，而是“运营动作入口 + 状态机”：
- 运营把内容加入监控 → 系统定期刷新 → 标记成功/失败/下次刷新时间
- 运营把内容加入评论维护 → 后续可批量评论/生成任务/重要内容排序

因此在 ai-workflows 中，`mkt_track_media/mkt_track_comments` 必须作为一等公民存在，不能只用 snapshots 替代。

## 4. 后续里程碑（仍然全 Python）

1) 实现真实的 xhs/douyin session validate（HTTP 探测 + 风控标记）  
2) 实现 track_media 刷新（更新最新指标并写快照）  
3) 实现 comment_sync（写入 mkt_comments）  
4) 实现 send_comment / send_message（写入 mkt_interaction_records）  
5) 再做 KOL 素材任务与外部任务服务对接

