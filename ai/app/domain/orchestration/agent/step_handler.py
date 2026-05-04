from __future__ import annotations

import inspect


class StepHandler:
    """Delegate the concrete step body to the selected handler."""

    async def execute(self, *, handler, task, step, resume_payload=None, progress_sink=None) -> dict:
        async_execute = getattr(handler, "execute_async", None)
        if async_execute is not None:
            return await async_execute(
                task=task,
                step=step,
                resume_payload=resume_payload,
                progress_sink=progress_sink,
            )

        result = handler.execute(task=task, step=step, resume_payload=resume_payload)
        if inspect.isawaitable(result):
            return await result
        return result
