from __future__ import annotations


class ProcessRegistry:
    """Minimal process registry placeholder aligned to Hermes terminal tooling."""

    def __init__(self) -> None:
        self._processes: dict[str, dict] = {}

    def register(self, process_id: str, metadata: dict) -> None:
        self._processes[process_id] = dict(metadata)

    def get(self, process_id: str) -> dict | None:
        record = self._processes.get(process_id)
        return dict(record) if record is not None else None
