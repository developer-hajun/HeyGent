from __future__ import annotations

import inspect


class StepHandler:
    """Delegate the concrete step body to the selected handler."""

    async def execute(self, *, handler, task, step, resume_payload=None, progress_sink=None, delegate_executor=None) -> dict:
        async_execute = getattr(handler, "execute_async", None)
        if async_execute is not None:
            kwargs = {
                "task": task,
                "step": step,
                "resume_payload": resume_payload,
                "progress_sink": progress_sink,
            }
            if _supports_keyword(async_execute, "delegate_executor"):
                # delegate_executor 는 agent.loop 처럼 worker 위임을 직접 처리하는 handler 에만 전달한다.
                kwargs["delegate_executor"] = delegate_executor
            return await async_execute(**kwargs)

        result = handler.execute(task=task, step=step, resume_payload=resume_payload)
        if inspect.isawaitable(result):
            return await result
        return result


def _supports_keyword(function, keyword: str) -> bool:
    """handler 별 시그니처 차이를 허용하면서 새 실행 콜백을 점진적으로 주입한다."""

    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return False
    if keyword in signature.parameters:
        return True
    return any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
