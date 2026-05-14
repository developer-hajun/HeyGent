import { UsersRound } from 'lucide-react'
import type { ActivityItemView } from '@/types/taskRuns'
import type { RawStepRun } from '@/types/taskRuns'
import { toTaskRunStatusText, toTaskRunStatusTone } from '@/utils/taskRunStatusView'
import { toStepProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusBadge, TaskRunStatusIcon } from './TaskRunStatusIcon'

export function StepProgressItem({
  step,
  activities,
  allActivities = activities,
}: {
  step: RawStepRun
  activities: ActivityItemView[]
  allActivities?: ActivityItemView[]
}) {
  const agentNameMap = buildAgentNameMap(step, allActivities)
  const workerItems = getStepWorkerItems(step, activities, agentNameMap)
  const executionLabel = getStepExecutionLabel(step, activities, agentNameMap)
  const stepTone = toTaskRunStatusTone(step.status)

  return (
    <li className="bg-card border-border rounded-lg border p-3">
      <div className="flex min-h-14 items-center gap-3">
        <TaskRunStatusIcon tone={stepTone} />
        <span className="min-w-0 flex-1">
          <span className="text-foreground line-clamp-2 block text-sm font-medium [overflow-wrap:anywhere] break-words">
            {toUserFacingTaskTitle(step.title ?? step.goal ?? '답변 준비')}
          </span>
          <TaskRunStatusBadge
            tone={stepTone}
            label={toStepProgressSentence(step.status)}
            className="mt-1"
          />
          {executionLabel !== undefined && (
            <span className="text-muted-foreground mt-0.5 line-clamp-1 block text-[11px]">
              {executionLabel}
            </span>
          )}
        </span>
      </div>

      {workerItems.length > 0 && <WorkerStatusList workers={workerItems} />}
    </li>
  )
}

type WorkerStatusItem = {
  id: string
  title: string
  status?: string | null
  summary?: string | null
}

function WorkerStatusList({ workers }: { workers: WorkerStatusItem[] }) {
  return (
    <section className="border-border bg-muted/20 mt-3 rounded-lg border px-3 py-2">
      <div className="text-muted-foreground mb-2 flex items-center gap-1.5 text-[11px] font-medium">
        <UsersRound className="h-3.5 w-3.5" />
        세션 에이전트 실행
      </div>
      <ol className="space-y-1.5">
        {workers.map((worker) => (
          <li key={worker.id} className="flex items-start gap-2">
            <TaskRunStatusIcon tone={toTaskRunStatusTone(worker.status)} />
            <span className="min-w-0 flex-1">
              <span className="text-foreground line-clamp-1 block text-xs font-medium [overflow-wrap:anywhere] break-words">
                {worker.title}
              </span>
              <TaskRunStatusBadge
                tone={toTaskRunStatusTone(worker.status)}
                label={worker.summary || toTaskRunStatusText(worker.status)}
                className="mt-1 max-w-full"
              />
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

function getStepWorkerItems(
  step: RawStepRun,
  activities: ActivityItemView[],
  agentNameMap: Map<string, string>,
) {
  const workers = new Map<string, WorkerStatusItem>()
  const delegatedTitles = getDelegatedTaskTitles(activities)

  getAgentDetailWorkers(step).forEach((worker, index) => {
    mergeWorker(workers, worker, index, agentNameMap, delegatedTitles[index])
  })

  getDisplayContextWorkers(step).forEach((worker, index) => {
    mergeWorker(workers, worker, index, agentNameMap)
  })

  const workerSession = asRecord(step.worker_session) ?? asRecord(step.workerSession)
  if (workerSession !== undefined) {
    mergeWorker(workers, workerSession, workers.size, agentNameMap)
  }

  activities.forEach((activity, index) => {
    const payload = asRecord(activity.raw.payload)
    const result = asRecord(payload?.result) ?? asRecord(payload?.output)
    const delegate = asRecord(result?.delegate)
    if (delegate !== undefined) {
      mergeWorker(workers, delegate, index, agentNameMap)
      return
    }

    if (getToolName(payload) === 'session_agent_task') {
      const input = asRecord(payload?.input) ?? asRecord(payload?.args)
      const agent = asRecord(result?.agent)
      mergeWorker(
        workers,
        {
          agentId:
            pickString(agent, 'profileId', 'profile_id', 'agentId', 'id') ??
            pickString(input, 'assigneeAgentId', 'agentId', 'id'),
          displayName: pickString(agent, 'name', 'displayName'),
          title: pickString(input, 'title', 'goal', 'name'),
          status: pickString(result, 'status') ?? activity.raw.status ?? activity.raw.event_type,
          summary: pickString(result, 'content', 'summary') ?? activity.title,
        },
        index,
        agentNameMap,
      )
      return
    }

    if (payload?.reason === 'delegate.started') {
      mergeWorker(workers, payload, index, agentNameMap, activity.title)
    }
  })

  return [...workers.values()]
}

function getDelegatedTaskTitles(activities: ActivityItemView[]) {
  const seen = new Set<string>()
  return activities
    .map((activity) => {
      const payload = asRecord(activity.raw.payload)
      const toolName = getToolName(payload)
      if (toolName !== 'delegate_task' && toolName !== 'session_agent_task') {
        return undefined
      }
      const input = asRecord(payload?.input) ?? asRecord(payload?.args)
      const tasks = Array.isArray(input?.tasks) ? input.tasks : []
      const firstTask = asRecord(tasks[0])
      return (
        pickString(firstTask, 'title', 'goal', 'name') ??
        pickString(input, 'title', 'goal', 'name') ??
        pickString(payload, 'title')
      )
    })
    .filter((title): title is string => {
      if (title === undefined || seen.has(title)) {
        return false
      }
      seen.add(title)
      return true
    })
}

function getAgentDetailWorkers(step: RawStepRun) {
  const detail = asRecord(step.detail_json)
  const agentDetail = asRecord(detail?.agentDetail)
  const workers = Array.isArray(agentDetail?.workers) ? agentDetail.workers : []
  const sessionAgents = Array.isArray(agentDetail?.sessionAgents) ? agentDetail.sessionAgents : []
  return [...workers, ...sessionAgents].filter(
    (worker): worker is Record<string, unknown> => asRecord(worker) !== undefined,
  )
}

function getDisplayContextWorkers(step: RawStepRun) {
  return (step.displayContext?.delegatedAgents ?? []) as Record<string, unknown>[]
}

function getStepExecutionLabel(
  step: RawStepRun,
  activities: ActivityItemView[],
  agentNameMap: Map<string, string>,
) {
  const delegatedAgentName = getDelegatedAgentName(step, activities, agentNameMap)
  if (delegatedAgentName !== undefined) {
    return `팀장이 ${delegatedAgentName}에게 위임`
  }

  const actorName = resolveAgentDisplayName(step.displayContext?.actorAgent, agentNameMap)
  if (actorName === undefined) {
    return undefined
  }
  return `실행 에이전트: ${actorName}`
}

function getDelegatedAgentName(
  step: RawStepRun,
  activities: ActivityItemView[],
  agentNameMap: Map<string, string>,
) {
  for (const worker of getAgentDetailWorkers(step)) {
    const name = resolveWorkerDisplayName(worker, agentNameMap)
    if (name !== undefined) return name
  }

  for (const activity of activities) {
    const payload = asRecord(activity.raw.payload)
    if (getToolName(payload) !== 'session_agent_task') continue
    const input = asRecord(payload?.input) ?? asRecord(payload?.args)
    const result = asRecord(payload?.result) ?? asRecord(payload?.output)
    const agent = asRecord(result?.agent)
    const name =
      pickString(agent, 'name', 'displayName') ??
      resolveAgentId(
        pickString(agent, 'profileId', 'profile_id', 'agentId', 'id') ??
          pickString(input, 'assigneeAgentId'),
        agentNameMap,
      )
    if (name !== undefined) return name
  }

  return undefined
}

function mergeWorker(
  workers: Map<string, WorkerStatusItem>,
  rawWorker: Record<string, unknown>,
  index: number,
  agentNameMap: Map<string, string>,
  fallbackTitle?: string,
) {
  const workerSessionId = pickString(
    rawWorker,
    'workerSessionId',
    'worker_session_id',
    'agentSessionId',
    'id',
  )
  const agentId = pickString(rawWorker, 'agentId', 'agent_id')
  const id = workerSessionId ?? agentId ?? `worker-${index}`
  const existing = workers.get(id)
  const tasks = Array.isArray(rawWorker.tasks) ? rawWorker.tasks : []
  const firstTask = asRecord(tasks[0])
  const agentName = resolveWorkerDisplayName(rawWorker, agentNameMap)
  const title =
    agentName ??
    pickString(firstTask, 'title', 'goal', 'name') ??
    pickString(rawWorker, 'goal', 'title', 'name', 'displayName') ??
    fallbackTitle ??
    pickString(rawWorker, 'profileKey', 'profile_key') ??
    `세션 에이전트 ${index + 1}`
  const normalizedTitle = toWorkerDisplayTitle(toUserFacingTaskTitle(title))
  const shouldReplaceTitle = existing?.title === undefined || isGenericWorkerTitle(existing.title)

  workers.set(id, {
    id,
    title: shouldReplaceTitle ? normalizedTitle : existing.title,
    status: pickString(rawWorker, 'status') ?? existing?.status,
    summary: summarizeWorker(rawWorker, agentName) ?? existing?.summary,
  })
}

function summarizeWorker(rawWorker: Record<string, unknown>, agentName?: string) {
  const rawSummary = pickString(rawWorker, 'summary')
  if (rawSummary === undefined) {
    return undefined
  }
  if (agentName === undefined) {
    return toWorkerDisplayTitle(rawSummary)
  }
  return toWorkerDisplayTitle(rawSummary.replaceAll(agentName, '').trim())
}

function isGenericWorkerTitle(value: string) {
  const normalized = value.trim().toLowerCase()
  return (
    normalized === '' ||
    normalized === 'worker.default' ||
    normalized === 'worker' ||
    normalized === '세션 에이전트' ||
    /^worker \d+$/.test(normalized) ||
    /^세션 에이전트 \d+$/.test(normalized)
  )
}

function toWorkerDisplayTitle(value: string) {
  const perspectiveMatch = value.match(/["'“‘]([^"'”’]+ 관점)["'”’]/)
  if (perspectiveMatch?.[1]) {
    return `${perspectiveMatch[1]} worker`
  }
  if (value.length <= 64) {
    return value
  }
  return `${value.slice(0, 61).trim()}...`
}

function buildAgentNameMap(step: RawStepRun, activities: ActivityItemView[]) {
  const names = new Map<string, string>()
  addAgentRef(names, step.displayContext?.actorAgent)
  addAgentRef(names, step.displayContext?.assigneeAgent)
  step.displayContext?.delegatedAgents?.forEach((agent) => addAgentRef(names, agent))

  getAgentDetailWorkers(step).forEach((worker) => {
    addAgentName(
      names,
      pickString(worker, 'agentId', 'agent_id', 'profileId', 'profile_id', 'id'),
      pickString(worker, 'displayName', 'display_name', 'name'),
    )
  })

  activities.forEach((activity) => {
    addAgentRef(names, activity.displayContext?.actorAgent)
    addAgentRef(names, activity.displayContext?.assigneeAgent)
    activity.displayContext?.delegatedAgents?.forEach((agent) => addAgentRef(names, agent))

    const payload = asRecord(activity.raw.payload)
    const input = asRecord(payload?.input) ?? asRecord(payload?.args)
    const result = asRecord(payload?.result) ?? asRecord(payload?.output)
    const agent = asRecord(result?.agent)
    addAgentName(
      names,
      pickString(agent, 'profileId', 'profile_id', 'agentId', 'id') ??
        pickString(input, 'assigneeAgentId', 'agentId', 'id'),
      pickString(agent, 'name', 'displayName'),
    )
  })

  return names
}

function addAgentRef(
  names: Map<string, string>,
  agent?: { id?: string; profileId?: string | null; displayName?: string },
) {
  addAgentName(names, agent?.id, agent?.displayName)
  addAgentName(names, agent?.profileId ?? undefined, agent?.displayName)
}

function addAgentName(names: Map<string, string>, id?: string, name?: string) {
  if (id === undefined || name === undefined) return
  const normalizedId = id.trim()
  const normalizedName = name.trim()
  if (!normalizedId || !normalizedName || isRawAgentId(normalizedName)) return
  names.set(normalizedId, normalizedName)
}

function resolveWorkerDisplayName(
  rawWorker: Record<string, unknown>,
  agentNameMap: Map<string, string>,
) {
  const directName = pickString(rawWorker, 'displayName', 'display_name', 'name')
  if (directName !== undefined && !isRawAgentId(directName)) {
    return directName
  }
  return resolveAgentId(
    pickString(rawWorker, 'agentId', 'agent_id', 'profileId', 'profile_id', 'id'),
    agentNameMap,
  )
}

function resolveAgentDisplayName(
  agent: { id?: string; profileId?: string | null; displayName?: string } | undefined,
  agentNameMap: Map<string, string>,
) {
  if (agent === undefined) return undefined
  if (agent.displayName !== undefined && !isRawAgentId(agent.displayName)) {
    return agent.displayName
  }
  return resolveAgentId(agent.profileId ?? agent.id, agentNameMap)
}

function resolveAgentId(agentId: string | undefined, agentNameMap: Map<string, string>) {
  if (agentId === undefined) return undefined
  return agentNameMap.get(agentId) ?? (isRawAgentId(agentId) ? undefined : agentId)
}

function getToolName(payload: Record<string, unknown> | undefined) {
  return pickString(payload, 'toolName', 'tool_name')
}

function isRawAgentId(value: string) {
  return /^agent_profile_[a-z0-9]+$/i.test(value.trim())
}

function pickString(value: unknown, ...keys: string[]) {
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

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}
