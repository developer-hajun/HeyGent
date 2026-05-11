# 날짜

2026-05-11

# 작성자

전희수

# 관련 브랜치 또는 PR

로컬 작업 브랜치

# 작업 목적

브라우저에서 작업 삭제 버튼을 눌렀을 때 `DELETE` preflight 요청이 CORS 설정에 막혀 Network Error로 보이는 문제를 수정한다.

# 변경 요약

- AI HTTP CORS 기본 허용 메서드에 `PUT`, `PATCH`, `DELETE`를 추가했다.
- 삭제 요청 preflight가 기본 설정에서도 허용되는지 테스트를 추가했다.
- 환경 변수로 CORS 메서드를 명시하면 기존처럼 해당 값을 우선 사용한다.

# 주요 파일

- `ai/app/core/config.py`
- `ai/tests/api/test_cors.py`
- `ai/tests/core/test_config.py`

# 테스트 또는 확인 내용

- `python -m pytest ai\tests\api\test_cors.py ai\tests\core\test_config.py`
- Docker AI 서비스를 재빌드한 뒤 `DELETE` preflight가 200으로 응답하는 것을 확인했다.
- 임시 작업을 생성하고 preflight 후 삭제 API를 호출해 작업 목록에서 제외되는 것을 확인했다.

# 결정, 이슈, 리스크

- 작업 삭제뿐 아니라 문서/결과물 수정처럼 `PUT`, `PATCH`, `DELETE`를 쓰는 브라우저 API가 같은 문제를 겪지 않도록 기본값을 함께 정리했다.

# 다음 단계

- 프론트 화면에서 같은 작업 삭제 버튼을 다시 눌러 Network Error가 사라졌는지 확인한다.
