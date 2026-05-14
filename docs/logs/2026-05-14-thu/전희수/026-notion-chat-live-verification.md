# Notion 채팅 실사용 검증

- 날짜: 2026-05-14
- 작성자: 전희수
- 관련 브랜치 또는 PR: AI-feat/AI-Skills-impl

## 작업 목적

- 새 세션의 실제 채팅 입력에서 팀장 에이전트가 Notion 스킬을 사용해 사용자의 연결된 Notion에 결과물을 생성할 수 있는지 확인한다.
- 기본 스킬 정책을 팀장 중심으로 정리하고, 서브에이전트 템플릿은 사용자가 직접 선택한 경우에만 Notion을 갖도록 조정한다.

## 변경 요약

- 팀장 기본 스킬에 `notion`을 추가하고, 더 이상 placeholder가 아닌 `notion`을 legacy 스킬 차단 목록에서 제거했다.
- 서브에이전트 템플릿과 새 서브에이전트 폼의 기본 Notion 선택을 제거했다.
- Notion 런타임에서 정리 불가능한 workspace-level page 생성을 차단했다.
- `POST /v1/blocks/{block_id}/children` 오용을 런타임에서 차단하고, 이미 휴지통 처리된 페이지에 대한 중복 archive 오류는 성공 상태로 해석하도록 보정했다.
- Notion 스킬 문서에 부모 페이지 아래 생성, block children 메서드 규칙을 보강했다.

## 주요 파일

- `ai/app/domain/agents/templates.py`
- `ai/app/skills/integrations/notion/SKILL.md`
- `ai/app/tools/notion/notion_tool.py`
- `ai/tests/domain/test_agent_templates.py`
- `ai/tests/tools/test_notion_tool.py`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDraftForm.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/subAgentTemplates.ts`

## 테스트 또는 확인 내용

- `..\AI\.venv\Scripts\python.exe -m pytest tests\tools\test_notion_tool.py tests\domain\test_agent_templates.py tests\domain\test_capability_resolver.py -q`
  - 결과: 26 passed
- `pnpm.cmd --dir frontend build`
  - 결과: 성공
- Docker 환경에서 `GET /ai/api/v1/ready`
  - 결과: ready
- 실제 프론트 채팅 경로에서 개발용 테스트 로그인 후 Notion 페이지 생성 확인
  - 세션: `session_481042e9dd66457e8756cd1e7f62d117`
  - TaskRun: `task_7c3d229c0ff24e238f187370ead0a68e`
  - 생성 페이지 ID: `360ba9bf-a561-8174-9cb8-c544d7fa1971`
  - 생성 페이지 URL: `https://www.notion.so/AI-360ba9bfa56181749cb8c544d7fa1971`
  - 최종 확인: `in_trash: false`, 본문 block 조회 성공

## 결정, 이슈, 리스크

- 팀장만 Notion/Mattermost를 기본 보유한다.
- 다른 에이전트 템플릿에는 Notion/Mattermost를 기본 포함하지 않고, 사용자가 에이전트 설정에서 직접 추가할 수 있게 유지한다.
- workspace 최상위 page는 Notion API로 archive가 불가하므로 테스트 생성 대상에서 차단한다.
- 실제 테스트 중 생성된 최상위 테스트 페이지는 Notion API archive가 불가했으므로 수동 확인/정리 대상이 될 수 있다.

## 다음 단계

- 모델이 명령 JSON을 직접 받지 않아도 안정적으로 부모 page_id를 선택하고 생성하도록 Notion 스킬 예시를 추가 보강할 수 있다.
- 위험 작업 승인 플로우가 구현되면 Notion 쓰기/삭제류 작업에 연결한다.
