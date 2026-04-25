from server.workflows.registry import workflow_registry
from server.workflows.specs import WorkflowSpec


def register_workflows() -> None:
    """
    在 main.lifespan 里调用。把每个 agent 的流程图注册起来，供后台可视化使用。
    """

    from morning_radio.workflow import spec as morning_radio_spec
    from book_recommendation.workflow import spec as book_spec
    from travel_planner.workflow import spec as travel_spec
    from deeplegacy.workflow import spec as history_spec

    workflow_registry.register(morning_radio_spec)
    workflow_registry.register(book_spec)
    workflow_registry.register(travel_spec)
    workflow_registry.register(history_spec)

