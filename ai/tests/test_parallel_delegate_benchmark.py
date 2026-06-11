"""병렬 vs 직렬 delegate 실행 성능 비교 벤치마크.

실제 worker 지연 시간을 시뮬레이션해서 병렬 실행의 실제 절감 효과를 측정한다.
"""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopHandler
from app.domain.orchestration.agent.tool_guard import ToolGuard


# ────────────────────────────────── shared fakes ──────────────────────────────


class FakeToolCall:
    def __init__(self, call_id: str, name: str, args: dict | None = None) -> None:
        self.id = call_id
        self.name = name
        self.arguments = args or {}


class FakeToolRuntime:
    runtime_context: dict = {}

    def run_call(self, *, name: str, args: dict, enabled_toolsets=None) -> dict[str, Any]:
        return {
            "ok": True,
            "child_session": {
                "goal": args.get("goal", "task"),
                "metadata": {"profile_key": "worker.default"},
            },
        }


class FakeCircuit:
    def pre_call_decision(self, *, tool_name, args):
        return SimpleNamespace(action="allow", record=None, should_abort=False)

    def record_result(self, *, tool_name, args, result):
        pass


def _make_handler() -> ToolCallingLoopHandler:
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
        tool_runtime=FakeToolRuntime(),
        tool_catalog=FakeCatalog(),
        tool_guard=ToolGuard(),
    )


async def _run_parallel(
    tool_calls: list[FakeToolCall],
    worker_delay: float,
) -> tuple[float, list[dict]]:
    """_try_parallel_delegate_execution을 사용하는 병렬 경로."""
    handler = _make_handler()
    all_tool_results: list[dict] = []
    task = SimpleNamespace(id=None, task_run_id="task_bench", input_payload={})
    executor = _make_executor(worker_delay)

    first_accepted = {"ok": True, "child_session": {"goal": tool_calls[0].arguments.get("goal", ""), "metadata": {"profile_key": "worker.default"}}}

    started = time.perf_counter()
    await handler._try_parallel_delegate_execution(
        tool_call=tool_calls[0],
        tool_call_index=0,
        accepted_result=first_accepted,
        all_tool_calls=tool_calls,
        delegate_executor=executor,
        provider_tool_name_map={"delegate_task": "delegate_task"},
        requested_toolsets=("delegate",),
        tool_runtime=FakeToolRuntime(),
        guard_task_input={},
        failure_circuit=FakeCircuit(),
        all_tool_results=all_tool_results,
        messages=[],
        transcript_session_id=None,
        operations=[],
        operation_counters={},
        progress_sink=None,
        task=task,
        task_input={},
    )
    elapsed = time.perf_counter() - started
    return elapsed, all_tool_results


async def _run_sequential(
    tool_calls: list[FakeToolCall],
    worker_delay: float,
) -> tuple[float, list[dict]]:
    """asyncio.gather 없이 순서대로 await하는 직렬 경로."""
    executor = _make_executor(worker_delay)
    all_tool_results: list[dict] = []

    started = time.perf_counter()
    for tc in tool_calls:
        accepted = {"ok": True, "child_session": {"goal": tc.arguments.get("goal", ""), "metadata": {"profile_key": "worker.default"}}}
        result = await ToolCallingLoopHandler._execute_delegate_tool_result(
            delegate_executor=executor,
            tool_call_id=tc.id,
            args=tc.arguments,
            accepted_result=accepted,
        )
        all_tool_results.append({"tool_call_id": tc.id, "result": result})
    elapsed = time.perf_counter() - started
    return elapsed, all_tool_results


def _make_executor(delay: float):
    async def executor(*, child_session, tool_call_id, args, accepted_result):
        await asyncio.sleep(delay)
        return {"ok": True, "content": f"완료: {child_session.get('goal')}", "childStatus": "COMPLETED"}
    return executor


def _make_calls(n: int, delay_label: str = "") -> list[FakeToolCall]:
    return [FakeToolCall(f"call_{i+1}", "delegate_task", {"goal": f"작업_{i+1}{delay_label}"}) for i in range(n)]


# ────────────────────────────────── benchmark tests ──────────────────────────


WORKER_DELAY = 0.15   # worker 1개당 가상 실행 시간 (초)
REPEAT = 3            # 각 케이스를 N번 반복해 평균 측정


def _avg_elapsed(times: list[float]) -> float:
    return sum(times) / len(times)


@pytest.mark.asyncio
async def test_benchmark_2_workers():
    n = 2
    calls = _make_calls(n)

    seq_times, par_times = [], []
    for _ in range(REPEAT):
        t, _ = await _run_sequential(calls, WORKER_DELAY)
        seq_times.append(t)
        t, _ = await _run_parallel(calls, WORKER_DELAY)
        par_times.append(t)

    seq_avg = _avg_elapsed(seq_times)
    par_avg = _avg_elapsed(par_times)
    speedup = seq_avg / par_avg
    saved_pct = (1 - par_avg / seq_avg) * 100

    print(f"\n[{n} workers @ {WORKER_DELAY*1000:.0f}ms each]")
    print(f"  직렬: {seq_avg*1000:.1f}ms  병렬: {par_avg*1000:.1f}ms  speedup: {speedup:.2f}x  절감: {saved_pct:.1f}%")

    assert speedup > 1.5, f"2 worker 병렬화 speedup이 기대 이하: {speedup:.2f}x"


@pytest.mark.asyncio
async def test_benchmark_3_workers():
    n = 3
    calls = _make_calls(n)

    seq_times, par_times = [], []
    for _ in range(REPEAT):
        t, _ = await _run_sequential(calls, WORKER_DELAY)
        seq_times.append(t)
        t, _ = await _run_parallel(calls, WORKER_DELAY)
        par_times.append(t)

    seq_avg = _avg_elapsed(seq_times)
    par_avg = _avg_elapsed(par_times)
    speedup = seq_avg / par_avg
    saved_pct = (1 - par_avg / seq_avg) * 100

    print(f"\n[{n} workers @ {WORKER_DELAY*1000:.0f}ms each]")
    print(f"  직렬: {seq_avg*1000:.1f}ms  병렬: {par_avg*1000:.1f}ms  speedup: {speedup:.2f}x  절감: {saved_pct:.1f}%")

    assert speedup > 2.0, f"3 worker 병렬화 speedup이 기대 이하: {speedup:.2f}x"


@pytest.mark.asyncio
async def test_benchmark_5_workers():
    n = 5
    calls = _make_calls(n)

    seq_times, par_times = [], []
    for _ in range(REPEAT):
        t, _ = await _run_sequential(calls, WORKER_DELAY)
        seq_times.append(t)
        t, _ = await _run_parallel(calls, WORKER_DELAY)
        par_times.append(t)

    seq_avg = _avg_elapsed(seq_times)
    par_avg = _avg_elapsed(par_times)
    speedup = seq_avg / par_avg
    saved_pct = (1 - par_avg / seq_avg) * 100

    print(f"\n[{n} workers @ {WORKER_DELAY*1000:.0f}ms each]")
    print(f"  직렬: {seq_avg*1000:.1f}ms  병렬: {par_avg*1000:.1f}ms  speedup: {speedup:.2f}x  절감: {saved_pct:.1f}%")

    assert speedup > 3.0, f"5 worker 병렬화 speedup이 기대 이하: {speedup:.2f}x"


@pytest.mark.asyncio
async def test_benchmark_result_order_preserved_under_parallel():
    """병렬 실행 중에도 결과 순서가 호출 순서와 일치하는지 확인."""
    n = 4
    calls = _make_calls(n)

    _, results = await _run_parallel(calls, worker_delay=0.02)

    assert [r["tool_call_id"] for r in results] == [f"call_{i+1}" for i in range(n)]


@pytest.mark.asyncio
async def test_benchmark_realistic_llm_worker_delay():
    """실제 LLM worker 지연(~2–5초)을 모사한 현실적 시나리오."""
    realistic_delay = 2.0   # worker 1개 = 2초
    n = 3
    calls = _make_calls(n, "_real")

    t_seq, _ = await _run_sequential(calls, realistic_delay)
    t_par, _ = await _run_parallel(calls, realistic_delay)
    speedup = t_seq / t_par
    saved_sec = t_seq - t_par

    print(f"\n[현실적 시나리오: {n} workers @ {realistic_delay:.0f}s each]")
    print(f"  직렬: {t_seq:.2f}s  병렬: {t_par:.2f}s  speedup: {speedup:.2f}x  절감: {saved_sec:.2f}s")

    assert speedup > 2.0
    assert saved_sec > realistic_delay * (n - 1) * 0.8  # 이론 절감의 80% 이상
