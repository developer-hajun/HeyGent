from __future__ import annotations


class TaskMaterializer:
    def __init__(self, planner) -> None:
        self.planner = planner

    def materialize(self, **kwargs):
        return self.planner.materialize_task(**kwargs)
