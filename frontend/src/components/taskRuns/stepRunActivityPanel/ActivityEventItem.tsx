import { ChevronDown } from 'lucide-react'
import type { ActivityItemView } from '@/types/taskRuns'
import { toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusBadge, TaskRunStatusIcon } from './TaskRunStatusIcon'

export function ActivityEventItem({
  activity,
  taskRunFinished = false,
  compact = false,
  agentNameMap,
}: {
  activity: ActivityItemView
  taskRunFinished?: boolean
  compact?: boolean
  agentNameMap?: Map<string, string>
}) {
  // 세부 기록은 과거 이벤트의 상태를 보여준다. 다만 TaskRun이 이미 끝난 뒤에는
  // 과거 started/running 이벤트 아이콘이 계속 도는 것처럼 보이지 않게 고정 아이콘으로 바꾼다.
  const tone = taskRunFinished && activity.tone === 'running' ? 'completed' : activity.tone
  const detailSections = buildActivityDetailSections(activity.raw)
  const actorName = resolveAgentDisplayName(activity.displayContext?.actorAgent, agentNameMap)
  const title = getActivityDisplayTitle(activity, actorName)
  const statusText = getActivityStatusLine(activity, actorName)

  return (
    <li
      className={compact ? 'bg-muted/20 rounded-md' : 'bg-muted/30 border-border rounded-lg border'}
    >
      <details className="group">
        <summary
          className={
            compact
              ? 'hover:bg-muted/50 flex min-h-12 cursor-pointer list-none items-start gap-2 rounded-md px-2 py-2 transition-colors'
              : 'hover:bg-muted/50 flex min-h-20 cursor-pointer list-none items-center gap-3 rounded-lg p-3 transition-colors'
          }
        >
          <TaskRunStatusIcon tone={tone} />
          <span className="selectable-text min-w-0 flex-1">
            <span
              className={
                compact
                  ? 'text-foreground/90 line-clamp-1 block text-xs font-medium [overflow-wrap:anywhere] break-words'
                  : 'text-foreground line-clamp-2 block text-sm font-medium [overflow-wrap:anywhere] break-words'
              }
            >
              {title}
            </span>
            <TaskRunStatusBadge tone={tone} label={statusText} className="mt-1 max-w-full" />
          </span>
          <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0 transition-transform group-open:rotate-180" />
        </summary>
        {(activity.occurredAt || detailSections.length > 0) && (
          <div
            className={
              compact
                ? 'selectable-text border-border space-y-2 border-t px-2 py-2 pl-8'
                : 'selectable-text border-border space-y-2 border-t px-3 py-2 pl-12'
            }
          >
            {activity.occurredAt && (
              <div className="text-muted-foreground/80 text-[11px]">{activity.occurredAt}</div>
            )}
            {detailSections.map((section) => (
              <details key={section.label} className="group/detail">
                <summary className="text-muted-foreground hover:text-foreground flex cursor-pointer list-none items-center justify-between rounded px-1 py-1 text-[11px] font-medium transition-colors">
                  <span>{section.label}</span>
                  <ChevronDown className="h-3 w-3 shrink-0 transition-transform group-open/detail:rotate-180" />
                </summary>
                <pre className="selectable-text bg-background/80 border-border text-muted-foreground mt-1 max-h-72 overflow-auto rounded border p-2 text-[11px] leading-4 [overflow-wrap:anywhere] whitespace-pre-wrap">
                  {section.text}
                </pre>
              </details>
            ))}
          </div>
        )}
      </details>
    </li>
  )
}

type DetailSection = {
  label: string
  text: string
}

const MAX_DETAIL_CHARS = 1800

const getActivityDisplayTitle = (activity: ActivityItemView, actorName?: string) => {
  const payload = asRecord(activity.raw.payload)
  const toolName = pickString(payload, 'toolName', 'tool_name')
  if (toolName === 'session_agent_task') {
    const result = asRecord(payload?.result) ?? asRecord(payload?.output)
    const agent = asRecord(result?.agent)
    const agentName = pickString(agent, 'name', 'displayName')
    if (agentName !== undefined) {
      return `${agentName}에게 작업 위임`
    }
  }

  const title = toUserFacingTaskTitle(activity.title)
  if (
    actorName !== undefined &&
    isToolEvent(activity.raw.event_type) &&
    !title.includes(actorName)
  ) {
    return `${actorName}가 ${title}`
  }
  return title
}

const getActivityStatusLine = (activity: ActivityItemView, actorName?: string) => {
  if (actorName === undefined) {
    return activity.statusText
  }
  if (isToolEvent(activity.raw.event_type)) {
    return `${actorName} 실행`
  }
  return `${activity.statusText} · ${actorName}`
}

const isToolEvent = (eventType?: string | null) =>
  eventType === 'tool.started' ||
  eventType === 'tool.completed' ||
  eventType === 'search.started' ||
  eventType === 'search.completed'

const resolveAgentDisplayName = (
  agent:
    | {
        id?: string
        profileId?: string | null
        displayName?: string
      }
    | undefined,
  agentNameMap?: Map<string, string>,
) => {
  if (agent === undefined) return undefined
  if (agent.displayName !== undefined && !isRawAgentId(agent.displayName)) {
    return agent.displayName
  }
  const id = agent.profileId ?? agent.id
  if (id === undefined) return isRawAgentId(agent.displayName ?? '') ? undefined : agent.displayName
  return agentNameMap?.get(id) ?? (isRawAgentId(id) ? undefined : id)
}

const isRawAgentId = (value: string) => /^agent_profile_[a-z0-9]+$/i.test(value.trim())

const buildActivityDetailSections = (raw: ActivityItemView['raw']): DetailSection[] => {
  const sections: DetailSection[] = []
  const payload = raw.payload
  const payloadRecord = asRecord(payload)

  if (payloadRecord !== undefined) {
    const input = payloadRecord.input ?? payloadRecord.args
    const result = payloadRecord.result ?? payloadRecord.output
    const metadata = withoutKeys(payloadRecord, ['input', 'args', 'result', 'output'])

    pushDetailSection(sections, '도구 입력', input)
    pushDetailSection(sections, '도구 결과', result)
    pushDetailSection(sections, '원본 이벤트', metadata)
  } else {
    pushDetailSection(sections, '원본 이벤트', payload)
  }

  pushDetailSection(sections, '원본 상세 데이터', raw.detail_json)
  return sections
}

const pickString = (value: unknown, ...keys: string[]) => {
  const record = asRecord(value)
  if (record === undefined) {
    return undefined
  }
  for (const key of keys) {
    const candidate = record[key]
    if (typeof candidate === 'string' && candidate.trim() !== '') {
      return candidate.trim()
    }
  }
  return undefined
}

const pushDetailSection = (sections: DetailSection[], label: string, value: unknown) => {
  if (value === undefined || value === null) {
    return
  }
  if (isEmptyRecord(value)) {
    return
  }

  sections.push({
    label,
    text: formatDetailValue(value),
  })
}

const formatDetailValue = (value: unknown) => {
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  if (text.length <= MAX_DETAIL_CHARS) {
    return text
  }
  return `${text.slice(0, MAX_DETAIL_CHARS)}\n...`
}

const asRecord = (value: unknown): Record<string, unknown> | undefined => {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return undefined
  }
  return value as Record<string, unknown>
}

const withoutKeys = (value: Record<string, unknown>, keys: string[]) => {
  const copied = { ...value }
  keys.forEach((key) => {
    delete copied[key]
  })
  return copied
}

const isEmptyRecord = (value: unknown) => {
  const record = asRecord(value)
  return record !== undefined && Object.keys(record).length === 0
}
