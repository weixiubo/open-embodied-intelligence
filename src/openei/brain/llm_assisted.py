from __future__ import annotations

from ..contracts import PerceptionEvent, RuntimeContext, TaskPlan
from ..ports import Brain


class LLMAssistedSpeechBrain(Brain):
    """Phase 1 placeholder for an LLM-assisted planning surface.

    The delegate remains fully deterministic; this wrapper only annotates plans
    so the runtime can evolve without letting an LLM own execution safety.
    """

    def __init__(self, delegate: Brain) -> None:
        self._delegate = delegate

    def plan(self, event: PerceptionEvent, context: RuntimeContext) -> TaskPlan | None:
        plan = self._delegate.plan(event, context)
        if plan is None:
            return None

        plan.metadata = {
            **plan.metadata,
            "brain_mode": "llm-assisted",
            "llm_assistance": {
                "status": "placeholder",
                "reason": "Phase 1 keeps deterministic execution; LLM assistance is advisory only.",
            },
        }
        return plan
