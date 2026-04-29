# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- AI WebSocket first-message auth에서 backend가 사용자 JWT를 검증해 주는 내부 API 계약을 준비한다.

## 변경 요약

- `POST /api/v1/internal/auth/verify` 엔드포인트를 추가했다.
- 내부 호출자 검증용 `X-Internal-Service-Token` 헤더와 `internal.ai.service-token` 설정 키를 사용한다.
- 사용자 access token 검증, 사용자 존재 확인, 기본 scope 응답을 추가했다.
- JWT claims 파싱 책임을 `JwtProvider`로 모아 중복 파싱을 줄였다.

## 주요 파일

- `backend/src/main/java/com/ssafy/heygent/domain/auth/controller/InternalAuthVerificationController.java`
- `backend/src/main/java/com/ssafy/heygent/domain/auth/service/AuthVerificationService.java`
- `backend/src/main/java/com/ssafy/heygent/domain/auth/dto/request/AuthVerificationRequest.java`
- `backend/src/main/java/com/ssafy/heygent/domain/auth/dto/response/AuthVerificationResponse.java`
- `backend/src/main/java/com/ssafy/heygent/global/config/jwt/JwtProvider.java`
- `backend/src/main/java/com/ssafy/heygent/global/config/security/SecurityConfig.java`
- `backend/src/test/java/com/ssafy/heygent/domain/auth/`

## 테스트 / 확인

- `.\gradlew.bat test --tests "*AuthVerification*" --rerun-tasks`
- 환경 변수를 로컬 compose 기준으로 지정한 뒤 `.\gradlew.bat test --rerun-tasks`

## 결정 / 이슈

- 현재 workspace 도메인이 없으므로 `workspaceKey`는 `null`, `scopes`는 `["USER"]`로 반환한다.
- 실제 운영 배포에서는 내부 API가 외부 네트워크에 노출되지 않도록 네트워크 경계와 토큰 로테이션 정책이 추가로 필요하다.
- filter chain 통합 테스트는 아직 별도 보강 대상으로 남아 있다.

## 다음 단계

- AI 서버에서 backend verify API를 호출하는 client와 WebSocket first-message auth 상태 전이를 구현한다.
