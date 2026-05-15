from app.tools.runtime.local_tool_runtime import LocalToolRuntime
from app.tools.runtime.toolsets import resolve_runtime_tool_names


class DummySessionStore:
    pass


class FakePrototypeRepository:
    def __init__(self) -> None:
        self.calls = []
        self.active_artifact = None

    def create_artifact_version(self, **kwargs):
        self.calls.append(kwargs)
        self.active_artifact = {
            "artifact_id": "artifact_1",
            "version_id": "version_1",
            "session_id": kwargs["session_id"],
            "owner_key": kwargs["owner_key"],
            "title": kwargs["title"],
            "framework": kwargs["framework"],
            "styling": kwargs["styling"],
            "design_preset_id": kwargs["design_preset_id"],
            "entry_file": kwargs["entry_file"],
            "files": kwargs["files"],
            "version_number": 1,
            "summary": kwargs["summary"],
        }
        return self.active_artifact

    def get_active_artifact(self, **kwargs):
        if self.active_artifact is None:
            return None
        if self.active_artifact["session_id"] != kwargs["session_id"]:
            return None
        if self.active_artifact["owner_key"] != kwargs["owner_key"]:
            return None
        return self.active_artifact


def test_prototype_toolset_exposes_artifact_creation():
    runtime = LocalToolRuntime(
        skill_registry=object(),
        session_store=DummySessionStore(),
        prototype_repository=FakePrototypeRepository(),
    )

    definitions = runtime.list_tool_definitions(enabled_toolsets=("prototype",))

    assert [definition["name"] for definition in definitions] == [
        "prototype.create_artifact",
        "prototype.get_active_artifact",
    ]
    assert "prototype.create_artifact" in resolve_runtime_tool_names(("prototype",))
    assert "prototype.get_active_artifact" in resolve_runtime_tool_names(("prototype",))


def test_prototype_create_artifact_stores_react_files_without_bridge():
    repository = FakePrototypeRepository()
    runtime = LocalToolRuntime(
        skill_registry=object(),
        session_store=DummySessionStore(),
        prototype_repository=repository,
    ).bind_request_context(
        owner_key="42",
        runtime_context={
            "sessionId": "session_1",
            "taskRunId": "task_1",
        },
    )

    result = runtime.run_call(
        name="prototype.create_artifact",
        args={
            "title": "AI 고객지원 SaaS 대시보드",
            "framework": "react",
            "styling": "css",
            "designPresetId": "stripe",
            "entryFile": "/src/App.tsx",
            "summary": "Stripe 계열 디자인 규칙을 반영한 대시보드 프로토타입",
            "files": {
                "/src/App.tsx": "export default function App() { return <main /> }",
                "/src/styles.css": ":root { --primary: #533afd; }",
            },
        },
        enabled_toolsets=("prototype",),
    )

    assert result["ok"] is True
    assert result["activeArtifactId"] == "artifact_1"
    assert result["activeArtifactVersionId"] == "version_1"
    assert result["framework"] == "react"
    assert result["styling"] == "css"
    assert result["designPresetId"] == "stripe"
    assert result["previewMode"] == "sandpack"
    assert repository.calls == [
        {
            "session_id": "session_1",
            "owner_key": "42",
            "title": "AI 고객지원 SaaS 대시보드",
            "framework": "react",
            "styling": "css",
            "design_preset_id": "stripe",
            "entry_file": "/src/App.tsx",
            "files": {
                "/src/App.tsx": {"code": "export default function App() { return <main /> }"},
                "/src/styles.css": {"code": ":root { --primary: #533afd; }"},
            },
            "summary": "Stripe 계열 디자인 규칙을 반영한 대시보드 프로토타입",
            "task_run_id": "task_1",
            "prompt_message_id": None,
            "metadata": {},
        }
    ]


def test_prototype_create_artifact_requires_bound_session_and_owner():
    runtime = LocalToolRuntime(
        skill_registry=object(),
        session_store=DummySessionStore(),
        prototype_repository=FakePrototypeRepository(),
    )

    result = runtime.run_call(
        name="prototype.create_artifact",
        args={
            "title": "프로토타입",
            "files": {"/src/App.tsx": "export default function App() { return null }"},
        },
        enabled_toolsets=("prototype",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "prototype_context_required"


def test_prototype_get_active_artifact_returns_session_files_for_followup_edits():
    repository = FakePrototypeRepository()
    runtime = LocalToolRuntime(
        skill_registry=object(),
        session_store=DummySessionStore(),
        prototype_repository=repository,
    ).bind_request_context(
        owner_key="42",
        runtime_context={"sessionId": "session_1"},
    )
    runtime.run_call(
        name="prototype.create_artifact",
        args={
            "title": "대시보드",
            "files": {
                "/src/App.tsx": "export default function App() { return <main>v1</main> }",
                "/src/styles.css": "body { margin: 0; }",
            },
        },
        enabled_toolsets=("prototype",),
    )

    result = runtime.run_call(
        name="prototype.get_active_artifact",
        args={},
        enabled_toolsets=("prototype",),
    )

    assert result["ok"] is True
    assert result["artifact"]["artifactId"] == "artifact_1"
    assert result["artifact"]["files"]["/src/App.tsx"]["code"].endswith("<main>v1</main> }")
