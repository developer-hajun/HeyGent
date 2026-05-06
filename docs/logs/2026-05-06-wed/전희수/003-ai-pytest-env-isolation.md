# AI pytest 환경 의존성 정리

- 날짜: 2026-05-06
- 작성자: 전희수
- 관련 브랜치 또는 PR: 로컬 작업 브랜치
- 작업 목적: 로컬 `.env` 값 때문에 흔들리던 AI 테스트 실패를 정리하고 `pytest -q` 통과 상태를 복구한다.

## 변경 요약

- Redis 필수 설정 검증 테스트가 실제 로컬 `.env`를 다시 읽지 않도록 설정 객체를 직접 주입하게 변경했다.
- `heygent` launcher 테스트가 로컬 `.env`의 `HEYGENT_API_BASE_URL` 값에 따라 실패하지 않도록 테스트 내부에서 기준 base URL을 고정했다.
- 불필요한 테스트 삭제 없이, 필요한 검증을 환경 독립적으로 유지하는 방향으로 정리했다.

## 주요 파일

- `ai/tests/api/test_health.py`
- `ai/tests/test_heygent.py`

## 테스트 또는 확인 내용

- `cd ai; .\.venv\Scripts\python.exe -m pytest tests\api\test_health.py tests\test_heygent.py -q`
  - 결과: `12 passed`
- `cd ai; .\.venv\Scripts\python.exe -m pytest -q`
  - 결과: `318 passed`

## 결정, 이슈, 리스크

- 기존 실패 테스트는 기능이 불필요해서 삭제할 대상은 아니었다.
- 실패 원인은 런타임 로직이 아니라 테스트가 로컬 `.env` 값과 하드코딩된 URL에 의존한 점이었다.
- 이후 `.env` 예시나 로컬 기본 URL이 바뀌어도 해당 테스트들은 테스트 내부 기준으로 재현 가능해야 한다.

## 다음 단계

- Docker/브라우저 실테스트로 프론트 입력부터 AI 작업 완료까지 흐름을 다시 확인한다.
