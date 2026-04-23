from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


_JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


@dataclass(slots=True)
class AgentLoopDirective:
    final_text: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    approval_required: bool = False
    approval_reason: str | None = None
    delegate_prompt: str | None = None
    delegate_skill_hints: list[str] = field(default_factory=list)
    delegate_summary_prompt: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class AgentResponseParser:
    """Interpret plain text or JSON tool-loop responses from the model."""

    def parse(self, text: str) -> AgentLoopDirective:
        payload = self._parse_payload(text)
        if payload is None:
            return AgentLoopDirective(final_text=text.strip() or text)

        tool_calls = self._normalize_tool_calls(payload.get("tool_calls"))
        final_text = self._normalize_final_text(payload)
        return AgentLoopDirective(
            final_text=final_text,
            tool_calls=tool_calls,
            approval_required=bool(payload.get("approval_required")),
            approval_reason=self._normalize_optional_text(payload.get("approval_reason")),
            delegate_prompt=self._normalize_optional_text(payload.get("delegate_prompt")),
            delegate_skill_hints=self._normalize_string_list(payload.get("delegate_skill_hints")),
            delegate_summary_prompt=self._normalize_optional_text(payload.get("delegate_summary_prompt")),
            raw_payload=payload,
        )

    def _parse_payload(self, text: str) -> dict[str, Any] | None:
        stripped = text.strip()
        if not stripped:
            return None

        for candidate in self._json_candidates(stripped):
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                payload = self._decode_first_json_object(candidate)
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _json_candidates(text: str) -> list[str]:
        candidates = [text]
        match = _JSON_BLOCK_PATTERN.search(text)
        if match is not None:
            candidates.insert(0, match.group(1).strip())
        return candidates

    @staticmethod
    def _decode_first_json_object(text: str) -> dict[str, Any] | None:
        decoder = json.JSONDecoder()
        for start_index, character in enumerate(text):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(text[start_index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _normalize_tool_calls(raw_calls: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if not isinstance(raw_calls, list):
            return normalized

        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue
            name = str(raw_call.get("name") or "").strip()
            if not name:
                continue
            args = raw_call.get("args")
            normalized.append(
                {
                    "name": name,
                    "args": dict(args) if isinstance(args, dict) else {},
                }
            )
        return normalized

    @classmethod
    def _normalize_final_text(cls, payload: dict[str, Any]) -> str | None:
        for key in ("final", "final_response", "text", "message"):
            value = cls._normalize_optional_text(payload.get(key))
            if value:
                return value
        return None

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _normalize_string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]
