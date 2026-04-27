# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 없음

## 작업 목적

- runtime tool의 workspace 경계, secret path 접근, terminal 출력/위험 명령 방어를 1차 보강한다.

## 변경 요약

- file tool 실행 시 모델 인자의 `workspace_root` 대신 서버가 바인딩한 workspace root를 사용하도록 보강했다.
- `.env`, SSH/AWS 계열 secret path의 직접 read/write와 검색 노출을 차단했다.
- `terminal.run`에 위험 명령 사전 차단, workspace 내부 cwd 제한, stdout/stderr 출력 cap과 truncation 표시를 추가했다.
- runtime tool result의 큰 문자열 필드를 공통 cap 처리하도록 보강했다.

## 주요 파일

- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/app/tools/file/file_tools.py`
- `AI/tests/tools/test_runtime_tools.py`
- `AI/tests/tools/test_file_runtime_tools.py`

## 테스트 / 확인

- `.venv\Scripts\python.exe -m pytest tests/tools/test_runtime_tools.py tests/tools/test_file_runtime_tools.py`
- `.venv\Scripts\python.exe -m pytest`
- 결과: 142 passed

## 결정 / 이슈

- `workspace_root`는 모델 인자를 신뢰하지 않고 runtime 생성 시점의 서버 루트 또는 환경 변수 기반 루트를 우선한다.
- shell 실행 자체 제거는 이번 범위에서 제외하고, 위험 패턴 기본 차단과 출력 제한을 우선 적용했다.

## 다음 단계

- delegate child 권한 제한은 실제 delegate runtime 연결 지점의 정책과 함께 추가 검증이 필요하다.
