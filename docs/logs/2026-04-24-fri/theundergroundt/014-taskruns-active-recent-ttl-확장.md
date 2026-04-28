# 작업 로그

## 시간

2026-04-24 23:59

## 사용자 요청

- `active`에 recent TTL과 `source=active|recent` 추가
- 왜 필요한지에 대한 설명도 협업 기록에 반영

## 답변/작업 요약

- `active` API가 실행 중 작업만 보여주던 구조에서, 최근 종료 작업도 짧은 시간 동안 함께 보여주도록 확장했다.
- 각 item에 `source`를 추가해서 FE가 `active`와 `recent`를 구분할 수 있게 했다.
- 이 확장은 새로고침/재접속 직후 방금 끝난 작업이 목록에서 바로 사라져 보이는 UX 문제를 줄이기 위한 목적이다.

## 변경 사항

- `AI/app/contracts/task/task_response.py`
  - `ActiveTaskRunListItemResponse.source` 추가
- `AI/app/api/http/tasks.py`
  - recent terminal task TTL 필터 추가
  - active/recent source 분류 및 정렬 추가
  - active snapshot total_count 계산을 active+recent 기준으로 조정
- `AI/tests/api/test_tasks_runtime.py`
  - recent 포함 검증 추가
  - TTL 만료 후 recent 제외 검증 추가
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`
  - recent TTL / source 확장 근거와 현재 기준 정리

## 관련 파일

- `AI/app/api/http/tasks.py`
- `AI/app/contracts/task/task_response.py`
- `AI/tests/api/test_tasks_runtime.py`
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`

## 결정 또는 해석

- `active`는 단순 실행 중 목록이 아니라 재접속 복원용 snapshot 으로 보는 것이 맞다.
- 따라서 막 종료된 작업을 짧은 시간 포함하는 것이 FE 안정성에 유리하다.
- `source`가 없으면 FE가 실행 중 항목과 방금 끝난 항목을 같은 의미로 오해할 수 있으므로 명시 필드가 필요하다.

## 다음 단계

- FE에서 recent TTL 300초가 과한지 짧은지 확인
- 필요하면 세션/루틴 소속 정보도 active snapshot 에 추가 검토
