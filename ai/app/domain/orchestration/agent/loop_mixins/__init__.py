"""loop_mixins: ToolCallingLoopHandler 책임별 믹스인 모음.

ToolCallingLoopHandler는 아래 7개 믹스인을 상속해 단일 클래스처럼 동작한다.
모든 믹스인은 self를 통해 최상위 클래스의 속성에 접근하므로 별도 상태를 갖지 않는다.

믹스인별 책임:
  ToolSchemaMixin      - provider tool 스키마 변환·이름 매핑
  TranscriptMixin      - transcript 세션 생성·메시지 저장/복원
  ProgressMixin        - tool·model 진행 이벤트 emit
  ToolExecutorMixin    - tool call 실행·guard·circuit breaker·deferred 결과
  ModelCallMixin       - LLM 호출 (sync/async/streaming)
  OutcomeMixin         - 완료·대기·실패·차단 결과 빌드
  LoopConfigMixin      - 루프 설정 조회·런타임 컨텍스트 관리
"""

from app.domain.orchestration.agent.loop_mixins.tool_schema_mixin import ToolSchemaMixin
from app.domain.orchestration.agent.loop_mixins.transcript_mixin import TranscriptMixin
from app.domain.orchestration.agent.loop_mixins.progress_mixin import ProgressMixin
from app.domain.orchestration.agent.loop_mixins.tool_executor_mixin import ToolExecutorMixin
from app.domain.orchestration.agent.loop_mixins.model_call_mixin import ModelCallMixin
from app.domain.orchestration.agent.loop_mixins.outcome_mixin import OutcomeMixin
from app.domain.orchestration.agent.loop_mixins.loop_config_mixin import LoopConfigMixin

__all__ = [
    "LoopConfigMixin",
    "ModelCallMixin",
    "OutcomeMixin",
    "ProgressMixin",
    "ToolExecutorMixin",
    "ToolSchemaMixin",
    "TranscriptMixin",
]
