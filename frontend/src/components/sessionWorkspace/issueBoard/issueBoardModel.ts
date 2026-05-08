export const ISSUE_BOARD_STATUSES = ['todo', 'in_progress', 'blocked', 'done'] as const

export type IssueBoardStatus = (typeof ISSUE_BOARD_STATUSES)[number]

export interface IssueBoardIssue {
  id: string
  identifier: string
  title: string
  description: string
  status: IssueBoardStatus
  assigneeAgentId: string | null
  createdAt: string
  updatedAt: string
  live: boolean
  needsNextStep?: boolean
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
    todo: '대기',
    in_progress: '진행 중',
    blocked: '차단됨',
    done: '완료',
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
      createdAt: iso(220),
      updatedAt: iso(110),
      live: false,
    },
    {
      id: `${sessionId}:todo:002`,
      identifier: createIssueBoardIdentifier(2),
      title: '작업 실행 상태 표시',
      description: '실행 중인 TaskRun을 작업 카드에 연결해 진행 상태를 보여줍니다.',
      status: 'in_progress',
      assigneeAgentId: 'main-agent',
      createdAt: iso(180),
      updatedAt: iso(8),
      live: true,
      needsNextStep: true,
    },
    {
      id: `${sessionId}:todo:003`,
      identifier: createIssueBoardIdentifier(3),
      title: '담당 에이전트 선택 UI 정리',
      description: '작업마다 하나의 담당 에이전트만 배정되도록 선택 흐름을 단순화합니다.',
      status: 'todo',
      assigneeAgentId: null,
      createdAt: iso(120),
      updatedAt: iso(45),
      live: false,
    },
    {
      id: `${sessionId}:todo:004`,
      identifier: createIssueBoardIdentifier(4),
      title: '서버 연결 방식 결정 필요',
      description: '작업 저장과 TaskRun 연결 이벤트를 어떤 실시간 계약으로 받을지 정해야 합니다.',
      status: 'blocked',
      assigneeAgentId: 'main-agent',
      createdAt: iso(90),
      updatedAt: iso(30),
      live: false,
    },
    {
      id: `${sessionId}:todo:005`,
      identifier: createIssueBoardIdentifier(5),
      title: '보드 한글 문구 정리',
      description: '사용자가 보는 보드 문구를 한글 기준으로 맞춘 작업입니다.',
      status: 'done',
      assigneeAgentId: 'main-agent',
      createdAt: iso(80),
      updatedAt: iso(20),
      live: false,
    },
  ]
}
