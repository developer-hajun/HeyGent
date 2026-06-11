# 작업 로그

## 날짜

2026-04-28

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: develop
- PR: 없음

## 작업 목적

- AI, BE, FE, MOB 초기 통합 이후 로컬 임시 파일이 Git 상태에 노출되지 않도록 루트 ignore 기준을 정리한다.

## 변경 요약

- 루트 `.gitignore`를 OS, IDE, 로컬 임시 파일, 환경변수 파일 기준으로 분리했다.
- `tmp/`, `reference/`, `.idea/`, `.env` 계열 파일을 루트 공통 ignore 대상으로 추가했다.
- `.env.example`은 공유 샘플 파일로 추적 가능하도록 예외 처리했다.

## 주요 파일

- `.gitignore`
- `docs/logs/2026-04-28-tue/전희수/001-root-gitignore-local-files.md`

## 테스트 / 확인

- `git check-ignore -v tmp reference .env .env.example`로 ignore 적용을 확인했다.
- `git ls-files tmp reference` 출력이 없는 것을 확인했다.

## 결정 / 이슈

- `frontend/.vscode/settings.json`이 이미 팀 설정으로 추적 중이므로 루트에서 `.vscode/` 전체 ignore는 적용하지 않았다.
- 배포 설정 자체는 아직 루트 Compose, CI/CD, 환경변수 분리 기준이 추가되지 않았다.

## 다음 단계

- 루트 배포 구성 파일과 서비스별 환경변수 예시를 정리한다.
- GitLab CI에서 서비스 경로별 build/test/deploy job을 분리한다.
