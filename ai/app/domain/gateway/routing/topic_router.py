from __future__ import annotations


class TopicRouter:
    """Translate domain events and subscription targets into gateway topics."""

    @staticmethod
    def task_topic(task_run_id: str) -> str:
        return f"task:{task_run_id}"

    @staticmethod
    def all_topic() -> str:
        return "task:all"

    def topic_for_event(self, event) -> str:
        return self.task_topic(event.task_run_id)
