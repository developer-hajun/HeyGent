# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Orchestration-impl

# 작업 목적

agent.loop 실행 중 모델이 새 의미 단계를 다시 선언했을 때 StepRun이 첫 단계에 계속 묶이는 문제를 해결하고, 파일 도구 결과가 실제 작업 workspace에 저장되도록 한다.

# 변경 요약

- `step` 도구 진행 이벤트마다 모델이 선언한 의미 단계 목록을 다시 동기화해 새 active StepRun으로 전환하도록 수정했다.
- tool 진행 이벤트 payload에 세부 기록용 `input`/`result`를 축약 저장해 프론트에서 실제 도구 입출력을 펼쳐 볼 수 있게 했다.
- AI 컨테이너 기본 workspace를 bind mount된 작업 폴더로 맞춰 상대 경로 파일 쓰기가 호스트 작업 폴더에 반영되게 했다.
- Windows 절대 경로가 workspace를 가리키는 경우 컨테이너 workspace 상대 경로로 변환하도록 파일 도구를 보강했다.
- 프론트 StepRun 활동 패널에서 tool payload 제목을 우선 표시하고, 세부 기록에 `도구 입력`, `도구 결과`, `이벤트 payload`, `상세 데이터` 드롭다운을 추가했다.
- 파일명 안의 `step-run` 같은 일반 문자열을 내부 실행 타입으로 오인하지 않도록 사용자 표시 문구 필터를 좁혔다.

# 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/tools/file/file_tools.py`
- `frontend/src/components/taskRuns/stepRunActivityPanel/ActivityEventItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepProgressItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/activityPanelText.ts`
- `frontend/src/utils/taskRunStatusView.ts`
- `compose.yml`

# 테스트 또는 확인 내용

- `python -m pytest ai/tests -q` 결과: 288 passed
- `npm run build` 결과: 성공
- Docker compose 재빌드 및 기동 확인
- Playwright로 개발용 테스트 로그인 버튼을 직접 클릭하고 실제 채팅 요청을 전송해 StepRun 2개 분리와 `write_file` 이벤트의 입력/결과 표시를 확인했다.
- Browser Use로 개발용 테스트 로그인 버튼 클릭 후 대시보드 진입을 확인했다.
- 실제 파일 쓰기 결과가 host workspace의 테스트 파일로 생성되는 것을 확인했다.

# 결정, 이슈, 리스크

- StepRun 경계는 todo 상태가 아니라 모델이 `step` 도구로 선언한 의미 단계만 따른다.
- 실제 파일 저장은 AI 컨테이너 workspace와 host workspace 연결이 필요하므로 compose 설정을 함께 수정했다.
- tool 입출력 payload는 UI 디버깅을 위해 남기되, 길이를 제한하고 민감 키/토큰 형태는 마스킹한다.

# 다음 단계

- 실제 장문 조사 요청에서 검색/파일 도구가 여러 번 섞일 때 세부 기록 밀도가 과도하지 않은지 추가 QA한다.
