# 세션 recall 축은 추후 재설계 예정이라 현재는 전체 비활성화한다.
#
# from __future__ import annotations
#
# from app.domain.session.sessions import TranscriptStore
#
#
# class RecallService:
#     """과거 대화 세션 검색은 TranscriptStore 단일 주체를 통해서만 수행한다."""
#
#     def __init__(self, session_store: TranscriptStore) -> None:
#         self._session_store = session_store
#
#     def search(self, query: str, *, limit: int = 5) -> list[dict]:
#         if not query.strip():
#             return []
#         return self._session_store.search_sessions(query.strip(), limit=limit)
