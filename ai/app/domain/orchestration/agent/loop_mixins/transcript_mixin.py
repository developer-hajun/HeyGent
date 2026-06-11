"""TranscriptMixin: transcript 세션 생성·메시지 저장/복원."""
from __future__ import annotations

import json
from typing import Any

from app.core.utils.ids import new_id
from app.domain.providers.model.base import AgentMessage, ToolResultMessage


class TranscriptMixin:
    """agent.loop 실행 기록을 transcript 세션에 저장하고 replay용으로 복원한다."""

    def _ensure_transcript_session(
        self,
        *,
        task: Any,
        task_input: dict[str, Any],
        model: str,
    ) -> str | None:
        """transcript 저장소가 있으면 agent.loop 기록을 같은 세션에 묶는다."""
        if self.session_store is None:
            return None
        explicit_session_id = self._optional_text(task_input.get("transcript_session_id"))
        if explicit_session_id and self.session_store.get_session(explicit_session_id) is not None:
            return explicit_session_id
        session_key = str(
            getattr(task, "session_key", "") or getattr(task, "task_run_id", "")
        ).strip()
        if not session_key:
            return None
        latest = self.session_store.get_latest_session_by_key(session_key)
        if latest is not None:
            return str(latest["id"])
        session_id = new_id("session")
        self.session_store.create_session(
            session_id=session_id,
            session_key=session_key,
            source="agent.loop",
            user_id=getattr(task, "owner_key", None),
            model=model,
            title=str(
                getattr(task, "title", "") or task_input.get("prompt") or session_key
            )[:120],
            metadata={"task_run_id": getattr(task, "task_run_id", None)},
        )
        return session_id

    def _load_transcript_messages(
        self,
        session_id: str | None,
    ) -> list[AgentMessage | ToolResultMessage]:
        """저장된 transcript를 provider 재호출 입력으로 복원한다."""
        if self.session_store is None or not session_id:
            return []
        messages: list[AgentMessage | ToolResultMessage] = []
        for row in self.session_store.list_messages(session_id):
            role = str(row.get("role") or "")
            if role == "tool":
                tool_call_id = str(row.get("tool_call_id") or "")
                if tool_call_id:
                    messages.append(
                        ToolResultMessage(
                            tool_call_id=tool_call_id,
                            content=str(row.get("content") or ""),
                        )
                    )
                continue
            if role in {"system", "developer", "user", "assistant"}:
                messages.append(
                    AgentMessage(
                        role=role,
                        content=row.get("content"),
                        tool_calls=list(row.get("tool_calls") or []),
                        metadata=dict(row.get("metadata") or {}),
                    )
                )
        return self._order_tool_results_for_replay(messages)

    @staticmethod
    def _order_tool_results_for_replay(
        messages: list[AgentMessage | ToolResultMessage],
    ) -> list[AgentMessage | ToolResultMessage]:
        """assistant tool_calls 뒤의 tool result 순서를 provider replay 규칙에 맞춘다."""
        ordered: list[AgentMessage | ToolResultMessage] = []
        index = 0
        while index < len(messages):
            message = messages[index]
            ordered.append(message)
            index += 1
            if (
                not isinstance(message, AgentMessage)
                or message.role != "assistant"
                or not message.tool_calls
            ):
                continue
            tool_messages: list[ToolResultMessage] = []
            while index < len(messages) and isinstance(messages[index], ToolResultMessage):
                tool_messages.append(messages[index])
                index += 1
            by_call_id = {tm.tool_call_id: tm for tm in tool_messages}
            emitted_ids: set[str] = set()
            for tool_call in message.tool_calls:
                tm = by_call_id.get(tool_call.id)
                if tm is not None:
                    ordered.append(tm)
                    emitted_ids.add(tm.tool_call_id)
            ordered.extend(tm for tm in tool_messages if tm.tool_call_id not in emitted_ids)
        return ordered

    def _append_transcript_message(
        self,
        session_id: str | None,
        message: AgentMessage | ToolResultMessage,
        *,
        tool_name: str | None = None,
        finish_reason: str | None = None,
    ) -> None:
        if self.session_store is None or not session_id:
            return
        tool_calls = [tc.model_dump(mode="json") for tc in message.tool_calls]
        self.session_store.append_message(
            session_id=session_id,
            role=message.role,
            content=self._message_content_text(message.content),
            tool_name=tool_name,
            tool_call_id=message.tool_call_id,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            metadata=message.metadata,
        )

    @staticmethod
    def _message_content_text(content: str | list[dict[str, Any]] | None) -> str | None:
        if content is None or isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
