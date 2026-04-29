import { useAuthStore } from '@/store/useAuthStore'

// 인증 성공 이벤트(auth.ok): AI 서버가 backend 검증을 통과한 사용자 정보를 내려준다.
export type AuthOkEvent = {
  // type: WebSocket 이벤트 종류를 구분하는 값이다.
  type: 'auth.ok'
  // userId: backend가 JWT(로그인 토큰)에서 검증한 사용자 ID다.
  userId: string
  // workspaceKey: workspace(작업공간) 권한 검증 결과가 있을 때만 내려오는 키다.
  workspaceKey?: string
}

// 인증 실패 이벤트(auth.failed): 토큰이 없거나 backend 검증에 실패했을 때 내려온다.
export type AuthFailedEvent = {
  // type: 인증 실패 상태를 화면/상위 로직에서 분기하기 위한 값이다.
  type: 'auth.failed'
}

// 인증 필요 이벤트(auth.required): 인증 전에 구독 같은 메시지를 보내면 내려온다.
export type AuthRequiredEvent = {
  // type: 클라이언트가 먼저 auth.start를 보내야 한다는 뜻이다.
  type: 'auth.required'
}

// 구독 성공 이벤트(subscribed): 특정 TaskRun 실시간 이벤트 구독이 열린 상태다.
export type SubscribedEvent = {
  // type: 구독 성공 이벤트 종류다.
  type: 'subscribed'
  // taskRunId: 구독에 성공한 TaskRun(작업 실행) ID다.
  taskRunId: string
}

// TaskRun 이벤트 본문: AI 실행 중 발생한 step/tool/status 변화를 담는다.
export type TaskEventData = {
  // event_id: 중복 수신 제거에 쓰는 이벤트 고유 ID다.
  event_id: string
  // event_type: tool.started, task.completed 같은 실제 이벤트 이름이다.
  event_type: string
  // task_run_id: 이 이벤트가 속한 TaskRun ID다.
  task_run_id: string
  // step_run_id: 특정 StepRun(작업 단계)에 묶인 이벤트면 값이 있고, 전체 이벤트면 null이다.
  step_run_id: string | null
  // producer: 이벤트를 만든 주체(agent_loop, tool_runtime 등)를 나타낸다.
  producer: string
  // occurred_at: 서버가 이벤트를 기록한 시각이다.
  occurred_at: string
  // status: 이 이벤트 이후 상태가 있을 때만 들어간다.
  status: string | null
  // summary_message: UI에 짧게 보여줄 수 있는 요약 문구다.
  summary_message: string | null
  // payload: 이벤트별 추가 데이터이며, 화면은 모르는 필드를 무시해야 한다.
  payload: Record<string, unknown>
}

// task.event: TaskRun 실행 이벤트를 WebSocket envelope(겉봉투)로 감싼 타입이다.
export type TaskEvent = {
  // type: TaskRun 이벤트 envelope임을 나타낸다.
  type: 'task.event'
  // data: 실제 TaskRun 이벤트 본문이다.
  data: TaskEventData
}

// pong: 클라이언트 ping에 대한 서버 응답이며 연결 생존 확인에 사용한다.
export type PongEvent = {
  // type: heartbeat(연결 생존 확인) 응답 이벤트다.
  type: 'pong'
}

// 서버에서 내려올 수 있는 모든 realtime 이벤트의 합집합이다.
export type TaskRunSocketEvent =
  | AuthOkEvent
  | AuthFailedEvent
  | AuthRequiredEvent
  | SubscribedEvent
  | TaskEvent
  | PongEvent

// 이벤트 핸들러: 파싱된 realtime 이벤트를 화면/store 쪽으로 전달하는 콜백이다.
export type TaskRunSocketEventHandler = (event: TaskRunSocketEvent) => void

// TaskRun 구독 옵션: 재연결 시 마지막으로 본 sequence(순번)를 서버에 힌트로 줄 수 있다.
export type SubscribeTaskOptions = {
  // lastSequence: 클라이언트가 마지막으로 처리한 이벤트 순번이다.
  lastSequence?: number
}

// WebSocket 생성 옵션: 테스트나 화면별 연결 정보를 외부에서 주입할 때 사용한다.
export type CreateTaskRunSocketOptions = {
  // accessToken: 직접 넘기면 auth store 대신 이 토큰으로 인증한다.
  accessToken?: string | null
  // workspaceKey: 특정 workspace(작업공간) 권한 검증을 요청할 때 보내는 힌트다.
  workspaceKey?: string | null
  // url: 테스트 또는 특수 환경에서 VITE_AI_WS_BASE_URL 대신 사용할 WebSocket URL이다.
  url?: string
}

// createTaskRunSocket이 반환하는 작은 client 객체다.
export type TaskRunSocketClient = {
  // socket: 브라우저 WebSocket 원본 객체다.
  socket: WebSocket
  // isAuthenticated: auth.ok 수신 여부를 확인한다.
  isAuthenticated: () => boolean
  // onMessage: 파싱된 이벤트 구독자를 등록하고, 반환 함수로 해제한다.
  onMessage: (handler: TaskRunSocketEventHandler) => () => void
  // subscribeTask: 특정 TaskRun의 realtime 이벤트를 구독한다.
  subscribeTask: (taskRunId: string, options?: SubscribeTaskOptions) => void
  // subscribeAll: 전체 구독 요청이다. 현재 서버 정책상 거부될 수 있다.
  subscribeAll: () => void
  // ping: application-level heartbeat(애플리케이션 레벨 생존 확인)를 보낸다.
  ping: () => void
  // close: WebSocket 연결을 닫는다.
  close: (code?: number, reason?: string) => void
}

// JSON parse 직후의 원본 이벤트다. 아직 안전한 타입으로 검증되기 전 상태다.
type RawTaskRunSocketEvent = {
  // type: 서버 이벤트 종류일 수 있지만, parse 전에는 unknown으로 취급한다.
  type?: unknown
  // 나머지 필드는 이벤트 종류별로 달라서 검증 함수에서 하나씩 확인한다.
  [key: string]: unknown
}

// AI WebSocket 주소를 결정한다. 운영/로컬 차이는 env로만 분리한다.
const getAiWebSocketBaseUrl = (options: CreateTaskRunSocketOptions) => {
  // baseUrl: 테스트 주입 URL이 있으면 우선하고, 없으면 Vite 환경변수를 사용한다.
  const baseUrl = options.url ?? import.meta.env.VITE_AI_WS_BASE_URL

  if (typeof baseUrl !== 'string' || baseUrl.trim() === '') {
    throw new Error('VITE_AI_WS_BASE_URL이 설정되지 않아 AI WebSocket에 연결할 수 없습니다.')
  }

  return baseUrl
}

// 인증에 사용할 accessToken을 가져온다. 옵션 주입값이 없으면 전역 auth store를 본다.
const getAccessToken = (options: CreateTaskRunSocketOptions) => {
  if ('accessToken' in options) {
    return options.accessToken
  }
  return useAuthStore.getState().accessToken
}

// accessToken이 실제 문자열인지 확인하고, 없으면 연결 전에 명확한 에러를 낸다.
const requireAccessToken = (options: CreateTaskRunSocketOptions) => {
  // accessToken: AI 서버가 backend에 검증 요청할 JWT(로그인 토큰)다.
  const accessToken = getAccessToken(options)

  if (typeof accessToken !== 'string' || accessToken.trim() === '') {
    throw new Error('AI WebSocket 연결에 사용할 accessToken이 없습니다.')
  }

  return accessToken
}

// workspaceKey는 선택 값이라 빈 문자열이면 아예 보내지 않는다.
const getWorkspaceKey = (options: CreateTaskRunSocketOptions) => {
  if (typeof options.workspaceKey !== 'string' || options.workspaceKey.trim() === '') {
    return undefined
  }

  return options.workspaceKey
}

// WebSocket message.data 문자열을 객체로 파싱한다. 실패하면 조용히 무시할 수 있게 null을 반환한다.
const parseObject = (data: string): RawTaskRunSocketEvent | null => {
  try {
    // parsed: 외부 입력이라 바로 신뢰하지 않고 object 여부만 1차 확인한다.
    const parsed: unknown = JSON.parse(data)
    return typeof parsed === 'object' && parsed !== null ? (parsed as RawTaskRunSocketEvent) : null
  } catch {
    return null
  }
}

// 서버 원본 문자열을 화면에서 쓰기 좋은 안전한 이벤트 타입으로 변환한다.
export const parseTaskRunSocketEvent = (data: string): TaskRunSocketEvent | null => {
  // event: JSON parse는 성공했지만 필드 검증은 아직 끝나지 않은 원본 객체다.
  const event = parseObject(data)

  switch (event?.type) {
    case 'auth.ok':
      return typeof event.userId === 'string'
        ? {
            type: 'auth.ok',
            userId: event.userId,
            workspaceKey: typeof event.workspaceKey === 'string' ? event.workspaceKey : undefined,
          }
        : null
    case 'auth.failed':
      return { type: 'auth.failed' }
    case 'auth.required':
      return { type: 'auth.required' }
    case 'subscribed':
      return parseSubscribedEvent(event)
    case 'task.event':
      return isTaskEventData(event.data) ? { type: 'task.event', data: event.data } : null
    case 'pong':
      return { type: 'pong' }
    default:
      return null
  }
}

// AI TaskRun WebSocket client를 만든다. 실제 연결, 인증, 구독, heartbeat를 한 객체로 묶는다.
export const createTaskRunSocket = (
  options: CreateTaskRunSocketOptions = {},
): TaskRunSocketClient => {
  // accessToken: 연결 직후 auth.start 메시지에 담아 보낸다.
  const accessToken = requireAccessToken(options)
  // workspaceKey: backend workspace 권한 검증을 돕는 선택 힌트다.
  const workspaceKey = getWorkspaceKey(options)
  // socket: 프론트가 AI 서버에 직접 연결하는 WebSocket이다.
  const socket = new WebSocket(getAiWebSocketBaseUrl(options))
  // handlers: 화면/store에서 등록한 이벤트 구독자 목록이다.
  const handlers = new Set<TaskRunSocketEventHandler>()
  // authenticated: auth.ok 수신 후 true가 되며, 그 전에는 TaskRun 구독을 막는다.
  let authenticated = false

  socket.addEventListener('open', () => {
    // 브라우저 WebSocket 생성자는 Authorization header를 직접 지정할 수 없다.
    // 그래서 연결 직후 문서 계약의 auth.start 메시지로 accessToken을 보내 인증한다.
    socket.send(JSON.stringify({ type: 'auth.start', accessToken, workspaceKey }))
  })

  socket.addEventListener('message', (message) => {
    if (typeof message.data !== 'string') {
      return
    }

    // event: JSON 문자열을 타입 검증까지 통과한 이벤트로 변환한 결과다.
    const event = parseTaskRunSocketEvent(message.data)
    if (event === null) {
      return
    }

    if (event.type === 'auth.ok') {
      authenticated = true
    }

    handlers.forEach((handler) => handler(event))
  })

  // send: 모든 client -> server 메시지를 JSON 문자열로 직렬화해 보낸다.
  const send = (payload: Record<string, unknown>) => {
    socket.send(JSON.stringify(payload))
  }

  // requireAuthenticated: 인증 전 subscribe 호출을 client 단계에서 먼저 차단한다.
  const requireAuthenticated = () => {
    if (!authenticated) {
      throw new Error('AI WebSocket 인증 완료 전에는 구독할 수 없습니다.')
    }
  }

  return {
    socket,
    isAuthenticated: () => authenticated,
    onMessage: (handler) => {
      // handler: 파싱 완료된 이벤트를 받을 화면/store 콜백이다.
      handlers.add(handler)
      return () => handlers.delete(handler)
    },
    subscribeTask: (taskRunId, subscribeOptions = {}) => {
      requireAuthenticated()
      send({
        type: 'subscribe.task',
        taskRunId,
        lastSequence: subscribeOptions.lastSequence,
      })
    },
    subscribeAll: () => {
      requireAuthenticated()
      // 서버는 보안상 전체 구독을 거부할 수 있지만, 테스트/관리 UI를 위해 client 메서드는 남겨둔다.
      send({ type: 'subscribe.all' })
    },
    ping: () => {
      // 브라우저 JS는 native ping frame을 직접 보낼 수 없어 application-level ping을 사용한다.
      send({ type: 'ping' })
    },
    close: (code, reason) => {
      socket.close(code, reason)
    },
  }
}

// subscribed 이벤트는 서버 전환기 호환 때문에 camelCase/snake_case를 모두 받아들인다.
const parseSubscribedEvent = (event: RawTaskRunSocketEvent): SubscribedEvent | null => {
  if (typeof event.taskRunId === 'string') {
    return { type: 'subscribed', taskRunId: event.taskRunId }
  }

  if (typeof event.task_run_id === 'string') {
    return { type: 'subscribed', taskRunId: event.task_run_id }
  }

  return null
}

// task.event data가 UI에서 믿고 쓸 수 있는 최소 필드를 갖췄는지 확인한다.
const isTaskEventData = (value: unknown): value is TaskEventData => {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  // data: Partial로 좁힌 뒤 각 필드를 런타임에서 하나씩 검증한다.
  const data = value as Partial<TaskEventData>

  return (
    typeof data.event_id === 'string' &&
    typeof data.event_type === 'string' &&
    typeof data.task_run_id === 'string' &&
    (typeof data.step_run_id === 'string' || data.step_run_id === null) &&
    typeof data.producer === 'string' &&
    typeof data.occurred_at === 'string' &&
    (typeof data.status === 'string' || data.status === null) &&
    (typeof data.summary_message === 'string' || data.summary_message === null) &&
    typeof data.payload === 'object' &&
    data.payload !== null
  )
}
