from __future__ import annotations

from server.workflows.specs import WorkflowSpec


spec = WorkflowSpec(
    agent="travel_planner",
    name="旅游规划",
    nodes=[
        {"id": "start", "label": "开始", "position": {"x": 0, "y": 60}},
        {"id": "prompt", "label": "Prompt 渲染", "position": {"x": 220, "y": 60}},
        {"id": "llm", "label": "LLM 生成行程", "position": {"x": 460, "y": 60}},
        {"id": "out", "label": "输出行程", "position": {"x": 700, "y": 60}},
        {"id": "map", "label": "地图/POI（预留）", "position": {"x": 460, "y": 200}},
        {"id": "image", "label": "路线图/封面图（预留）", "position": {"x": 700, "y": 200}},
        {"id": "publish", "label": "导出/发布（预留）", "position": {"x": 940, "y": 120}},
    ],
    edges=[
        {"id": "e1", "source": "start", "target": "prompt"},
        {"id": "e2", "source": "prompt", "target": "llm"},
        {"id": "e3", "source": "llm", "target": "out"},
        {"id": "e4", "source": "out", "target": "publish"},
        {"id": "e5", "source": "out", "target": "map"},
        {"id": "e6", "source": "map", "target": "image"},
        {"id": "e7", "source": "image", "target": "publish"},
    ],
)

