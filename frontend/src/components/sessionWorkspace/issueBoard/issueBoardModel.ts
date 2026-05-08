export const ISSUE_BOARD_STATUSES = [
  'backlog',
  'todo',
  'in_progress',
  'in_review',
  'blocked',
  'done',
  'cancelled',
] as const

export const ISSUE_BOARD_PRIORITY_ORDER = ['critical', 'high', 'medium', 'low'] as const

export type IssueBoardStatus = (typeof ISSUE_BOARD_STATUSES)[number]
export type IssueBoardPriority = (typeof ISSUE_BOARD_PRIORITY_ORDER)[number]

export interface IssueBoardAssignee {
  id: string
  name: string
}

export interface IssueBoardIssue {
  id: string
  identifier: string
  title: string
  description: string
  status: IssueBoardStatus
  priority: IssueBoardPriority
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
    issue.id === issueId ? { ...issue, status, updatedAt: now } : issue,
  )
}

export function issueBoardStatusLabel(status: IssueBoardStatus) {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

export function createIssueBoardFixtures(sessionId: string): IssueBoardIssue[] {
  const prefix =
    sessionId
      .replace(/[^a-zA-Z0-9]/g, '')
      .slice(-4)
      .toUpperCase() || 'SESS'
  const now = new Date()
  const iso = (minutesAgo: number) => new Date(now.getTime() - minutesAgo * 60_000).toISOString()

  return [
    {
      id: `${sessionId}:issue:001`,
      identifier: `${prefix}-101`,
      title: 'Sketch company analytics dashboard',
      description: '운영자가 한 화면에서 실행 흐름과 병목을 확인할 수 있게 정리합니다.',
      status: 'backlog',
      priority: 'low',
      assigneeAgentId: 'agent-ceo',
      createdAt: iso(360),
      updatedAt: iso(320),
      live: true,
    },
    {
      id: `${sessionId}:issue:002`,
      identifier: `${prefix}-102`,
      title: 'Wire issue board status transitions',
      description: '상태 변경이 카드 이동과 상세 표시에서 같은 값으로 보이게 만듭니다.',
      status: 'todo',
      priority: 'high',
      assigneeAgentId: 'agent-coder',
      createdAt: iso(250),
      updatedAt: iso(60),
      live: false,
    },
    {
      id: `${sessionId}:issue:003`,
      identifier: `${prefix}-103`,
      title: 'Connect running task marker to active execution',
      description: '실행 중인 작업을 보드 카드에서 파란 표시로 드러냅니다.',
      status: 'in_progress',
      priority: 'critical',
      assigneeAgentId: 'agent-coder',
      createdAt: iso(180),
      updatedAt: iso(10),
      live: true,
      needsNextStep: true,
    },
    {
      id: `${sessionId}:issue:004`,
      identifier: `${prefix}-104`,
      title: 'Review generated handoff summary',
      description: '완료 판단 전에 산출물 요약과 다음 조치를 검토합니다.',
      status: 'in_review',
      priority: 'medium',
      assigneeAgentId: 'agent-review',
      createdAt: iso(160),
      updatedAt: iso(35),
      live: false,
    },
    {
      id: `${sessionId}:issue:005`,
      identifier: `${prefix}-105`,
      title: 'Resolve missing workspace decision',
      description: '작업 범위를 정하지 못해 실행이 멈춘 항목입니다.',
      status: 'blocked',
      priority: 'high',
      assigneeAgentId: 'agent-ceo',
      createdAt: iso(120),
      updatedAt: iso(50),
      live: false,
    },
    {
      id: `${sessionId}:issue:006`,
      identifier: `${prefix}-106`,
      title: 'Close completed chat loading fix',
      description: '완료된 작업을 닫고 이후 실행에서 제외합니다.',
      status: 'done',
      priority: 'medium',
      assigneeAgentId: 'agent-coder',
      createdAt: iso(90),
      updatedAt: iso(20),
      live: false,
    },
    {
      id: `${sessionId}:issue:007`,
      identifier: `${prefix}-107`,
      title: 'Remove obsolete board color migration',
      description: '더 이상 진행하지 않는 작업을 보드 뒤쪽으로 보냅니다.',
      status: 'cancelled',
      priority: 'medium',
      assigneeAgentId: null,
      createdAt: iso(80),
      updatedAt: iso(75),
      live: false,
    },
  ]
}
