from __future__ import annotations

from app.domain.capabilities.tools.contracts import TaskCapabilityExecutor
from app.domain.capabilities.tools.model.generate import ModelGenerateCapability
from app.domain.capabilities.tools.notion.database_append import NotionDatabaseAppendCapability
from app.domain.capabilities.tools.notion.page_create import NotionPageCreateCapability
from app.domain.capabilities.tools.stub.approval_wait import ApprovalWaitCapability
from app.domain.capabilities.tools.stub.delegate_echo import DelegateEchoCapability
from app.domain.capabilities.tools.stub.echo import EchoCapability


class CapabilityRegistry:
    """intent 와 capability 키를 실제 실행체에 연결한다.

    flow 제거 이후에는 더 이상 `flow_name -> route -> worker` 복원 과정을 두지 않는다.
    시작점과 재개점 모두 capability registry 를 바로 조회해서 loop 가 실행자를 잡는다.
    """

    def __init__(self, *, provider_registry, notion_client, notion_mapper) -> None:
        default_provider = provider_registry.get("openai_oauth")
        executors = [
            EchoCapability(),
            DelegateEchoCapability(),
            ApprovalWaitCapability(),
            ModelGenerateCapability(default_provider),
            NotionPageCreateCapability(notion_client, notion_mapper, default_provider),
            NotionDatabaseAppendCapability(notion_client, notion_mapper, default_provider),
        ]
        self._executors_by_key: dict[str, TaskCapabilityExecutor] = {executor.spec.executor_key: executor for executor in executors}
        self._default_entry_by_intent = {executor.spec.intent_type: executor.spec.entry_capability for executor in executors}

    def resolve(
        self,
        *,
        intent_type: str | None = None,
        entry_capability: str | None = None,
    ) -> TaskCapabilityExecutor:
        if entry_capability:
            return self.get(entry_capability)

        canonical_intent = str(intent_type or "model.generate")
        try:
            return self.get(self._default_entry_by_intent[canonical_intent])
        except KeyError as error:
            raise KeyError(canonical_intent) from error

    def get(self, executor_key: str) -> TaskCapabilityExecutor:
        try:
            return self._executors_by_key[executor_key]
        except KeyError as error:
            raise KeyError(executor_key) from error

    def list_intent_types(self) -> list[str]:
        return sorted(self._default_entry_by_intent)
