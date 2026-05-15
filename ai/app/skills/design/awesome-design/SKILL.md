---
name: awesome-design
description: 제품 아이디어, 기획안, 웹사이트, 웹페이지, 화면 프로토타입, UI 코드 생성, 웹 프리뷰 요청에 DESIGN.md 컬렉션을 적용합니다. 사용자가 "디자인해줘", "화면/사이트/페이지 만들어줘", "예쁘게 잡아줘", "기획을 화면으로 보여줘", 대시보드/관리콘솔/랜딩/앱/정보성 웹사이트 생성처럼 구체적이거나 모호하게 요청해도 사용합니다. `design.list_presets`, `design.read_preset`, `prototype.create_artifact`로 DESIGN.md를 읽고 React 컴포넌트 프로토타입 Artifact를 생성합니다.
license: MIT
metadata:
  category: design
  phase: prototype
---

# Awesome DESIGN.md

## When to use

- 제품 아이디어를 화면으로 구체화해야 할 때
- 제품 기획 대화 중 바로 확인 가능한 프로토타입 화면이 필요할 때
- 사용자가 "디자인해줘", "화면 만들어줘", "예쁘게 만들어줘", "UI 잡아줘"처럼 모호하게 요청할 때
- 사용자가 웹사이트, 웹페이지, 사이트, 페이지, 대시보드, SaaS, 앱 화면, 랜딩 화면, 관리 콘솔, 설정 화면, 온보딩, 결제/가격표, 데이터 테이블 같은 UI 생성을 요청할 때
- 사용자가 날씨/기상예보, 리포트, 지역 정보, 조사 결과처럼 가져온 정보를 화면이나 사이트로 구성해 달라고 요청할 때
- 사용자가 텍스트 기획안, 제품 설명, 기능 목록, 고객군, 업무 플로우를 화면으로 보고 싶어 할 때
- 사용자가 기존 화면이나 생성 결과를 더 완성도 있게 다듬어 달라고 할 때
- 생성된 코드를 웹 프리뷰로 보여줘야 할 때

## How to use

1. `design.list_presets`로 사용 가능한 DESIGN.md 목록을 확인한다.
2. 사용자 요청과 가장 가까운 DESIGN.md를 고른다.
3. `design.read_preset`으로 선택한 DESIGN.md 내용을 읽는다.
4. 읽은 DESIGN.md 내용을 디자인 컨텍스트로 삼아 React 컴포넌트 파일 세트를 만든다.
5. DESIGN.md의 색상, 타이포그래피, spacing, radius, shadow, layout, 컴포넌트 규칙을 `src/styles.css`와 컴포넌트 className에 구체적으로 반영한다.
6. `write_file`, `terminal.run`, 로컬 브릿지용 파일 도구를 사용하지 않는다. 생성 결과는 반드시 `prototype.create_artifact`로 세션 Artifact에 저장한다.
7. 사용자 입력이 모호하면 가장 가까운 제품 유형과 화면 목적을 먼저 추론하고, 필요한 경우 화면 가정을 코드에 반영한다.
8. 디자인 디테일 보존이 최우선이다. 단순 placeholder보다 실제 레이아웃, 밀도, 시각 계층, 상태, 샘플 데이터를 포함한다.

## Output rule

- 사용자가 프로토타입을 요청하면 실제로 렌더링 가능한 React 프론트엔드 코드를 만든다.
- 기본 파일은 `/src/App.tsx`, `/src/main.tsx`, `/src/styles.css`를 포함한다.
- 화면이 복잡하면 `/src/components/...`로 컴포넌트를 분리한다.
- `prototype.create_artifact`의 `files`에는 파일 경로별 코드를 모두 넣고, `framework`는 `react`, `styling`은 `css` 또는 `mixed`, `entryFile`은 `/src/App.tsx`로 둔다.
- 코드 탭이나 프리뷰에서 다시 사용할 수 있도록 한 세션 안의 생성 코드는 같은 흐름으로 이어간다.
- 결과를 보고할 때는 실제 `prototype.create_artifact` 결과의 `artifactId`, `versionId`, `designPresetId`를 기준으로 말한다. 도구 호출 여부를 추측하거나, 이미 Artifact가 생성된 뒤에 스킬을 쓰지 않았다고 단정하지 않는다.
