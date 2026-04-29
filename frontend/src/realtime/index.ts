export {
  // createTaskRunSocket: AI WebSocket 연결, 인증, 구독, ping/pong을 다루는 client 생성 함수다.
  createTaskRunSocket,
  // parseTaskRunSocketEvent: 서버가 보낸 JSON 문자열을 안전한 이벤트 타입으로 변환한다.
  parseTaskRunSocketEvent,
  // AuthFailedEvent: 토큰 검증 실패 이벤트 타입이다.
  type AuthFailedEvent,
  // AuthOkEvent: backend 검증이 끝난 사용자 인증 성공 이벤트 타입이다.
  type AuthOkEvent,
  // AuthRequiredEvent: 인증 전에 구독 같은 메시지를 보냈을 때 받는 이벤트 타입이다.
  type AuthRequiredEvent,
  // CreateTaskRunSocketOptions: WebSocket URL, accessToken, workspaceKey를 주입하는 옵션 타입이다.
  type CreateTaskRunSocketOptions,
  // PongEvent: client ping에 대한 서버 생존 응답 타입이다.
  type PongEvent,
  // SubscribeTaskOptions: TaskRun 구독 시 lastSequence(마지막 이벤트 순번)를 넘기는 옵션 타입이다.
  type SubscribeTaskOptions,
  // SubscribedEvent: 특정 TaskRun 구독 성공 이벤트 타입이다.
  type SubscribedEvent,
  // TaskEvent: TaskRun 실행 이벤트 envelope(겉봉투) 타입이다.
  type TaskEvent,
  // TaskEventData: TaskRun 이벤트의 실제 본문 타입이다.
  type TaskEventData,
  // TaskRunSocketClient: 화면에서 사용하는 WebSocket client 객체 타입이다.
  type TaskRunSocketClient,
  // TaskRunSocketEvent: 서버에서 받을 수 있는 모든 realtime 이벤트의 합집합 타입이다.
  type TaskRunSocketEvent,
  // TaskRunSocketEventHandler: realtime 이벤트를 처리하는 콜백 타입이다.
  type TaskRunSocketEventHandler,
} from './taskRunSocket'
