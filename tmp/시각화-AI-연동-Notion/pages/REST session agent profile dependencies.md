# REST session agent profile dependencies

Method: REST DEPENDENCY
URL: /ai/api/v1
direction: WEB to AI
백엔드: 개발 완료
BE: 전희수
프론트: 연동 필요
카테고리: 시각화
사용처: FE 초기 로딩

## 설명

시각화 화면에서 팀장/서브에이전트의 이름, 역할, 스킬, 프로필 이미지를 표시하기 위해 사용하는 기존 REST API 목록이다.

이 문서는 새 API 추가 명세가 아니다. 아래 API는 현재 코드에 이미 존재하며, 실시간 상태가 아니라 정적 표시 정보와 설정 정보를 초기 로딩하는 용도다.

## API 목록

| API | Method | 용도 |
| --- | --- | --- |
| `/agent-templates` | GET | 기본 제공 에이전트 template과 기본 `profileImage`, `visualKey` 확인 |
| `/skills` | GET | 사용자 스킬 목록 조회 |
| `/skills/{skillId}` | GET | 스킬 상세 설명 조회 |
| `/sessions/{sessionId}/agents/main` | GET | 세션 팀장 에이전트 profile 조회 |
| `/sessions/{sessionId}/agents` | GET | 세션 subagent profile 목록 조회 |
| `/sessions/{sessionId}/agents/defaults` | POST | 기본 제공 세션 subagent profile 생성 |
| `/sessions/{sessionId}/agents` | POST | 세션 에이전트 직접 생성 |
| `/sessions/{sessionId}/agents/{profileId}` | PATCH | 세션 에이전트 설정 수정 |

## 표시 정보 기준

| 정보 | 기준 API |
| --- | --- |
| 팀장 이름/역할/스킬 | `GET /sessions/{sessionId}/agents/main` |
| 서브에이전트 이름/역할/스킬 | `GET /sessions/{sessionId}/agents` |
| 스킬 표시명/설명 | `GET /skills`, `GET /skills/{skillId}` |
| 기본 제공 agent template | `GET /agent-templates` |
| 프로필 이미지 | agent profile 응답의 `profileImage` |
| 시각화 매핑 키 | agent profile/template 응답의 `visualKey` |

## Response에서 시각화가 쓰는 필드

Agent profile:

| 필드 | 설명 |
| --- | --- |
| `profileId` | 세션 에이전트 profile ID. 실시간 event의 `profileId`와 매핑 기준 |
| `sessionId` | profile이 속한 AI 세션 ID |
| `profileKey` | backend profile key. sprite key로 추론하지 않음 |
| `agentType` | 팀장/서브에이전트 구분 |
| `templateKey` | 기본 제공 template 구분 |
| `name` | 표시 이름 |
| `role` | 표시 역할 |
| `title` | 표시 제목 |
| `description` | 설명 |
| `profileImage` | 프로필 이미지 경로. 없거나 로드 실패 시 프론트는 이니셜 fallback 사용 |
| `visualKey` | sprite/시각화 매핑 키. 예: `agent06`. `profileImage` 문자열에서 추론하지 않음 |
| `skills` | agent에 설정된 skill id 목록 |

Skill:

| 필드 | 설명 |
| --- | --- |
| `skillId` | skill id |
| `name` | skill 이름 |
| `displayName` | UI 표시명 |
| `description` | UI 설명 |
| `enabled` | 사용 여부 |

## 실시간 상태와의 관계

- 위 REST API는 초기 표시 정보의 source다.
- 에이전트별 현재 실행 상태는 `task.event`, `taskRun.snapshot.get`, `taskRun.events.replay`로 판단한다.
- child TaskRun이 있으면 parent StepRun을 계속 파는 것이 아니라 `childTaskRunId` 기준으로 child TaskRun을 별도 구독/조회한다.
- 기존 LLM `session_agent_task` 경로는 WebSocket context가 없으므로 자동 구독을 보장하지 않는다. parent event에서 `childTaskRunId`를 받은 클라이언트가 직접 `subscribe.task`를 호출한다.

## 이미지 경로 기준

- CEO `profileImage`는 `/assets/agents/ceo/ceo_profile.png`를 유지한다.
- 기본 subagent template/profile `profileImage`는 `/assets/agents/agentXX/idle_front.png` 형태의 실제 프론트 asset 경로로 제공한다.
- 기존 저장값이 `/assets/agents/sub/agentXX.png`이면 REST response에서 `/assets/agents/agentXX/idle_front.png`로 정규화한다.
- 상태 매핑은 `profileImage`가 아니라 `visualKey`를 사용한다.
