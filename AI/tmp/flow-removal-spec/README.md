# Flow 제거 / Hermes 채용 문서 묶음

작성일: 2026-04-22
대상: `S14P31E105/AI`

현황 갱신: 2026-04-23

- Phase 0 ~ Phase 6 기준 cutover 작업은 현재 코드에 반영 완료
- 제품 코드의 주석/docstring/UI 문구에서는 외부 레퍼런스 이름을 사용하지 않음
- 이 문서 묶음은 내부 작업 기준과 완료 상태를 기록하는 용도로 유지

이 폴더 문서는 최대 3개만 유지한다.

## 문서 구성

1. `README.md`
   - 문서 묶음 인덱스
   - 지금 읽는 파일

2. `01-core-principles.md`
   - 상위 원칙
   - 왜 `flow`를 즉시 폐기하는지
   - 왜 Hermes를 core runtime으로 사실상 그대로 채용하는지
   - `TaskRun / StepRun`을 어디에 얹는지
   - tool / skill / child spec / 폴더 구조 원칙

3. `02-cutover-plan.md`
   - 실제 절단 순서
   - Phase별 구현 계획
   - 파일별 체크리스트
   - blocker / migration / 테스트 영향

## 이 문서 묶음의 핵심 입장

- `flow`는 약화가 아니라 즉시 폐기 대상이다.
- Hermes는 "참고"보다 강한 기준 구현으로 본다.
- 가능하면 loop, tool, todo, delegate, prompt layering, child isolation은 Hermes를 그대로 복붙하는 쪽을 우선한다.
- 우리 쪽에서 추가하는 고유 레이어는 주로 `TaskRun / StepRun / Event`와 웹/IoT 시각화 상태다.
- 중간 아키텍처를 새로 만들지 않는다.

## 문서와 코드의 표현 규칙

- 이 문서 묶음은 내부 작업 기준이므로 `Hermes`라는 레퍼런스 이름을 계속 사용한다.
- 다만 실제 제품 코드의 주석, docstring, UI 문구에는 `Hermes`를 적지 않는다.
- 코드에서는 외부 레퍼런스 이름 대신 상태 전이, waiting/resume, approval, delegation 로직 자체를 한국어로 설명한다.

## 읽는 순서

1. `01-core-principles.md`
2. `02-cutover-plan.md`
