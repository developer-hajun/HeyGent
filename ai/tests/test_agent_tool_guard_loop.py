from types import SimpleNamespace

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopExecutor
from app.domain.orchestration.agent.tool_guard import ToolGuardDecision, ToolGuardResult
from app.domain.providers.model.base import AgentMessage, AgentModelResponse, AssistantToolCall, ToolResultMessage


def _response(*, text: str = "", tool_calls: list[AssistantToolCall] | None = None) -> AgentModelResponse:
    calls = tool_calls or []
    return AgentModelResponse(
        provider_name="fake",
        model="gpt-test",
        message=AgentMessage(role="assistant", content=text, tool_calls=calls),
        output_text=text,
        tool_calls=calls,
        finish_reason="tool_calls" if calls else "stop",
        metadata={"model": "gpt-test"},
    )


def _tool_call(call_id: str, name: str, arguments: dict) -> AssistantToolCall:
    return AssistantToolCall(id=call_id, name=name, arguments=arguments)


class FakeProvider:
    name = "fake"

    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict] = []

    def respond(self, messages, tools, model, tool_choice=None):
        self.calls.append({"messages": list(messages), "tools": tools, "model": model, "tool_choice": tool_choice})
        return next(self.responses)


class FakePromptBuilder:
    def build_agent_loop_prompt(self, **kwargs) -> str:
        return "agent loop prompt"


class FakeToolCatalog:
    def list_available_tools(self, *, requested_toolsets=None):
        return [
            {
                "name": "terminal.run",
                "summary": "terminal",
                "toolset": "terminal",
                "schema": {
                    "name": "terminal.run",
                    "description": "terminal",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]


class FakeSessionStore:
    def __init__(self) -> None:
        self.sessions_by_key: dict[str, dict] = {}
        self.messages_by_session_id: dict[str, list[dict]] = {}

    def get_latest_session_by_key(self, session_key):
        return self.sessions_by_key.get(session_key)

    def create_session(self, *, session_id, session_key, source, user_id, model, title, metadata):
        session = {
            "id": session_id,
            "session_key": session_key,
            "source": source,
            "user_id": user_id,
            "model": model,
            "title": title,
            "metadata": metadata,
        }
        self.sessions_by_key[session_key] = session
        self.messages_by_session_id[session_id] = []

    def append_message(
        self,
        *,
        session_id,
        role,
        content,
        tool_name=None,
        tool_call_id=None,
        tool_calls=None,
        finish_reason=None,
        metadata=None,
    ):
        self.messages_by_session_id.setdefault(session_id, []).append(
            {
                "role": role,
                "content": content,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "tool_calls": tool_calls or [],
                "finish_reason": finish_reason,
                "metadata": metadata or {},
            }
        )

    def list_messages(self, session_id):
        return list(self.messages_by_session_id.get(session_id, []))


class RecordingRuntime:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run_call(self, *, name, args, enabled_toolsets=None):
        self.calls.append({"name": name, "args": args, "enabled_toolsets": enabled_toolsets})
        return {"ok": True, "content": "executed"}


class StaticGuard:
    def __init__(self, result: ToolGuardResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def evaluate(self, *, task_input, tool_call_id, tool_name, arguments):
        self.calls.append(
            {
                "task_input": task_input,
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )
        return self.result


def _task(input_payload: dict | None = None):
    return SimpleNamespace(
        task_run_id="task_guard",
        session_key=None,
        owner_key="tester",
        title="guard test",
        input_payload=input_payload or {"prompt": "run"},
        todo_state={},
    )


def _session_task(input_payload: dict | None = None):
    task = _task(input_payload)
    task.session_key = "sess_guard"
    return task


def _step(wait_payload: dict | None = None):
    return SimpleNamespace(step_run_id="step_guard", wait_payload=wait_payload or {})


def _executor(provider, runtime, guard, session_store=None) -> ToolCallingLoopExecutor:
    return ToolCallingLoopExecutor(
        provider=provider,
        prompt_builder=FakePromptBuilder(),
        tool_runtime=runtime,
        tool_catalog=FakeToolCatalog(),
        session_store=session_store,
        tool_guard=guard,
    )


def test_guard_block_appends_blocked_tool_result_without_runtime_call():
    provider = FakeProvider(
        [
            _response(tool_calls=[_tool_call("call_block", "terminal_run", {"argv": ["echo", "blocked"]})]),
            _response(text="BLOCK_OBSERVED"),
        ]
    )
    runtime = RecordingRuntime()
    guard = StaticGuard(
        ToolGuardResult(
            decision=ToolGuardDecision.BLOCK,
            reason="blocked by policy",
            payload={"policy": "deny_terminal"},
        )
    )

    outcome = _executor(provider, runtime, guard).execute(task=_task(), step=_step())

    assert runtime.calls == []
    assert outcome["task_status"] == TaskStatus.COMPLETED
    blocked_result = outcome["result_payload"]["tool_results"][0]
    assert blocked_result["tool_call_id"] == "call_block"
    assert blocked_result["result"]["ok"] is False
    assert blocked_result["result"]["error"]["code"] == "tool_blocked"
    assert blocked_result["result"]["guard"]["decision"] == "BLOCK"

    replayed_tool_messages = [message for message in provider.calls[1]["messages"] if isinstance(message, ToolResultMessage)]
    assert len(replayed_tool_messages) == 1
    assert replayed_tool_messages[0].tool_call_id == "call_block"
    assert "blocked by policy" in replayed_tool_messages[0].content


def test_resume_rejected_appends_blocked_pending_tool_result_and_recontinues_loop():
    provider = FakeProvider([_response(text="DENIED_CONTINUED")])
    runtime = RecordingRuntime()
    guard = StaticGuard(ToolGuardResult(decision=ToolGuardDecision.ALLOW))
    step = _step(
        {
            "pending_tool_call_id": "call_pending",
            "pending_tool_name": "terminal.run",
            "pending_tool_arguments": {"argv": ["echo", "pending"]},
        }
    )

    outcome = _executor(provider, runtime, guard).execute(
        task=_task(),
        step=step,
        resume_payload={"approved": False, "reason": "user denied"},
    )

    assert runtime.calls == []
    assert outcome["task_status"] == TaskStatus.COMPLETED
    denied_result = outcome["result_payload"]["tool_results"][0]
    assert denied_result["tool_call_id"] == "call_pending"
    assert denied_result["result"]["ok"] is False
    assert denied_result["result"]["error"]["code"] == "tool_blocked"
    assert denied_result["result"]["guard"]["decision"] == "BLOCK"
    assert denied_result["result"]["guard"]["resume_decision"] == "rejected"

    replayed_tool_messages = [message for message in provider.calls[0]["messages"] if isinstance(message, ToolResultMessage)]
    assert len(replayed_tool_messages) == 1
    assert replayed_tool_messages[0].tool_call_id == "call_pending"


def test_approved_resume_context_allows_followup_tool_calls_after_global_approval():
    provider = FakeProvider(
        [
            _response(tool_calls=[_tool_call("call_followup", "terminal_run", {"argv": ["echo", "followup"]})]),
            _response(text="APPROVED_CONTINUED"),
        ]
    )
    runtime = RecordingRuntime()
    step = _step(
        {
            "pending_tool_call_id": "call_pending",
            "pending_tool_name": "terminal.run",
            "pending_tool_arguments": {"argv": ["echo", "pending"]},
            "approval_policy_result": {"decision": "NEEDS_APPROVAL", "source": "legacy_input_payload"},
        }
    )

    outcome = _executor(provider, runtime, guard=None).execute(
        task=_task({"prompt": "run", "approval_required": True}),
        step=step,
        resume_payload={"approved": True},
    )

    assert outcome["task_status"] == TaskStatus.COMPLETED
    assert [call["args"]["argv"] for call in runtime.calls] == [["echo", "pending"], ["echo", "followup"]]
    assert [item["tool_call_id"] for item in outcome["result_payload"]["tool_results"]] == ["call_pending", "call_followup"]


def test_resume_after_first_sibling_wait_replays_outputs_for_every_previous_tool_call():
    session_store = FakeSessionStore()
    provider = FakeProvider(
        [
            _response(
                tool_calls=[
                    _tool_call("call_wait", "terminal_run", {"argv": ["echo", "wait"]}),
                    _tool_call("call_sibling", "terminal_run", {"argv": ["echo", "sibling"]}),
                ]
            ),
            _response(text="RESUMED"),
        ]
    )
    runtime = RecordingRuntime()
    guard = StaticGuard(
        ToolGuardResult(
            decision=ToolGuardDecision.NEEDS_APPROVAL,
            reason="approval needed",
            payload={"risk": "terminal_execution"},
        )
    )
    task = _session_task()

    waiting = _executor(provider, runtime, guard, session_store=session_store).execute(task=task, step=_step())
    assert waiting["task_status"] == TaskStatus.WAITING

    step = _step(waiting["wait_payload"])
    resume_provider = FakeProvider([_response(text="RESUMED")])
    resumed = _executor(
        resume_provider,
        runtime,
        StaticGuard(ToolGuardResult(decision=ToolGuardDecision.ALLOW)),
        session_store=session_store,
    ).execute(task=task, step=step, resume_payload={"approved": True})

    replayed_tool_ids = [
        message.tool_call_id for message in resume_provider.calls[0]["messages"] if isinstance(message, ToolResultMessage)
    ]
    assert resumed["task_status"] == TaskStatus.COMPLETED
    assert replayed_tool_ids == ["call_wait", "call_sibling"]
    assert [call["args"]["argv"] for call in runtime.calls] == [["echo", "wait"]]


def test_rejected_resume_after_sibling_wait_replays_outputs_in_tool_call_order():
    session_store = FakeSessionStore()
    provider = FakeProvider(
        [
            _response(
                tool_calls=[
                    _tool_call("call_wait", "terminal_run", {"argv": ["echo", "wait"]}),
                    _tool_call("call_sibling", "terminal_run", {"argv": ["echo", "sibling"]}),
                ]
            ),
            _response(text="REJECTED_CONTINUED"),
        ]
    )
    runtime = RecordingRuntime()
    guard = StaticGuard(
        ToolGuardResult(
            decision=ToolGuardDecision.NEEDS_APPROVAL,
            reason="approval needed",
            payload={"risk": "terminal_execution"},
        )
    )
    task = _session_task()

    waiting = _executor(provider, runtime, guard, session_store=session_store).execute(task=task, step=_step())

    step = _step(waiting["wait_payload"])
    resume_provider = FakeProvider([_response(text="REJECTED_CONTINUED")])
    resumed = _executor(
        resume_provider,
        runtime,
        StaticGuard(ToolGuardResult(decision=ToolGuardDecision.ALLOW)),
        session_store=session_store,
    ).execute(task=task, step=step, resume_payload={"approved": False, "reason": "user denied"})

    replayed_tool_ids = [
        message.tool_call_id for message in resume_provider.calls[0]["messages"] if isinstance(message, ToolResultMessage)
    ]
    assert resumed["task_status"] == TaskStatus.COMPLETED
    assert runtime.calls == []
    assert replayed_tool_ids == ["call_wait", "call_sibling"]


def test_resume_after_second_sibling_wait_replays_outputs_for_every_previous_tool_call():
    session_store = FakeSessionStore()
    provider = FakeProvider(
        [
            _response(
                tool_calls=[
                    _tool_call("call_done", "terminal_run", {"argv": ["echo", "done"]}),
                    _tool_call("call_wait", "terminal_run", {"argv": ["echo", "wait"]}),
                    _tool_call("call_sibling", "terminal_run", {"argv": ["echo", "sibling"]}),
                ]
            ),
            _response(text="RESUMED"),
        ]
    )
    runtime = RecordingRuntime()

    class SecondCallWaitGuard:
        def evaluate(self, *, task_input, tool_call_id, tool_name, arguments):
            if tool_call_id == "call_wait":
                return ToolGuardResult(
                    decision=ToolGuardDecision.NEEDS_APPROVAL,
                    reason="approval needed",
                    payload={"risk": "terminal_execution"},
                )
            return ToolGuardResult(decision=ToolGuardDecision.ALLOW)

    task = _session_task()

    waiting = _executor(provider, runtime, SecondCallWaitGuard(), session_store=session_store).execute(task=task, step=_step())
    assert waiting["task_status"] == TaskStatus.WAITING

    step = _step(waiting["wait_payload"])
    resume_provider = FakeProvider([_response(text="RESUMED")])
    resumed = _executor(
        resume_provider,
        runtime,
        StaticGuard(ToolGuardResult(decision=ToolGuardDecision.ALLOW)),
        session_store=session_store,
    ).execute(task=task, step=step, resume_payload={"approved": True})

    replayed_tool_ids = [
        message.tool_call_id for message in resume_provider.calls[0]["messages"] if isinstance(message, ToolResultMessage)
    ]
    assert resumed["task_status"] == TaskStatus.COMPLETED
    assert replayed_tool_ids == ["call_done", "call_wait", "call_sibling"]
    assert [call["args"]["argv"] for call in runtime.calls] == [["echo", "done"], ["echo", "wait"]]


def test_guard_needs_approval_stores_pending_tool_snapshot_in_wait_and_approval_payload():
    provider = FakeProvider(
        [_response(tool_calls=[_tool_call("call_wait", "terminal_run", {"argv": ["echo", "wait"]})])]
    )
    runtime = RecordingRuntime()
    guard = StaticGuard(
        ToolGuardResult(
            decision=ToolGuardDecision.NEEDS_APPROVAL,
            reason="terminal requires approval",
            payload={"risk": "terminal_execution"},
        )
    )

    outcome = _executor(provider, runtime, guard).execute(task=_task(), step=_step())

    assert runtime.calls == []
    assert outcome["task_status"] == TaskStatus.WAITING
    assert outcome["step_status"] == StepStatus.WAITING
    assert outcome["wait_payload"]["pending_tool_call_id"] == "call_wait"
    assert outcome["wait_payload"]["pending_tool_name"] == "terminal.run"
    assert outcome["wait_payload"]["pending_tool_arguments"] == {"argv": ["echo", "wait"]}
    assert outcome["wait_payload"]["approval_policy_result"]["decision"] == "NEEDS_APPROVAL"
    assert outcome["wait_payload"]["approval_policy_result"]["risk"] == "terminal_execution"
    assert outcome["approval_payload"]["pending_tool_call_id"] == "call_wait"
    assert outcome["approval_payload"]["approval_policy_result"]["decision"] == "NEEDS_APPROVAL"
