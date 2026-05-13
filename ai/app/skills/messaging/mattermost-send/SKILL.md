---
name: mattermost-send
description: 사용자가 요청한 요약, 알림, 작업 결과를 설정된 Mattermost 채널로 전송한다.
license: MIT
metadata:
  category: messaging
  integration: mattermost
  phase: poc
---

# Mattermost Send

## What this skill does

사용자가 명시적으로 Mattermost 전송을 요청하면, 메시지를 짧고 읽기 좋게 정리한 뒤 등록된 Mattermost 채널 별칭으로 전송한다.
실제 전송은 `mattermost.send` runtime tool을 사용한다.

## When to use

- "이 회의 요약 Mattermost에 보내줘"
- "이거 mm에 보내줘"
- "백엔드 채널에 공유해줘"
- "이 작업 결과를 매터모스트 e105 채널에 올려줘"
- "방금 정리한 내용을 backend 채널로 전송해줘"

## When not to use

- 사용자가 Mattermost 설정 방법만 질문한 경우
- 사용자가 채널 전송을 명시적으로 요청하지 않은 경우
- 메시지에 토큰, webhook URL, 비밀번호, 로컬 민감 경로가 포함된 경우

## Inputs

- `message`: Mattermost에 보낼 최종 메시지
- `target`: 선택 채널 별칭. 예: `backend`, `frontend`, `e105`, `default`

사용자가 채널을 말하지 않으면 `target`을 생략한다. backend가 기본 채널로 전송한다.

## Workflow

### 1. Confirm send intent

사용자가 "보내줘", "공유해줘", "올려줘", "전송해줘"처럼 외부 채널 전송을 명시했는지 확인한다.
명시 요청이 없으면 전송하지 않는다.

### 2. Resolve target alias

사용자 문장에서 채널 표현을 찾는다.

- "백엔드 채널" -> `backend`
- "프론트엔드 채널" -> `frontend`
- "e105 채널" -> `e105`
- "mm", "Mattermost", "매터모스트"만 있고 채널 언급 없음 -> target 생략

확실하지 않은 별칭을 추측해서 만들지 않는다.

### 3. Prepare message

Mattermost에서 읽기 쉽게 짧은 Markdown으로 정리한다.
민감정보, webhook URL, API key, access token, refresh token, 비밀번호, 긴 로컬 경로는 제거한다.

### 4. Send with runtime tool

`mattermost.send` runtime tool을 호출한다.

예시:

```json
{
  "target": "backend",
  "message": "공유할 최종 메시지"
}
```

기본 채널로 보내려면 `target`을 생략한다.

```json
{
  "message": "공유할 최종 메시지"
}
```

## Done when

- `mattermost.send` 결과가 성공으로 돌아왔다
- 사용자에게 전송 대상 별칭과 성공 여부를 짧게 알렸다

## Failure modes

- 등록된 Mattermost 채널 별칭이 없는 경우
- 기본 채널이 설정되지 않은 경우
- backend 또는 Mattermost webhook 호출이 실패한 경우

실패 시 webhook URL이나 내부 토큰을 노출하지 말고, Settings > Channels에서 채널 설정을 확인하라고 안내한다.

## Security notes

- webhook URL은 대화에 반복하지 않는다.
- tool 인자로 webhook URL을 넘기지 않는다.
- 외부 채널 전송은 사용자의 명시 요청이 있을 때만 수행한다.
