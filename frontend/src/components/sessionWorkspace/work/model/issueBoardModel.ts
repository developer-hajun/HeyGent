export const ISSUE_BOARD_STATUSES = [
  'backlog',
  'todo',
  'in_progress',
  'in_review',
  'blocked',
  'done',
  'cancelled',
] as const
export const ISSUE_BOARD_LABELS = [
  { id: 'ui', name: 'UI', color: '#14b8a6' },
  { id: 'api', name: 'API', color: '#3b82f6' },
  { id: 'chat', name: '채팅', color: '#8b5cf6' },
  { id: 'execution', name: '실행', color: '#f97316' },
  { id: 'realtime', name: '실시간', color: '#06b6d4' },
  { id: 'taskrun', name: 'TaskRun', color: '#6366f1' },
  { id: 'board', name: '보드', color: '#10b981' },
  { id: 'assignee', name: '담당', color: '#f59e0b' },
  { id: 'copy', name: '문구', color: '#64748b' },
  { id: 'blocked', name: '차단', color: '#ef4444' },
] as const

export type IssueBoardStatus = (typeof ISSUE_BOARD_STATUSES)[number]
export interface IssueBoardLabel {
  id: string
  name: string
  color: string
}

export interface IssueBoardComment {
  id: string
  authorType: 'user' | 'agent' | 'system'
  authorName: string
  body: string
  createdAt: string
}

export interface IssueBoardRun {
  id: string
  status: 'queued' | 'running' | 'waiting' | 'completed' | 'failed'
  title: string
  summary: string
  startedAt: string
  finishedAt: string | null
}

export interface IssueBoardDocument {
  id: string
  title: string
  summary: string
  updatedAt: string
}

export interface IssueBoardRelatedItem {
  id: string
  identifier: string
  title: string
  status: IssueBoardStatus
}

export interface IssueBoardIssue {
  id: string
  identifier: string
  title: string
  description: string
  status: IssueBoardStatus
  assigneeAgentId: string | null
  labels: string[]
  comments: IssueBoardComment[]
  runs: IssueBoardRun[]
  documents: IssueBoardDocument[]
  relatedItems: IssueBoardRelatedItem[]
  blockedBy: IssueBoardRelatedItem[]
  createdAt: string
  updatedAt: string
  startedAt: string | null
  completedAt: string | null
  live: boolean
}

export type IssueBoardColumnMap = Record<IssueBoardStatus, IssueBoardIssue[]>

export function createEmptyIssueBoardGroups(): IssueBoardColumnMap {
  const grouped = {} as IssueBoardColumnMap
  for (const status of ISSUE_BOARD_STATUSES) {
    grouped[status] = []
  }
  return grouped
}

export function groupIssuesByStatus(issues: IssueBoardIssue[]): IssueBoardColumnMap {
  const grouped = createEmptyIssueBoardGroups()
  for (const issue of issues) {
    grouped[issue.status].push(issue)
  }
  return grouped
}

export function moveIssueToStatus(
  issues: IssueBoardIssue[],
  issueId: string,
  status: IssueBoardStatus,
): IssueBoardIssue[] {
  const now = new Date().toISOString()
  return issues.map((issue) =>
    issue.id === issueId
      ? { ...issue, status, updatedAt: now, live: status === 'in_progress' }
      : issue,
  )
}

export function issueBoardStatusLabel(status: IssueBoardStatus) {
  const labels: Record<IssueBoardStatus, string> = {
    backlog: '보류',
    todo: '대기',
    in_progress: '진행 중',
    in_review: '검토 중',
    blocked: '차단됨',
    done: '완료',
    cancelled: '취소됨',
  }
  return labels[status]
}

export function createIssueBoardIdentifier(sequence: number) {
  return `TASK-${String(100 + sequence).padStart(3, '0')}`
}

export function createIssueBoardFixtures(sessionId: string): IssueBoardIssue[] {
  const now = new Date()
  const iso = (minutesAgo: number) => new Date(now.getTime() - minutesAgo * 60_000).toISOString()

  return [
    {
      id: `${sessionId}:todo:001`,
      identifier: createIssueBoardIdentifier(1),
      title: '채팅 입력에서 작업 선택 연결',
      description: '채팅 실행 전에 담당 에이전트가 묶인 작업을 선택할 수 있게 합니다.',
      status: 'todo',
      assigneeAgentId: 'main-agent',
      labels: ['chat', 'execution'],
      comments: [
        {
          id: `${sessionId}:comment:001`,
          authorType: 'user',
          authorName: '사용자',
          body: '채팅 입력에서 작업을 고르고 실행하면 해당 작업 컨텍스트가 같이 넘어가야 합니다.',
          createdAt: iso(210),
        },
        {
          id: `${sessionId}:comment:002`,
          authorType: 'agent',
          authorName: '메인 에이전트',
          body: '작업 선택 UI와 TaskRun 생성 요청 사이의 연결 지점을 확인했습니다.',
          createdAt: iso(150),
        },
      ],
      runs: [
        {
          id: `${sessionId}:run:001`,
          status: 'completed',
          title: '채팅 작업 선택 흐름 점검',
          summary: '입력 영역에서 작업 컨텍스트를 선택하는 흐름을 정리했습니다.',
          startedAt: iso(205),
          finishedAt: iso(190),
        },
      ],
      documents: [
        {
          id: `${sessionId}:doc:001`,
          title: '작업 선택 UX 메모',
          summary: '채팅 + 메뉴에서 작업 선택 창을 여는 방향으로 정리했습니다.',
          updatedAt: iso(140),
        },
      ],
      relatedItems: [],
      blockedBy: [],
      createdAt: iso(220),
      updatedAt: iso(110),
      startedAt: null,
      completedAt: null,
      live: false,
    },
    {
      id: `${sessionId}:todo:002`,
      identifier: createIssueBoardIdentifier(2),
      title: '작업 실행 상태 표시',
      description: '실행 중인 TaskRun을 작업 카드에 연결해 진행 상태를 보여줍니다.',
      status: 'in_progress',
      assigneeAgentId: 'main-agent',
      labels: ['taskrun', 'realtime'],
      comments: [
        {
          id: `${sessionId}:comment:003`,
          authorType: 'system',
          authorName: '시스템',
          body: '담당 에이전트가 작업을 실행 중입니다.',
          createdAt: iso(10),
        },
      ],
      runs: [
        {
          id: `${sessionId}:run:002`,
          status: 'running',
          title: 'TaskRun 상태 보드 연결',
          summary: '실행 이벤트를 작업 카드와 상세 패널에 반영하는 중입니다.',
          startedAt: iso(12),
          finishedAt: null,
        },
      ],
      documents: [],
      relatedItems: [
        {
          id: `${sessionId}:todo:001`,
          identifier: createIssueBoardIdentifier(1),
          title: '채팅 입력에서 작업 선택 연결',
          status: 'todo',
        },
      ],
      blockedBy: [],
      createdAt: iso(180),
      updatedAt: iso(8),
      startedAt: iso(12),
      completedAt: null,
      live: true,
    },
    {
      id: `${sessionId}:todo:003`,
      identifier: createIssueBoardIdentifier(3),
      title: '담당 에이전트 선택 UI 정리',
      description: '작업마다 하나의 담당 에이전트만 배정되도록 선택 흐름을 단순화합니다.',
      status: 'todo',
      assigneeAgentId: null,
      labels: ['board', 'assignee'],
      comments: [
        {
          id: `${sessionId}:comment:004`,
          authorType: 'user',
          authorName: '사용자',
          body: '에이전트가 많아졌을 때도 담당 변경 UI가 무너지지 않아야 합니다.',
          createdAt: iso(80),
        },
      ],
      runs: [],
      documents: [
        {
          id: `${sessionId}:doc:002`,
          title: '담당 선택 규칙',
          summary: '작업 하나에는 담당 에이전트 한 명만 배정합니다.',
          updatedAt: iso(60),
        },
      ],
      relatedItems: [],
      blockedBy: [],
      createdAt: iso(120),
      updatedAt: iso(45),
      startedAt: null,
      completedAt: null,
      live: false,
    },
    {
      id: `${sessionId}:todo:004`,
      identifier: createIssueBoardIdentifier(4),
      title: '서버 연결 방식 결정 필요',
      description: '작업 저장과 TaskRun 연결 이벤트를 어떤 실시간 계약으로 받을지 정해야 합니다.',
      status: 'blocked',
      assigneeAgentId: 'main-agent',
      labels: ['api', 'realtime'],
      comments: [
        {
          id: `${sessionId}:comment:005`,
          authorType: 'agent',
          authorName: '메인 에이전트',
          body: '작업 CRUD와 TaskRun 이벤트를 같은 WebSocket 흐름에서 갱신하는 계약이 필요합니다.',
          createdAt: iso(35),
        },
      ],
      runs: [
        {
          id: `${sessionId}:run:003`,
          status: 'waiting',
          title: '실시간 계약 설계 확인',
          summary: '작업 이벤트와 실행 이벤트의 책임 경계를 확인 중입니다.',
          startedAt: iso(40),
          finishedAt: null,
        },
      ],
      documents: [],
      relatedItems: [],
      blockedBy: [
        {
          id: `${sessionId}:todo:blocker:001`,
          identifier: 'TASK-API',
          title: 'AI 서버 작업 이벤트 계약 확정',
          status: 'blocked',
        },
      ],
      createdAt: iso(90),
      updatedAt: iso(30),
      startedAt: iso(40),
      completedAt: null,
      live: false,
    },
    {
      id: `${sessionId}:todo:005`,
      identifier: createIssueBoardIdentifier(5),
      title: '보드 한글 문구 정리',
      description: '사용자가 보는 보드 문구를 한글 기준으로 맞춘 작업입니다.',
      status: 'done',
      assigneeAgentId: 'main-agent',
      labels: ['ui', 'copy'],
      comments: [
        {
          id: `${sessionId}:comment:006`,
          authorType: 'system',
          authorName: '시스템',
          body: '작업이 완료되었습니다.',
          createdAt: iso(20),
        },
      ],
      runs: [
        {
          id: `${sessionId}:run:004`,
          status: 'completed',
          title: '보드 문구 정리',
          summary: '이슈 중심 문구를 작업 중심 문구로 바꿨습니다.',
          startedAt: iso(50),
          finishedAt: iso(25),
        },
      ],
      documents: [
        {
          id: `${sessionId}:doc:003`,
          title: '표시 문구 변경 내역',
          summary: '상태, 필터, 대시보드 문구 변경 사항을 기록했습니다.',
          updatedAt: iso(20),
        },
      ],
      relatedItems: [],
      blockedBy: [],
      createdAt: iso(80),
      updatedAt: iso(20),
      startedAt: iso(50),
      completedAt: iso(20),
      live: false,
    },
  ]
}
