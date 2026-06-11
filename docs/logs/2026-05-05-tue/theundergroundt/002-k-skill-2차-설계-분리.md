# 작업 로그

## 시간

2026-05-05 00:28

## 사용자 요청

- k-skill 2차 설계를 1차 문서에 계속 누적할지, 별도 문서로 분리할지 판단해달라고 요청했다.
- 2차 설계 문서 생성, `skill-index` 완료 작업 기록, 2차 후보 재검증, 실제로 가져올 2차 1차분 목록 확정을 요청했다.

## 답변/작업 요약

- 1차 설계 문서는 1차 기록으로 유지하고 2차 설계를 별도 문서로 분리했다.
- `skill-index`는 2차 기반 작업으로 기록했다.
- 원본 k-skill 후보를 다시 확인해 실제 2차 1차분을 5개로 확정했다.

## 변경 사항

- 생성: `tmp/docs/k-skill-runtime-tools-2차-설계.md`
- 수정: `tmp/docs/k-skill-runtime-tools-1차-설계.md`

## 결정 또는 해석

- 실제로 가져올 2차 1차분은 `joseon-sillok-search`, `library-book-search`, `k-schoollunch-menu`, `cheap-gas-nearby`, `lotto-results`로 정했다.
- `subway-lost-property`, `public-restroom-nearby`, `household-waste-info`, `korean-spell-check`, `delivery-tracking`, `lh-notice-search`, `korean-law-search`는 추가 검증 또는 정책 기준이 필요해 이번 범위에서 제외했다.

## 다음 단계

- 확정한 5개 skill을 `ai/app/skills/k-skills/` 아래에 추가한다.
- `SkillLoader` 로딩 테스트와 helper/proxy smoke test를 확장한다.
