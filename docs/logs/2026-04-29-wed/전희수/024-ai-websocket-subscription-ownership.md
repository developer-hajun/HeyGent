# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

WebSocket subscribe 시 추측 가능한 TaskRun ID만으로 다른 사용자의 실행 상태를 구독하지 못하도록 소유권 검증을 추가한다.

# 변경 요약

- WebSocket 인증 후 subscribe 처리에 backend 검증 결과의 user id를 전달한다.
- Redis projection snapshot이 있으면 해당 TaskRun owner를 우선 확인한다.
- projection miss 또는 TTL 만료 시 repository에서 TaskRun을 조회해 fallback 검증한다.
- TaskRun이 없으면 `subscription.denied/not_found`, 소유자가 다르면 `subscription.denied/forbidden` 응답을 보낸다.
- 허용된 구독은 기존 `latestSequence` resync 힌트를 유지한다.

# 주요 파일

- `ai/app/api/ws/gateway.py`
- `ai/app/api/ws/subscriptions.py`
- `ai/tests/api/test_gateway_ws_auth.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/api/test_gateway_ws_auth.py -q`
- `ai/.venv/Scripts/python.exe -m pytest tests -q`

# 결정, 이슈, 리스크

- 현재 검증 기준은 backend auth 결과의 user id와 TaskRun `owner_key` 일치다.
- workspace scope, product session owner 검증은 backend 계약이 더 구체화되면 추가로 확장해야 한다.

# 다음 단계

- 실제 backend JWT 검증 API와 결합한 통합 테스트 범위를 별도로 잡는다.
