from __future__ import annotations


class TrajectoryRecorder:
    """Collect lightweight execution breadcrumbs for debugging."""

    def __init__(self) -> None:
        self._records: list[dict] = []

    def append(self, item: dict) -> None:
        self._records.append(dict(item))

    def dump(self) -> list[dict]:
        return [dict(item) for item in self._records]
