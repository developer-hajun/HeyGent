"""병렬 delegate_task 실행 최적화 테스트.

같은 LLM 응답 안의 연속된 delegate_task 호출이 asyncio.gather로 병렬 실행되는지,
그리고 결과가 호출 순서대로 all_tool_results에 쌓이는지 검증한다.
"""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopHandler
from app.domain.orchestration.agent.tool_guard import ToolGuard


# ────────────────────────────────── fakes ──────────────────────────────────


class FakeToolCall:
    def __init__(self, tool_call_id: str, name: str, args: dict | None = None) -> None:
        self.id = tool_call_id
        self.name = name
        self.arguments = args or {}


class FakeToolRuntime:
    """delegate_task accepted_result를 즉시 반환하는 동기 fake"""

    def run_call(self, *, name: str, args: dict, enabled_toolsets=None) -> dict[str, Any]:
        return {
            "ok": True,
            "child_session": {
                "goal": args.get("goal", "worker task"),
                "metadata": {"profile_key": "worker.default"},
            },
        }

    runtime_context: dict = {}


class SlowFakeToolRuntime(FakeToolRuntime):
    """각 run_call에 실제 지연을 넣어 병렬/직렬 판단용 타이밍을 측정할 수 있게 한다."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay

    def run_call(self, *, name: str, args: dict, enabled_toolsets=None) -> dict[str, Any]:
        time.sleep(self.delay)  # sync delay (to_thread로 실행되므로 블로킹이 허용됨)
        return {
            "ok": True,
            "child_session": {
                "goal": args.get("goal", "worker task"),
                "metadata": {"profile_key": "worker.default"},
            },
        }


class RecordingDelegateExecutor:
    """실행 순서와 실행 시각을 기록하는 executor. 각 worker는 delay 후 완료된다."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.calls: list[dict] = []
        self._start_times: dict[str, float] = {}
        self._end_times: dict[str, float] = {}

    async def __call__(self, *, child_session: dict, tool_call_id: str, args: dict, accepted_result: dict) -> dict:
        self._start_times[tool_call_id] = time.perf_counter()
        self.calls.append({"tool_call_id": tool_call_id, "goal": child_session.get("goal")})
        await asyncio.sleep(self.delay)
        self._end_times[tool_call_id] = time.perf_counter()
        return {
            "ok": True,
            "content": f"완료: {child_session.get('goal')}",
            "childStatus": "COMPLETED",
        }

    def workers_overlapped(self, id_a: str, id_b: str) -> bool:
        """두 worker의 실행 구간이 겹치면 병렬 실행된 것이다."""
        start_a = self._start_times.get(id_a, float("inf"))
        end_a = self._end_times.get(id_a, float("-inf"))
        start_b = self._start_times.get(id_b, float("inf"))
        return start_b < end_a and start_a < end_a


def _make_handler(tool_runtime=None, tool_guard=None) -> ToolCallingLoopHandler:
    """테스트용 최소 ToolCallingLoopHandler를 만든다."""

    class FakeProvider:
        default_model = "gpt-4o-mini"

    class FakePromptBuilder:
        def build_agent_loop_prompt(self, **_):
            return SimpleNamespace(system="sys", user="user")

    class FakeCatalog:
        default_toolsets = ("delegate",)

        def list_available_tools(self, *, requested_toolsets=None):
            return [{"name": "delegate_task", "provider_name": "delegate_task", "description": "위임"}]

    return ToolCallingLoopHandler(
        provider=FakeProvider(),
        prompt_builder=FakePromptBuilder(),
        tool_runtime=tool_runtime or FakeToolRuntime(),
        tool_catalog=FakeCatalog(),
        tool_guard=tool_guard or ToolGuard(),
    )


async def _run_parallel_helper(
    *,
    tool_calls: list[FakeToolCall],
    delegate_executor: RecordingDelegateExecutor,
    tool_runtime=None,
) -> tuple[list[dict], int | None]:
    """_try_parallel_delegate_execution를 직접 호출해 결과를 반환한다."""
    handler = _make_handler(tool_runtime=tool_runtime or FakeToolRuntime())
    all_tool_results: list[dict] = []
    messages: list = []
    operations: list = []
    operation_counters: dict = {}
    task = SimpleNamespace(id=None, task_run_id="task_test", input_payload={})

    # 첫 번째 call의 accepted_result를 미리 준비
    first_accepted = {"ok": True, "child_session": {"goal": tool_calls[0].arguments.get("goal", ""), "metadata": {"profile_key": "worker.default"}}}

    next_index = await handler._try_parallel_delegate_execution(
        tool_call=tool_calls[0],
        tool_call_index=0,
        accepted_result=first_accepted,
        all_tool_calls=tool_calls,
        delegate_executor=delegate_executor,
        provider_tool_name_map={"delegate_task": "delegate_task"},
        requested_toolsets=("delegate",),
        tool_runtime=tool_runtime or FakeToolRuntime(),
        guard_task_input={},
        failure_circuit=_make_failure_circuit(),
        all_tool_results=all_tool_results,
        messages=messages,
        transcript_session_id=None,
        operations=operations,
        operation_counters=operation_counters,
        progress_sink=None,
        task=task,
        task_input={},
    )
    return all_tool_results, next_index


def _make_failure_circuit():
    """테스트용 no-op 회로 차단기."""

    class FakeCircuit:
        def pre_call_decision(self, *, tool_name, args):
            return SimpleNamespace(action="allow", record=None, should_abort=False)

        def record_result(self, *, tool_name, args, result):
            pass

        def record_block(self, record):
            pass

    return FakeCircuit()


# ────────────────────────────────── tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_single_delegate_returns_none_for_fallback():
    """단일 delegate_task는 None을 반환해 기존 순차 경로로 fallback해야 한다."""
    executor = RecordingDelegateExecutor()
    tool_calls = [FakeToolCall("call_1", "delegate_task", {"goal": "단일 작업"})]

    _, next_index = await _run_parallel_helper(tool_calls=tool_calls, delegate_executor=executor)

    assert next_index is None, "단일 delegate는 None을 반환해 fallback 경로를 타야 한다"
    assert len(executor.calls) == 0, "fallback 경로에서 executor가 직접 호출되면 안 된다"


@pytest.mark.asyncio
async def test_two_delegates_run_in_parallel():
    """연속된 2개 delegate_task는 병렬 실행되어야 한다."""
    delay = 0.08
    executor = RecordingDelegateExecutor(delay=delay)
    tool_calls = [
        FakeToolCall("call_1", "delegate_task", {"goal": "작업 A"}),
        FakeToolCall("call_2", "delegate_task", {"goal": "작업 B"}),
    ]

    started_at = time.perf_counter()
    tool_results, next_index = await _run_parallel_helper(tool_calls=tool_calls, delegate_executor=executor)
    elapsed = time.perf_counter() - started_at

    assert next_index == 2, "두 delegate 모두 처리 후 index=2 반환해야 한다"
    assert len(tool_results) == 2, "결과가 2개여야 한다"
    # 병렬이면 delay * 2 보다 훨씬 짧아야 한다 (1.5x를 threshold로 사용)
    assert elapsed < delay * 1.5, f"병렬 실행이 아닌 것으로 보임: elapsed={elapsed:.3f}s (expected < {delay * 1.5:.3f}s)"


@pytest.mark.asyncio
async def test_three_delegates_run_in_parallel():
    """연속된 3개 delegate_task도 병렬 실행되어야 한다."""
    delay = 0.06
    executor = RecordingDelegateExecutor(delay=delay)
    tool_calls = [
        FakeToolCall("call_1", "delegate_task", {"goal": "작업 A"}),
        FakeToolCall("call_2", "delegate_task", {"goal": "작업 B"}),
        FakeToolCall("call_3", "delegate_task", {"goal": "작업 C"}),
    ]

    started_at = time.perf_counter()
    tool_results, next_index = await _run_parallel_helper(tool_calls=tool_calls, delegate_executor=executor)
    elapsed = time.perf_counter() - started_at

    assert next_index == 3
    assert len(tool_results) == 3
    assert elapsed < delay * 1.5, f"3개 병렬 실행 실패: elapsed={elapsed:.3f}s"


@pytest.mark.asyncio
async def test_results_ordered_by_original_call_order():
    """병렬 실행이어도 tool_results는 원래 호출 순서를 유지해야 한다."""
    executor = RecordingDelegateExecutor(delay=0.02)
    tool_calls = [
        FakeToolCall("call_1", "delegate_task", {"goal": "첫 번째"}),
        FakeToolCall("call_2", "delegate_task", {"goal": "두 번째"}),
        FakeToolCall("call_3", "delegate_task", {"goal": "세 번째"}),
    ]

    tool_results, _ = await _run_parallel_helper(tool_calls=tool_calls, delegate_executor=executor)

    assert tool_results[0]["tool_call_id"] == "call_1"
    assert tool_results[1]["tool_call_id"] == "call_2"
    assert tool_results[2]["tool_call_id"] == "call_3"


@pytest.mark.asyncio
async def test_non_delegate_after_delegates_not_included_in_batch():
    """delegate 뒤에 오는 비-delegate 호출은 배치에 포함되지 않아야 한다."""
    executor = RecordingDelegateExecutor(delay=0.02)
    tool_calls = [
        FakeToolCall("call_1", "delegate_task", {"goal": "A"}),
        FakeToolCall("call_2", "delegate_task", {"goal": "B"}),
        FakeToolCall("call_3", "web_search", {"query": "검색"}),
    ]

    tool_results, next_index = await _run_parallel_helper(tool_calls=tool_calls, delegate_executor=executor)

    assert next_index == 2, "web_search는 배치에 포함되지 않아 index=2 반환"
    assert len(tool_results) == 2, "delegate_task 2개 결과만 포함"
    assert all(r["name"] == "delegate_task" for r in tool_results)


@pytest.mark.asyncio
async def test_next_index_points_to_first_non_delegate():
    """반환된 next_index는 첫 번째 비-delegate 호출 위치를 가리켜야 한다."""
    executor = RecordingDelegateExecutor(delay=0.01)
    tool_calls = [
        FakeToolCall("call_1", "delegate_task", {"goal": "A"}),
        FakeToolCall("call_2", "delegate_task", {"goal": "B"}),
        FakeToolCall("call_3", "delegate_task", {"goal": "C"}),
        FakeToolCall("call_4", "file_read", {}),
        FakeToolCall("call_5", "web_search", {}),
    ]

    _, next_index = await _run_parallel_helper(tool_calls=tool_calls, delegate_executor=executor)

    assert next_index == 3, "4번째 호출(file_read)부터 기존 루프가 이어서 처리해야 한다"
