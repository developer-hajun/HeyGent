from __future__ import annotations

import json
from typing import Any

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.agent.response_parser import AgentResponseParser
from app.domain.orchestration.runtime_planning.todo_state import (
    apply_tool_results_to_todo_state,
    build_task_todo_payload,
    build_todo_detail_patch,
    parse_task_todo_payload,
)


class ToolCallingLoopExecutor:
    """Run a lightweight Hermes-style tool loop over the current provider."""

    def __init__(self, provider, prompt_builder, tool_runtime, tool_catalog) -> None:
        self.provider = provider
        self.prompt_builder = prompt_builder
        self.tool_runtime = tool_runtime
        self.tool_catalog = tool_catalog
        self.response_parser = AgentResponseParser()

    def execute(self, *, task, step, resume_payload=None) -> dict[str, Any]:
        task_input = dict(task.input_payload or {})
        requested_toolsets = self._requested_toolsets(task_input)
        available_tools = self.tool_catalog.list_available_tools(requested_toolsets=requested_toolsets)
        available_tool_names = {tool["name"] for tool in available_tools}

        pending_tool_calls = self._normalize_calls(task_input.get("tool_calls"))
        all_tool_results: list[dict[str, Any]] = []
        operations: list[dict[str, Any]] = []
        last_prompt = ""
        generated = None
        llm_call_count = 0
        current_todo_state = dict(task.todo_state or {})

        if resume_payload is not None and not bool(resume_payload.get("approved", False)):
            if pending_tool_calls:
                batch_result = self._execute_tool_calls(pending_tool_calls, available_tool_names)
                all_tool_results.extend(batch_result["tool_results"])
                operations.extend(batch_result["operations"])
                current_todo_state = self._next_todo_state(current_todo_state, batch_result["tool_results"])
            return self._build_canceled_outcome(
                tool_results=all_tool_results,
                operations=operations,
                resume_payload=resume_payload,
                todo_state=current_todo_state,
            )

        max_iterations = self._max_iterations(task_input)
        final_text: str | None = None
        delegate_prompt = self._optional_text(task_input.get("delegate_prompt"))
        delegate_skill_hints = self._string_list(
            task_input.get("delegate_skill_hints") or task_input.get("skill_hints")
        )
        delegate_summary_prompt = self._optional_text(task_input.get("delegate_summary_prompt"))

        for turn_index in range(1, max_iterations + 1):
            if pending_tool_calls:
                try:
                    batch_result = self._execute_tool_calls(pending_tool_calls, available_tool_names)
                except KeyError as error:
                    return self._build_failed_outcome(
                        error_message=str(error.args[0]),
                        tool_results=all_tool_results,
                        operations=operations,
                        llm_call_count=llm_call_count,
                        model_name=self._model_name(generated, task_input),
                        todo_state=current_todo_state,
                    )
                all_tool_results.extend(batch_result["tool_results"])
                operations.extend(batch_result["operations"])
                current_todo_state = self._next_todo_state(current_todo_state, batch_result["tool_results"])
                pending_tool_calls = []

            if task_input.get("approval_required") and resume_payload is None and turn_index == 1:
                approval_reason = str(task_input.get("approval_reason") or "사용자 확인이 필요합니다")
                return self._build_waiting_outcome(
                    tool_results=all_tool_results,
                    operations=operations,
                    approval_reason=approval_reason,
                    llm_call_count=llm_call_count,
                    model_name=self._model_name(generated, task_input),
                    todo_state=current_todo_state,
                )

            last_prompt = self.prompt_builder.build_agent_loop_prompt(
                input_payload=task_input,
                available_tools=available_tools,
                tool_results=all_tool_results,
                task_todo_state=current_todo_state,
                resume_payload=resume_payload,
                turn_index=turn_index,
                max_iterations=max_iterations,
            )
            generated = self.provider.generate(
                last_prompt,
                purpose="task_loop",
                model=task_input.get("model"),
            )
            llm_call_count += 1

            operations.append(
                {
                    "key": f"llm.generate.{turn_index}",
                    "title": f"모델 응답 생성 {turn_index}",
                    "kind": "llm",
                    "status": "completed",
                    "summary": generated.output_text[:80],
                }
            )

            directive = self.response_parser.parse(generated.output_text)
            if directive.approval_required and resume_payload is None:
                approval_reason = directive.approval_reason or "사용자 확인이 필요합니다"
                return self._build_waiting_outcome(
                    tool_results=all_tool_results,
                    operations=operations,
                    approval_reason=approval_reason,
                    llm_call_count=llm_call_count,
                    model_name=self._model_name(generated, task_input),
                    todo_state=current_todo_state,
                )

            if directive.delegate_prompt:
                delegate_prompt = directive.delegate_prompt
            if directive.delegate_skill_hints:
                delegate_skill_hints = directive.delegate_skill_hints
            if directive.delegate_summary_prompt:
                delegate_summary_prompt = directive.delegate_summary_prompt

            if directive.tool_calls:
                pending_tool_calls = directive.tool_calls
                continue

            final_text = directive.final_text or generated.output_text
            break

        if final_text is None and pending_tool_calls:
            return self._build_failed_outcome(
                error_message="tool-calling loop reached max iterations before producing a final response",
                tool_results=all_tool_results,
                operations=operations,
                llm_call_count=llm_call_count,
                model_name=self._model_name(generated, task_input),
                todo_state=current_todo_state,
            )

        if final_text is None:
            final_text = generated.output_text if generated is not None else ""

        return self._build_completed_outcome(
            task_input=task_input,
            prompt=last_prompt,
            generated=generated,
            final_text=final_text,
            tool_results=all_tool_results,
            operations=operations,
            llm_call_count=llm_call_count,
            delegate_prompt=delegate_prompt,
            delegate_skill_hints=delegate_skill_hints,
            delegate_summary_prompt=delegate_summary_prompt,
            resume_payload=resume_payload,
            todo_state=current_todo_state,
        )

    def _execute_tool_calls(self, calls: list[dict[str, Any]], available_tool_names: set[str]) -> dict[str, Any]:
        tool_results: list[dict[str, Any]] = []
        operations: list[dict[str, Any]] = []
        for call in calls:
            name = str(call.get("name") or "").strip()
            args = dict(call.get("args") or {})
            if name not in available_tool_names:
                raise KeyError(f"unknown or disabled runtime tool: {name}")
            result = self.tool_runtime.run_call(name=name, args=args)
            tool_results.append({"name": name, "args": args, "result": result})
            operations.append(
                {
                    "key": name,
                    "title": name,
                    "kind": "tool",
                    "status": "completed",
                    "summary": self._tool_summary(result),
                }
            )
        return {"tool_results": tool_results, "operations": operations}

    def _build_completed_outcome(
        self,
        *,
        task_input: dict[str, Any],
        prompt: str,
        generated,
        final_text: str,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        llm_call_count: int,
        delegate_prompt: str | None,
        delegate_skill_hints: list[str],
        delegate_summary_prompt: str | None,
        resume_payload: dict[str, Any] | None,
        todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        provider_name = generated.provider_name if generated is not None else self.provider.name
        metadata = dict(generated.metadata or {}) if generated is not None else {}
        usage = dict(generated.usage or {}) if generated is not None else {}
        model_name = self._model_name(generated, task_input)
        tool_names = [str(item["name"]) for item in tool_results]
        result_payload = {
            "provider_name": provider_name,
            "text": final_text,
            "metadata": metadata,
            "tool_results": tool_results,
        }
        output_payload = {
            "prompt": prompt,
            "text": final_text,
            "usage": usage,
            "tool_results": tool_results,
            "approval_response": resume_payload or {},
        }
        detail_json = self._build_detail_json(
            tool_names=tool_names,
            llm_call_count=llm_call_count,
            model_name=model_name,
            delegated=bool(delegate_prompt),
            todo_state=todo_state,
        )
        if resume_payload is not None:
            operations.append(
                {
                    "key": "approval.resume",
                    "title": "승인 후 재개",
                    "kind": "approval",
                    "status": "completed",
                    "summary": json.dumps(resume_payload, ensure_ascii=False),
                }
            )
        outcome = {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": result_payload,
            "output_payload": output_payload,
            "detail_json": detail_json,
            "todo_state": todo_state,
            "summary_message": "tool-calling loop completed",
            "operations": operations,
        }
        if delegate_prompt:
            result_payload["delegation_requested"] = True
            output_payload["delegation_requested"] = True
            outcome["child_session"] = {
                "intent_type": "model.generate",
                "entry_executor_key": "model.generate",
                "input_payload": {
                    "prompt": delegate_prompt,
                    "skill_hints": delegate_skill_hints,
                    "model": task_input.get("model"),
                },
                "summary_prompt": delegate_summary_prompt or "child model task completed",
                "metadata": {"source": "model.generate"},
            }
        return outcome

    def _build_waiting_outcome(
        self,
        *,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        approval_reason: str,
        llm_call_count: int,
        model_name: str | None,
        todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        tool_names = [str(item["name"]) for item in tool_results]
        return {
            "task_status": TaskStatus.WAITING,
            "step_status": StepStatus.WAITING,
            "output_payload": {
                "tool_results": tool_results,
            },
            "wait_payload": {
                "reason": "approval_required",
                "approvalReason": approval_reason,
            },
            "detail_json": self._build_detail_json(
                tool_names=tool_names,
                llm_call_count=llm_call_count,
                model_name=model_name,
                delegated=False,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "summary_message": "approval required",
            "approval_payload": {
                "reason": approval_reason,
                "tool_results": tool_results,
            },
            "operations": [
                *operations,
                {
                    "key": "approval.request",
                    "title": "사용자 승인 요청",
                    "kind": "approval",
                    "status": "waiting",
                    "summary": approval_reason,
                },
            ],
        }

    def _build_canceled_outcome(
        self,
        *,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        resume_payload: dict[str, Any],
        todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        tool_names = [str(item["name"]) for item in tool_results]
        return {
            "task_status": TaskStatus.CANCELED,
            "step_status": StepStatus.CANCELED,
            "output_payload": {
                "tool_results": tool_results,
                "approval_response": resume_payload,
            },
            "detail_json": self._build_detail_json(
                tool_names=tool_names,
                llm_call_count=0,
                model_name=None,
                delegated=False,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "summary_message": "approval rejected",
            "operations": [
                *operations,
                {
                    "key": "approval.reject",
                    "title": "사용자 승인 거절",
                    "kind": "approval",
                    "status": "completed",
                    "summary": json.dumps(resume_payload, ensure_ascii=False),
                },
            ],
        }

    def _build_failed_outcome(
        self,
        *,
        error_message: str,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        llm_call_count: int,
        model_name: str | None,
        todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        tool_names = [str(item["name"]) for item in tool_results]
        return {
            "task_status": TaskStatus.FAILED,
            "step_status": StepStatus.FAILED,
            "output_payload": {
                "tool_results": tool_results,
            },
            "detail_json": self._build_detail_json(
                tool_names=tool_names,
                llm_call_count=llm_call_count,
                model_name=model_name,
                delegated=False,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "summary_message": "tool-calling loop failed",
            "error_message": error_message,
            "operations": [
                *operations,
                {
                    "key": "agent.loop",
                    "title": "Tool-calling loop",
                    "kind": "agent",
                    "status": "failed",
                    "summary": error_message,
                },
            ],
        }

    @staticmethod
    def _normalize_calls(raw_calls: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_calls, list):
            return []
        normalized: list[dict[str, Any]] = []
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue
            name = str(raw_call.get("name") or "").strip()
            if not name:
                continue
            args = raw_call.get("args")
            normalized.append({"name": name, "args": dict(args) if isinstance(args, dict) else {}})
        return normalized

    @staticmethod
    def _requested_toolsets(task_input: dict[str, Any]) -> tuple[str, ...] | None:
        raw_toolsets = task_input.get("enabled_toolsets")
        if not isinstance(raw_toolsets, list):
            return None
        normalized = tuple(str(item).strip() for item in raw_toolsets if str(item).strip())
        return normalized or None

    @staticmethod
    def _max_iterations(task_input: dict[str, Any]) -> int:
        raw_value = task_input.get("max_iterations")
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 4
        return max(1, min(value, 12))

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _model_name(generated, task_input: dict[str, Any]) -> str | None:
        if generated is not None:
            metadata = generated.metadata or {}
            for key in ("model", "resolved_model"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        model = task_input.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
        return None

    @staticmethod
    def _build_detail_json(
        *,
        tool_names: list[str],
        llm_call_count: int,
        model_name: str | None,
        delegated: bool,
        todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        unique_tool_names = list(dict.fromkeys(tool_names))
        detail_json = {
            "agentDetail": {
                "called": delegated,
                "agentId": "pending" if delegated else None,
                "childTaskRunId": None,
            },
            "toolDetail": {
                "toolNames": unique_tool_names,
                "primaryTool": unique_tool_names[0] if unique_tool_names else None,
            },
            "llmDetail": {
                "model": model_name,
                "callCount": llm_call_count,
            },
        }
        return {**detail_json, **build_todo_detail_patch(parse_task_todo_payload(todo_state))}

    @staticmethod
    def _next_todo_state(current_todo_state: dict[str, Any], tool_results: list[dict[str, Any]]) -> dict[str, Any]:
        return build_task_todo_payload(apply_tool_results_to_todo_state(current_todo_state, tool_results))

    @staticmethod
    def _tool_summary(result: dict) -> str:
        if isinstance(result, dict):
            for key in ("stdout", "body", "count", "session_id"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:80]
                if isinstance(value, int):
                    return f"{key}={value}"
            return json.dumps(result, ensure_ascii=False)[:80]
        return str(result)[:80]
