from __future__ import annotations

from copy import deepcopy
from typing import Any


# StepRun detail 은 v1 에서 별도 invocation 테이블 대신 한 곳에 모아 둔다.
# 나중에 tool / agent / llm 계층을 분리하더라도 이 구조를 기준점으로 삼을 수 있게
# 키 이름을 먼저 고정해 둔다.
DEFAULT_STEP_DETAIL: dict[str, Any] = {
    "semanticDetail": {
        # semanticKey 는 StepRun 을 어떤 의미 단위로 묶는지 나타낸다.
        # executor/step_type 이 바뀌어도 "사용자에게 설명되는 단계"를 이 값으로 계속 추적한다.
        "semanticKey": None,
        # 화면과 이벤트 로그에서 보여 줄 semantic step 이름.
        # step.title 과 유사하지만, 나중에 실행 세부가 더 쪼개져도 대표 이름으로 유지할 수 있게 분리한다.
        "semanticStep": None,
        # 이 step 이 왜 존재하는지 설명하는 한 줄 목적.
        # StepRun 을 단순 UI 카드가 아니라 의미 단위 상태로 유지하려면 목적 문장을 같이 보존해야 한다.
        "goal": None,
        # semantic step 이 어떤 lifecycle 에 있는지 기록한다.
        # WAITING/RESUME/COMPLETED 전이를 detail 안에도 남겨 두어 이벤트만으로 잃어버리지 않게 한다.
        "lifecycle": "pending",
        # semantic step 의 operational anchor 인 StepRun ID.
        # approval, waiting, resume, child linkage 가 모두 결국 이 anchor 로 되돌아오게 하기 위해 넣는다.
        "anchorStepRunId": None,
    },
    "agentDetail": {
        # 다른 agent 를 실제로 호출했는지 여부.
        # 단순 LLM 호출과 agent orchestration 을 구분하려고 필요하다.
        "called": False,
        # 호출한 agent 의 식별자.
        # 어떤 agent 에 위임됐는지 추적해야 디버깅과 상세 화면 연결이 가능하다.
        "agentId": None,
        # agent 호출이 별도 child task 를 만들었다면 그 TaskRun ID.
        # 부모 step 에서 자식 task 로 이어지는 관계를 복원하려고 저장한다.
        "childTaskRunId": None,
        # child agent 가 남긴 한 줄 요약.
        # parent step 이 child 전체 로그를 열지 않아도 delegation 결과를 바로 보여 주기 위해 둔다.
        "summary": None,
        # child agent 의 최종 상태.
        # parent step 이 linkage 만 보고도 child 성공/실패/대기를 바로 판단할 수 있게 남긴다.
        "status": None,
    },
    "toolDetail": {
        # 사용한 tool 이름 목록.
        # 한 step 안에서 어떤 외부 도구를 건드렸는지 빠르게 파악할 수 있다.
        "toolNames": [],
        # 가장 핵심적으로 사용한 대표 tool 이름.
        # 목록이 길어질 때 UI 한 줄 요약용으로 쓰기 좋다.
        "primaryTool": None,
    },
    "llmDetail": {
        # 사용한 모델명.
        # 결과 품질/비용/재현성 이슈가 생겼을 때 모델 단위 추적이 필요하다.
        "model": None,
        # 해당 step 에서 LLM 을 몇 번 호출했는지 카운트.
        # 재시도나 다중 호출 여부를 파악해 비용/지연 분석에 쓴다.
        "callCount": 0,
    },
    "approvalDetail": {
        # 이 step 이 approval lifecycle 에 실제로 들어갔는지 여부.
        # WAITING step 중에서도 사용자 승인 기준으로 멈춘 것인지 구분해야 resume 정책을 단순하게 유지할 수 있다.
        "approvalRequested": False,
        # 현재 step 에 연결된 approval 식별자.
        # approval.step_run_id 와 함께 exact resume 를 복원하는 운영 기준점이다.
        "approvalId": None,
        # 어떤 이유로 승인을 요청했는지 저장한다.
        # StepRun 단독 조회만으로도 왜 멈췄는지 파악할 수 있어야 해서 request payload 를 복제 보관한다.
        "request": None,
        # 승인 응답 payload.
        # resume 가 끝난 뒤에도 어떤 입력으로 재개되었는지 이 step 에서 바로 볼 수 있게 남긴다.
        "response": None,
    },
}


def build_default_step_detail() -> dict[str, Any]:
    """StepRun 이 기본적으로 가져야 하는 detail 구조를 만든다.

    deepcopy 를 쓰는 이유는 dataclass default 로 같은 dict 인스턴스가 재사용되면
    다른 step 의 detail 이 섞일 수 있기 때문이다.
    """

    return deepcopy(DEFAULT_STEP_DETAIL)


def build_semantic_step_detail(
    *,
    step_run_id: str,
    semantic_key: str,
    semantic_step: str,
    semantic_goal: str,
    lifecycle: str,
) -> dict[str, Any]:
    """semantic step + operational anchor 메타데이터를 만든다.

    StepRun 은 지금 단계에서 UI 카드가 아니라, waiting/resume/approval 를 묶는 기준점이다.
    그래서 semantic 이름과 goal, 그리고 exact anchor 인 step_run_id 를 항상 같이 움직이게 한다.
    """

    return {
        "semanticDetail": {
            "semanticKey": semantic_key,
            "semanticStep": semantic_step,
            "goal": semantic_goal,
            "lifecycle": lifecycle,
            "anchorStepRunId": step_run_id,
        }
    }


def build_approval_detail(
    *,
    approval_requested: bool,
    approval_id: str | None,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """approval lifecycle 메타데이터 patch 를 만든다."""

    detail: dict[str, Any] = {
        "approvalRequested": approval_requested,
        "approvalId": approval_id,
    }
    if request_payload is not None:
        detail["request"] = request_payload
    if response_payload is not None:
        detail["response"] = response_payload
    return {
        "approvalDetail": detail
    }


def merge_step_detail(current: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
    """StepRun detail 에 부분 patch 를 합친다.

    v1 에서는 detailJson 을 StepRun 아래에 보관하기 때문에,
    loop 실행 중 계산된 일부 정보만 덮어쓸 수 있게 얕은-중첩 merge 를 제공한다.
    """

    merged = build_default_step_detail()
    for source in [current or {}, patch or {}]:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
    return merged
