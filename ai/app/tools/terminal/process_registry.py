from __future__ import annotations


class ProcessRegistry:
    """장기 실행 프로세스를 추적하기 위한 최소 registry 자리다."""

    def __init__(self) -> None:
        self._processes: dict[str, dict] = {}

    def register(self, process_id: str, metadata: dict) -> None:
        self._processes[process_id] = dict(metadata)

    def get(self, process_id: str) -> dict | None:
        record = self._processes.get(process_id)
        return dict(record) if record is not None else None
