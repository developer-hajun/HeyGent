"""ToolSchemaMixin: provider tool 스키마 변환·이름 매핑."""
from __future__ import annotations

import re
from typing import Any


class ToolSchemaMixin:
    """provider가 허용하는 tool name 변환과 역방향 map 관리."""

    @classmethod
    def _provider_tool_schemas(cls, available_tools: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """provider가 허용하는 tool name으로 변환하고 runtime 이름으로 되돌릴 map을 만든다."""
        schemas: list[dict[str, Any]] = []
        name_map: dict[str, str] = {}
        used_names: set[str] = set()
        for tool in available_tools:
            schema = tool.get("schema")
            if isinstance(schema, dict):
                function_schema = dict(schema)
                runtime_name = str(function_schema.get("name") or "").strip()
                provider_name = cls._unique_provider_tool_name(runtime_name, used_names)
                used_names.add(provider_name)
                if provider_name != runtime_name:
                    description = str(function_schema.get("description") or "").strip()
                    suffix = f"Runtime tool name: {runtime_name}."
                    function_schema["description"] = f"{description}\n{suffix}" if description else suffix
                function_schema["name"] = provider_name
                name_map[provider_name] = runtime_name or provider_name
                schemas.append({"type": "function", "function": function_schema})
        return schemas, name_map

    @classmethod
    def _unique_provider_tool_name(cls, runtime_name: str, used_names: set[str]) -> str:
        base_name = cls._safe_provider_tool_name(runtime_name)
        if base_name not in used_names:
            return base_name
        next_index = 2
        while f"{base_name}_{next_index}" in used_names:
            next_index += 1
        return f"{base_name}_{next_index}"

    @staticmethod
    def _safe_provider_tool_name(runtime_name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", str(runtime_name or "").strip())
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        return safe_name or "tool"

    @staticmethod
    def _runtime_tool_name(provider_tool_name: str, provider_tool_name_map: dict[str, str]) -> str:
        return provider_tool_name_map.get(provider_tool_name, provider_tool_name)

    @staticmethod
    def _provider_prompt_tools(
        available_tools: list[dict[str, Any]],
        provider_tool_name_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        runtime_to_provider_name = {
            runtime_name: provider_name
            for provider_name, runtime_name in provider_tool_name_map.items()
        }
        prompt_tools: list[dict[str, Any]] = []
        for tool in available_tools:
            item = dict(tool)
            runtime_name = str(item.get("name") or "").strip()
            provider_name = runtime_to_provider_name.get(runtime_name, runtime_name)
            if provider_name != runtime_name:
                summary = str(item.get("summary") or "").strip()
                item["summary"] = f"{summary} runtime name: {runtime_name}".strip()
            item["name"] = provider_name
            prompt_tools.append(item)
        return prompt_tools
