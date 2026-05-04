const REQUEST_ID_PREFIX = 'req'
const CLIENT_MESSAGE_ID_PREFIX = 'client_msg'
const CLIENT_COMMAND_ID_PREFIX = 'client_cmd'
const APPROVAL_RESPONSE_ID_PREFIX = 'approval_res'

const randomPart = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replaceAll('-', '')
  }

  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`
}

// requestId는 WebSocket 요청/응답 매칭 전용이다. 중복 실행 방지는 별도 idempotency key가 맡는다.
export const createRequestId = () => `${REQUEST_ID_PREFIX}_${randomPart()}`

// clientMessageId는 session.message.create의 idempotency key다.
export const createClientMessageId = () => `${CLIENT_MESSAGE_ID_PREFIX}_${randomPart()}`

// clientCommandId는 cancel/resume처럼 재전송 가능한 mutation의 idempotency key다.
export const createClientCommandId = () => `${CLIENT_COMMAND_ID_PREFIX}_${randomPart()}`

// approvalResponseId는 같은 approval 응답이 중복 처리되지 않게 하는 idempotency key다.
export const createApprovalResponseId = () => `${APPROVAL_RESPONSE_ID_PREFIX}_${randomPart()}`
