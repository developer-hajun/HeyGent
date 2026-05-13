from __future__ import annotations


class TopicRouter:
    """Translate domain events and subscription targets into gateway topics."""

    @staticmethod
    def task_topic(task_run_id: str) -> str:
        return f"task:{task_run_id}"

    @staticmethod
    def all_topic() -> str:
        return "task:all"

    @staticmethod
    def session_topic(public_session_id: str) -> str:
        return f"session:{public_session_id}"

    def topic_for_event(self, event) -> str:
        return self.task_topic(event.task_run_id)
