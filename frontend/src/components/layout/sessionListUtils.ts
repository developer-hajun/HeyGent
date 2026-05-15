import type { RawAiSession } from '@/types/aiChat'

function getStringValue(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value : undefined
}

export function getSessionTime(session: RawAiSession): number {
  const rawTime =
    getStringValue(session.last_message_at) ??
    getStringValue(session.updated_at) ??
    getStringValue(session.created_at)
  if (rawTime === undefined) {
    return 0
  }
  const time = new Date(rawTime).getTime()
  return Number.isFinite(time) ? time : 0
}

export function isRemovedSidebarSession(session: RawAiSession): boolean {
  return (
    session.deleted_at != null || session.status === 'DELETED' || isInternalAgentSession(session)
  )
}

/**
 * 시스템 내부에서 자동 생성된 세션을 판별한다.
 * (서브 에이전트 전용 세션, task run 처리용 세션 등) — 사이드바에서 숨길 대상.
 */
export function isInternalAgentSession(session: RawAiSession): boolean {
  const sessionRole = getStringValue(session.session_role) ?? getStringValue(session.sessionRole)
  if (sessionRole !== undefined && sessionRole !== 'main') {
    return true
  }
  if (getStringValue(session.parent_session_id) ?? getStringValue(session.parentSessionId)) {
    return true
  }
  if (getStringValue(session.task_run_id) ?? getStringValue(session.taskRunId)) {
    return true
  }
  return session.session_id.startsWith('agent_session_')
}

/**
 * sidebar 정렬 기준(고정 우선 → 최신 활동순)에 맞춰
 * 주어진 세션 목록 중 첫 번째(=가장 위에 보이는) 세션을 돌려준다.
 * excludeSessionId가 있으면 그 세션은 제외한다.
 */
export function pickTopSession(
  sessionsById: Record<string, RawAiSession>,
  pinnedSessionIds: Set<string>,
  excludeSessionId?: string,
): RawAiSession | null {
  const sorted = Object.values(sessionsById)
    .filter((session) => session.session_id !== excludeSessionId)
    .filter((session) => !isRemovedSidebarSession(session))
    .sort((first, second) => getSessionTime(second) - getSessionTime(first))
  const pinned = sorted.filter((session) => pinnedSessionIds.has(session.session_id))
  const unpinned = sorted.filter((session) => !pinnedSessionIds.has(session.session_id))
  return pinned[0] ?? unpinned[0] ?? null
}
