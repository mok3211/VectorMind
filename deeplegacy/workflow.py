from __future__ import annotations

from server.workflows.specs import WorkflowSpec


spec = WorkflowSpec(
    agent="morning_history",
    name="早安历史（deeplegacy）",
    nodes=[
        {"id": "start", "label": "开始", "position": {"x": 0, "y": 60}},
        {"id": "date", "label": "获取日期", "position": {"x": 190, "y": 60}},
        {"id": "prompt", "label": "Prompt 渲染", "position": {"x": 410, "y": 60}},
        {"id": "llm", "label": "LLM 生成历史事件", "position": {"x": 650, "y": 60}},
        {"id": "out", "label": "输出文案", "position": {"x": 910, "y": 60}},
        {"id": "image", "label": "配图（预留）", "position": {"x": 650, "y": 200}},
        {"id": "video", "label": "视频（预留）", "position": {"x": 910, "y": 200}},
        {"id": "publish", "label": "导出/发布（预留）", "position": {"x": 1150, "y": 120}},
    ],
    edges=[
        {"id": "e1", "source": "start", "target": "date"},
        {"id": "e2", "source": "date", "target": "prompt"},
        {"id": "e3", "source": "prompt", "target": "llm"},
        {"id": "e4", "source": "llm", "target": "out"},
        {"id": "e5", "source": "out", "target": "publish"},
        {"id": "e6", "source": "out", "target": "image"},
        {"id": "e7", "source": "image", "target": "video"},
        {"id": "e8", "source": "video", "target": "publish"},
    ],
)

