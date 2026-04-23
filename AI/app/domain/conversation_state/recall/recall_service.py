from __future__ import annotations


class RecallService:
    def search(self, query: str) -> list[str]:
        if not query.strip():
            return []
        return [query.strip()]
