from __future__ import annotations

from app.domain.capabilities.children.specs.child_session import ChildSessionSpec


class ChildSessionLauncher:
    """child runtime 의 최소 뼈대다.

    지금 단계에서는 실제 child 세션을 완전하게 실행하지 않더라도,
    부모 StepRun detail 이 어떤 linkage 키를 가져야 하는지는 먼저 고정해 둔다.
    이후 delegate 기능을 붙일 때도 같은 키를 계속 쓰게 만들려는 목적이다.
    """

    def build_pending_detail(self, spec: ChildSessionSpec) -> dict:
        return {
            "agentDetail": {
                "called": True,
                "agentId": f"{spec.parent_step_run_id}:child",
                "childTaskRunId": None,
            }
        }
