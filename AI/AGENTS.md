# 에이전트 지침서 (AGENTS)

이 문서는 HeyGent의 `AI` 폴더에서 작업할 때의 공용 정책과 최소 구현 원칙을 정의합니다.

## 정책

- 사용자가 명시적으로 구현 또는 코드 수정을 요청하기 전까지는 파일을 수정하지 않습니다.
- 파일/코드 검색, 읽기, 분석, 구조 검토, 설계/계획 수립, 리팩터링 아이디어 제안은 항상 가능합니다.
- 코드 수정이 허용된 이후에도 변경은 최소·점진적으로 수행합니다.
- 기존 코드 스타일과 패턴을 최대한 존중합니다.
- 불필요한 설정 변경이나 범위 밖 기능 추가는 지양합니다.
- `tmp/IMPLEMENTATION_PLAN.md` 는 현재 협업용 공통 골격 문서로 보고, 구현 전에는 이 문서의 용어와 책임 분리 기준을 먼저 맞춥니다.

## 브랜치명 규칙

- 규칙: `타입/이슈키-설명`
- 예시:
  - `BE-feat/로그인-구현`
  - `BE-fix/CORS-수정`

## 커밋 메시지 규칙

- 규칙: `컴포넌트-작업타입: 설명`
- 예시:
  - `BE-feat : 로그인 API 구현`
  - `BE-fix : WebMvcConfig CORS 설정 허용`

## 레퍼런스 참고 원칙

- Hermes 실제 코드는 적극 참고할 수 있습니다.
- OpenClaw 의 구조와 코드도 적극 참고할 수 있습니다.
- 다만 특정 프로젝트의 구조를 그대로 복제하지 않습니다.
- 런타임 전제, 상태 소유권, 내부 이벤트 체계까지 통째로 가져오지 않습니다.
- 참고한 패턴은 현재 `AI` 폴더 문맥에 맞게 다시 설명하고 정리합니다.
- 참고 구현을 가져올 때는 "왜 이 구조를 채택했는지"를 주석이나 문서에 남깁니다.

---

## 서브에이전트 규칙

- `subagent depth` 는 **1**로 봅니다.
- subagent 가 또 다른 subagent 를 생성하는 구조는 기본 전제로 두지 않습니다.
- 상위 레벨에서 여러 개의 병렬 세션을 만드는 구조는 허용합니다.

---

## 용어 고정

아래 용어는 코드와 문서에서 그대로 사용합니다.

- `TaskRun`
- `StepRun`
- `Orchestrator`
- `Task Engine`
- `Model Provider`

코드 상의 기본 이름은 유지하고, 필요한 경우 한글 설명은 주석이나 문서에서 보완합니다.

---

## 구현 원칙

- 큰 파일 하나에 모든 코드를 몰아넣지 않습니다.
- 모델 호출은 `Model Provider` 레이어를 통해서만 수행합니다.
- 상태 전이 로직에는 한글 주석을 작성합니다.
- 전반적으로 한글 주석을 충분히 작성합니다.
- `subagent depth = 1` 전제를 유지합니다.
- 현재 단계에서는 완성형 제품 아키텍처를 한 번에 확정하려 하지 않고, 백본 검증에 필요한 최소 구조부터 구현합니다.
- provider / orchestration / execution 책임이 섞이지 않게 유지합니다.

---

## 권장 폴더 구조

로컬 전용 `tmp/` 와 임시 DB 파일은 구조 표기에서 제외합니다.

```text
AI/
  AGENTS.md                           # 이 폴더에서 작업할 때 따를 정책과 최소 구현 원칙 문서
  pyproject.toml                      # Python 의존성, 실행, 테스트 설정 파일
  .env                                # 로컬 실행 환경 변수 파일
  .env.example                        # 환경 변수 예시 파일

  app/                                # 실제 애플리케이션 코드 루트
    main.py                           # FastAPI 애플리케이션 진입점
    cli.py                            # 로컬 테스트용 CLI 진입점

    api/                              # HTTP / WebSocket 진입 계층
      deps/                           # 라우터 공통 의존성 주입 모음
        task_context.py               # task 서비스와 요청 컨텍스트 준비
        provider_context.py           # provider 조회와 주입 준비
      http/                           # REST 엔드포인트 모음
        health.py                     # 서버 상태 확인 엔드포인트
        tasks.py                      # TaskRun 생성, 조회, 취소 엔드포인트
        providers.py                  # provider 상태 확인 또는 선택 관련 엔드포인트
        flows.py                      # 테스트용 플로우 실행 엔드포인트
      ws/                             # WebSocket 진입점 모음
        gateway.py                    # WebSocket 연결 시작점
        subscriptions.py              # task 구독과 이벤트 라우팅 처리

    core/                             # 전역 공통 설정, 예외, 유틸 영역
      config.py                       # 설정 로드와 환경 변수 처리
      logger.py                       # 로깅 설정
      enums.py                        # 공통 enum 정의
      exceptions.py                   # 공통 예외 정의
      time.py                         # 시간 처리 유틸
      utils/                          # 범용 보조 유틸 모음
        ids.py                        # ID 생성 유틸
        json.py                       # JSON 직렬화 보조 유틸

    contracts/                        # 외부와 맞출 요청/응답/이벤트 계약 모델
      common/                         # 여러 계약에서 공통으로 쓰는 베이스 모델
        base.py                       # 공통 베이스 스키마
        pagination.py                 # 목록 응답용 페이지네이션 구조
      task/                           # TaskRun / StepRun 관련 계약 모델
        task_request.py               # 작업 생성 요청 스키마
        task_response.py              # 작업 조회 응답 스키마
        task_status.py                # TaskRun 상태 정의
        step_status.py                # StepRun 상태 정의
      event/                          # 이벤트 전달 계약 모델
        task_events.py                # task 이벤트 페이로드 정의
        ws_events.py                  # WebSocket 이벤트 포맷 정의
      provider/                       # 모델 프로바이더 입출력 계약 모델
        provider_request.py           # provider 호출 입력 스키마
        provider_response.py          # provider 호출 출력 스키마

    domain/                           # 실제 비즈니스 로직 중심 계층
      tasks/                          # TaskRun / StepRun 기본 관리 로직
        models.py                     # task 도메인 모델 정의
        schemas.py                    # task 내부 스키마 정의
        service.py                    # task 생성/조회/갱신 서비스
        repository.py                 # task 저장소 추상화 또는 구현 연결
        events.py                     # task 관련 내부 이벤트 생성
      orchestration/                  # 요청 분류와 StepRun 계획 계층
        orchestrator.py               # 전체 오케스트레이션 진입 로직
        planner.py                    # 단계 계획 생성 로직
        flow_router.py                # 요청별 플로우 선택 로직
      execution/                      # 실제 실행과 상태 전이 계층
        task_engine.py                # TaskRun 실행 엔진
        step_executor.py              # StepRun 개별 실행기
        state_machine.py              # 상태 전이 규칙 정의
      providers/                      # 모델 프로바이더 추상화와 구현체
        base.py                       # provider 공통 인터페이스
        registry.py                   # provider 등록/조회 관리
        openai_oauth.py               # GPT-5.4 OAuth 기반 provider 구현체
      integrations/                   # Notion 등 외부 서비스 연동 코드
        notion_client.py              # Notion API 클라이언트
        notion_mapper.py              # Notion 데이터 변환 로직
      gateway/                        # 연결 상태와 이벤트 브로드캐스트 관리
        ws_manager.py                 # WebSocket 연결 목록 관리
        broadcaster.py                # 이벤트 송신 처리
        session_registry.py           # 세션별 연결 상태 관리

    storage/                          # SQLite 저장 계층
      sqlite.py                       # SQLite 연결과 기본 저장 처리
      tables.py                       # 테이블 정의
      queries/                        # SQL 쿼리 분리 영역
        task_queries.py               # TaskRun 관련 쿼리
        step_queries.py               # StepRun 관련 쿼리
        event_queries.py              # 이벤트 저장/조회 쿼리

    flows/                            # 실제 실행 가능한 샘플 플로우 모음
      stub/                           # 외부 의존성 없는 테스트용 플로우
        echo_flow.py                  # 입력을 그대로 돌려주는 기본 플로우
        health_check_flow.py          # 백본 동작 확인용 간단 플로우
      notion/                         # Notion 연동 플로우 모음
        notion_page_create.py         # Notion 페이지 생성 플로우
        notion_database_append.py     # Notion 데이터베이스 append 플로우

    tests/                            # 테스트 코드 모음
      conftest.py                     # 테스트 공통 fixture 설정
      api/                            # API 계층 테스트
        test_health.py                # health endpoint 테스트
        test_tasks.py                 # task endpoint 테스트
        test_ws.py                    # WebSocket endpoint 테스트
      flows/                          # 플로우 실행 테스트
        test_stub_flow.py             # stub 플로우 테스트
        test_notion_flow.py           # Notion 플로우 테스트
      providers/                      # 모델 프로바이더 테스트
        test_openai_provider.py       # GPT-5.4 OAuth provider 테스트
      storage/                        # 저장 계층 테스트
        test_sqlite_repository.py     # SQLite 저장소 테스트
```
