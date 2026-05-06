# AI 프론트 실테스트 결과

- 날짜: 2026-05-06
- 작성자: 전희수
- 관련 브랜치 또는 PR: 로컬 작업 브랜치
- 작업 목적: 테스트 정리 후 프론트 입력부터 AI 작업 완료, 파일 저장, StepRun 기록까지 실제 흐름을 확인한다.

## 변경 요약

- 코드 변경 없음.
- Playwright와 Browser Use로 프론트 화면 접근 및 최신 대화 반영을 확인했다.
- Postgres의 최신 task/step 기록과 로컬 파일 생성 결과를 함께 확인했다.

## 주요 파일

- `tmp/testfile/test2/pytest_fix_live_test.md`

## 테스트 또는 확인 내용

- API 상태 확인
  - `GET http://localhost:8000/ai/api/v1/health`: 정상
  - `GET http://localhost:8000/ai/api/v1/ready`: 정상, Postgres/Redis projection 활성
- Playwright 프론트 실테스트
  - `http://localhost:5173` 접속
  - 새 채팅 생성
  - 프롬프트 입력: `최근 AI 에이전트가 worker를 분리해서 쓰는 이유를 조사해줘. C:\Users\SSAFY\Desktop\PR\IDEA\S14P31E105\tmp\testfile\test2 여기에 pytest_fix_live_test.md 파일로 저장해줘`
  - 결과: 프론트 사이드바에 저장 완료 응답 반영
- 파일 확인
  - `tmp/testfile/test2/pytest_fix_live_test.md`
  - 결과: 생성됨, 약 11KB
- DB 확인
  - 최신 task: `task_e6c4f2756bb547ffb3ff131cdc8dec98`
  - durable status: `TERMINAL`
  - StepRun 2개 생성 및 완료
    - `AI 에이전트 worker 분리 사용 이유 조사`: `COMPLETED`
    - `AI 에이전트 worker 분리 이유 Markdown 문서 작성 및 저장`: `COMPLETED`
- Browser Use 확인
  - 대시보드에서 최신 대화 요약과 저장 완료 응답 확인

## 결정, 이슈, 리스크

- 이번 프론트 실테스트에서는 `로컬 브릿지 미연결` 문구가 최신 응답에 나타나지 않았다.
- AI 로그에는 Firecrawl 미설정으로 `web_extract` 본문 추출이 실패하는 로그가 남지만, hosted web search와 후속 LLM 처리로 전체 작업은 완료됐다.
- Playwright 콘솔 경고 2개가 있었다.
  - 최초 WebSocket 연결 실패 후 재연결되는 경고
  - DialogContent 접근성 description 경고
  - 이번 작업 범위가 AI 테스트 정리라 프론트 코드는 수정하지 않았다.

## 다음 단계

- 프론트 접근성 경고와 초기 WebSocket 401/재연결 경고는 별도 프론트 작업에서 정리할 수 있다.
