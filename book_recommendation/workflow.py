from __future__ import annotations

from server.workflows.specs import WorkflowSpec


spec = WorkflowSpec(
    agent="book_recommendation",
    name="书单推荐",
    nodes=[
        {"id": "start", "label": "开始", "position": {"x": 0, "y": 60}},
        {"id": "prompt", "label": "Prompt 渲染", "position": {"x": 220, "y": 60}},
        {"id": "llm", "label": "LLM 生成书单", "position": {"x": 460, "y": 60}},
        {"id": "out", "label": "输出文案", "position": {"x": 700, "y": 60}},
        {"id": "image", "label": "封面图（预留）", "position": {"x": 460, "y": 200}},
        {"id": "video", "label": "口播视频（预留）", "position": {"x": 700, "y": 200}},
        {"id": "publish", "label": "导出/发布（预留）", "position": {"x": 940, "y": 120}},
    ],
    edges=[
        {"id": "e1", "source": "start", "target": "prompt"},
        {"id": "e2", "source": "prompt", "target": "llm"},
        {"id": "e3", "source": "llm", "target": "out"},
        {"id": "e4", "source": "out", "target": "publish"},
        {"id": "e5", "source": "out", "target": "image"},
        {"id": "e6", "source": "image", "target": "video"},
        {"id": "e7", "source": "video", "target": "publish"},
    ],
)

