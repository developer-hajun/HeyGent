"""ProgressMixin: tool·model 진행 이벤트 emit."""
from __future__ import annotations

import re
import time
from typing import Any

from app.domain.providers.model.base import AgentMessage, AgentModelResponse, ToolResultMessage


class ProgressMixin:
    """tool 실행 및 모델 호출 진행 상황을 progress_sink로 내보낸다."""

    async def _emit_tool_progress(
        self,
        *,
        progress_sink: Any,
        event_type: str,
        tool_call_id: str,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any] | None,
    ) -> None:
        if progress_sink is None:
            return
        await progress_sink(
            event_type=event_type,
            summary_message=self._tool_progress_summary(
                tool_name=tool_name, args=args, result=result
            ),
            payload=self._tool_progress_payload(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                args=args,
                result=result,
            ),
        )

    async def _emit_model_call_progress(
        self,
        *,
        progress_sink: Any,
        event_type: str,
        turn_index: int,
        model: str,
        runtime_context: dict[str, Any],
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        duration_ms: int | None = None,
        generated: AgentModelResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        if progress_sink is None:
            return
        payload: dict[str, Any] = {
            "turnIndex": turn_index,
            "model": model,
            "providerName": str(
                runtime_context.get("provider_name")
                or runtime_context.get("providerName")
                or ""
            ),
            "messageCount": len(messages),
            "toolSchemaCount": len(tools or []),
        }
        if duration_ms is not None:
            payload["durationMs"] = duration_ms
        if generated is not None:
            payload.update(
                {
                    "finishReason": generated.finish_reason,
                    "toolCallCount": len(generated.tool_calls),
                    "outputTextLength": len(str(generated.output_text or "")),
                    "visibleTextLength": len(str(generated.visible_text or "")),
                    "usage": dict(generated.usage or {}),
                }
            )
        if error is not None:
            payload["error"] = {
                "type": type(error).__name__,
                "message": str(error)[:500],
            }
        await progress_sink(
            event_type=event_type,
            summary_message=self._model_progress_summary(
                event_type=event_type,
                turn_index=turn_index,
                duration_ms=duration_ms,
                generated=generated,
            ),
            payload=payload,
        )

    @staticmethod
    async def _emit_model_progress_update(
        *,
        progress_sink: Any,
        progress_update: dict[str, Any],
        turn_index: int,
        generated: AgentModelResponse,
    ) -> None:
        if progress_sink is None:
            return
        summary = str(progress_update.get("summary") or "").strip()
        await progress_sink(
            event_type="model.progress",
            summary_message=summary or f"모델 응답 업데이트 {turn_index}",
            payload={
                "turnIndex": turn_index,
                "progressUpdate": progress_update,
                "outputTextLength": len(str(generated.output_text or "")),
            },
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))

    @staticmethod
    def _model_progress_summary(
        *,
        event_type: str,
        turn_index: int,
        duration_ms: int | None,
        generated: AgentModelResponse | None,
    ) -> str:
        if event_type == "model.started":
            return f"모델 응답 생성 {turn_index} 시작"
        if event_type == "model.failed":
            return f"모델 응답 생성 {turn_index} 실패"
        suffix = f" ({duration_ms}ms)" if duration_ms is not None else ""
        if generated is not None and generated.tool_calls:
            return f"모델 응답 생성 {turn_index} 완료: tool_calls={len(generated.tool_calls)}{suffix}"
        return f"모델 응답 생성 {turn_index} 완료{suffix}"

    @staticmethod
    def _progress_summary(progress_update: Any) -> str | None:
        if not isinstance(progress_update, dict):
            return None
        return str(progress_update.get("summary") or "").strip() or None

    @classmethod
    def _tool_progress_summary(
        cls,
        *,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any] | None,
    ) -> str:
        if tool_name == "todo":
            active_title = cls._active_todo_title(args.get("todos"))
            if active_title:
                return active_title
        if tool_name == "write_file":
            path = cls._optional_text(args.get("path")) or cls._optional_text(
                (result or {}).get("path")
            )
            return f"{path} 파일 작성" if path else "파일 작성"
        if tool_name == "read_file":
            path = cls._optional_text(args.get("path")) or cls._optional_text(
                (result or {}).get("path")
            )
            return f"{path} 파일 읽기" if path else "파일 읽기"
        if tool_name == "search_files":
            query = cls._optional_text(args.get("query")) or cls._optional_text(
                args.get("pattern")
            )
            return f"{query} 검색" if query else "파일 검색"
        if tool_name == "terminal.run":
            command = cls._terminal_command_summary(args)
            return f"{command} 실행" if command else "터미널 실행"
        if tool_name == "delegate_task":
            delegate = (
                (result or {}).get("delegate") if isinstance(result, dict) else None
            )
            summary = (
                cls._optional_text((delegate or {}).get("summary"))
                if isinstance(delegate, dict)
                else None
            )
            goal = cls._optional_text(args.get("goal"))
            if summary:
                return f"worker 결과 회수: {summary[:80]}"
            return f"{goal} worker 실행" if goal else "worker 실행"
        return f"{tool_name} 실행"

    @classmethod
    def _tool_progress_payload(
        cls,
        *,
        tool_call_id: str,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool_call_id": tool_call_id,
            "toolCallId": tool_call_id,
            "tool_name": tool_name,
            "toolName": tool_name,
            "title": cls._tool_progress_summary(tool_name=tool_name, args=args, result=result),
            "input": cls._compact_progress_value(args),
        }
        for key in ("path", "query", "pattern"):
            value = cls._optional_text(args.get(key)) or cls._optional_text(
                (result or {}).get(key)
            )
            if value:
                payload[key] = value
        if tool_name == "todo":
            todos = [item for item in args.get("todos") or [] if isinstance(item, dict)]
            payload["todos"] = [
                {
                    "id": cls._optional_text(item.get("id") or item.get("key")),
                    "content": cls._optional_text(item.get("content") or item.get("title")),
                    "status": cls._optional_text(item.get("status")),
                }
                for item in todos[:12]
            ]
        if isinstance(result, dict):
            payload["result"] = cls._compact_progress_value(result)
            if result.get("ok") is False:
                payload["ok"] = False
                error = result.get("error")
                if isinstance(error, dict):
                    payload["error"] = {
                        "code": cls._optional_text(error.get("code")),
                        "message": cls._optional_text(error.get("message")),
                    }
            for key in ("bytes_written", "lines_written", "returncode", "total_count"):
                value = result.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    payload[key] = value
        return payload

    @classmethod
    def _compact_progress_value(cls, value: Any, *, depth: int = 0) -> Any:
        """세부 기록용 tool 입출력을 너무 커지지 않게 줄이고 민감값은 가린다."""
        if depth >= 5:
            return "..."
        if isinstance(value, dict):
            compacted: dict[str, Any] = {}
            for index, (key, item) in enumerate(value.items()):
                if index >= 40:
                    compacted["..."] = "truncated"
                    break
                key_text = str(key)
                if cls._looks_sensitive_key(key_text):
                    compacted[key_text] = "[redacted]"
                else:
                    compacted[key_text] = cls._compact_progress_value(item, depth=depth + 1)
            return compacted
        if isinstance(value, list):
            compacted_items = [cls._compact_progress_value(item, depth=depth + 1) for item in value[:20]]
            if len(value) > 20:
                compacted_items.append("...")
            return compacted_items
        if isinstance(value, str):
            return cls._redact_progress_text(value[:4000] + ("..." if len(value) > 4000 else ""))
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return cls._redact_progress_text(str(value))

    @staticmethod
    def _looks_sensitive_key(key: str) -> bool:
        return bool(
            re.search(
                r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|authorization)",
                key,
            )
        )

    @staticmethod
    def _redact_progress_text(value: str) -> str:
        redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[redacted]", value)
        redacted = re.sub(
            r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", redacted
        )
        return re.sub(
            r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[^,\s]+",
            r"\1=[redacted]",
            redacted,
        )

    @classmethod
    def _active_todo_title(cls, value: Any) -> str | None:
        if not isinstance(value, list):
            return None
        for status in ("in_progress", "pending", "completed"):
            for item in value:
                if not isinstance(item, dict):
                    continue
                if str(item.get("status") or "").strip().lower() != status:
                    continue
                title = cls._optional_text(item.get("content") or item.get("title"))
                if title:
                    return title
        return None

    @classmethod
    def _terminal_command_summary(cls, args: dict[str, Any]) -> str | None:
        argv = args.get("argv")
        if isinstance(argv, list) and argv:
            text = " ".join(str(item) for item in argv[:4])
            return text[:80]
        return cls._optional_text(args.get("command"))
