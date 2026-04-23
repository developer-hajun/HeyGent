from __future__ import annotations


class StepMaterializer:
    def __init__(self, planner) -> None:
        self.planner = planner

    def materialize(self, **kwargs):
        return self.planner.materialize_step(**kwargs)
