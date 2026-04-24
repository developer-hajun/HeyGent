# 협업 문서 안내

`docs`는 AI 프로젝트의 협업 기록을 모아두는 공간입니다.
기본 단위는 "PR 생성" 또는 "공유 가치가 있는 후속 push"입니다.

## 폴더 안내

- `logs/`: 날짜와 작성자 기준 작업 로그
- `decisions/`: 장기 유지가 필요한 설계 결정
- `handoffs/`: 다음 작업자에게 넘기는 인수인계 메모

## 로그 작성 순서

1. `git config user.name` 값을 확인합니다.
2. `docs/logs/YYYY-MM-DD-day/<git-user.name>/` 폴더를 만듭니다.
3. 해당 폴더에서 다음 인덱스 파일을 만듭니다. 예: `001-오케스트레이션-정리.md`
4. `docs/AGENTS.md` 템플릿에 맞춰 PR 수준으로 요약합니다.
5. 장기 결정이 있으면 `docs/decisions/`에 별도 문서를 추가합니다.

## 예시

```text
docs/
  logs/
    2026-04-24-thu/
      theundergroundt/
        001-taskrun-steprun-정리.md
        002-provider-응답-구조-수정.md
```

세부 규칙과 템플릿은 `docs/AGENTS.md`를 기준으로 합니다.
