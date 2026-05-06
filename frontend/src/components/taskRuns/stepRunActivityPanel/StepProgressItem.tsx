import { UsersRound } from 'lucide-react'
import type { ActivityItemView } from '@/types/taskRuns'
import type { RawStepRun } from '@/types/taskRuns'
import { toTaskRunStatusText, toTaskRunStatusTone } from '@/utils/taskRunStatusView'
import { toStepProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function StepProgressItem({
  step,
  activities,
}: {
  step: RawStepRun
  activities: ActivityItemView[]
}) {
  const workerItems = getStepWorkerItems(step, activities)

  return (
    <li className="bg-card border-border rounded-lg border p-3">
      <div className="flex min-h-14 items-center gap-3">
        <TaskRunStatusIcon tone={toTaskRunStatusTone(step.status)} />
        <span className="min-w-0 flex-1">
          <span className="text-foreground line-clamp-2 block text-sm font-medium [overflow-wrap:anywhere] break-words">
            {toUserFacingTaskTitle(step.title ?? step.goal ?? '답변 준비')}
          </span>
          <span className="text-muted-foreground mt-1 line-clamp-1 block text-xs">
            {toStepProgressSentence(step.status)}
          </span>
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
        worker 실행 상태
      </div>
      <ol className="space-y-1.5">
        {workers.map((worker) => (
          <li key={worker.id} className="flex items-start gap-2">
            <TaskRunStatusIcon tone={toTaskRunStatusTone(worker.status)} />
            <span className="min-w-0 flex-1">
              <span className="text-foreground line-clamp-1 block text-xs font-medium [overflow-wrap:anywhere] break-words">
                {worker.title}
              </span>
              <span className="text-muted-foreground line-clamp-1 block text-[11px] [overflow-wrap:anywhere] break-words">
                {worker.summary || toTaskRunStatusText(worker.status)}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

function getStepWorkerItems(step: RawStepRun, activities: ActivityItemView[]) {
  const workers = new Map<string, WorkerStatusItem>()
  const delegateTitles = getDelegateTaskTitles(activities)

  getAgentDetailWorkers(step).forEach((worker, index) => {
    mergeWorker(workers, worker, index, delegateTitles[index])
  })

  const workerSession = asRecord(step.worker_session) ?? asRecord(step.workerSession)
  if (workerSession !== undefined) {
    mergeWorker(workers, workerSession, workers.size)
  }

  activities.forEach((activity, index) => {
    const payload = asRecord(activity.raw.payload)
    const result = asRecord(payload?.result) ?? asRecord(payload?.output)
    const delegate = asRecord(result?.delegate)
    if (delegate !== undefined) {
      mergeWorker(workers, delegate, index)
      return
    }

    if (payload?.reason === 'delegate.started') {
      mergeWorker(workers, payload, index, activity.title)
    }
  })

  return [...workers.values()]
}

function getDelegateTaskTitles(activities: ActivityItemView[]) {
  const seen = new Set<string>()
  return activities
    .map((activity) => {
      const payload = asRecord(activity.raw.payload)
      const toolName = pickString(payload, 'toolName', 'tool_name')
      if (toolName !== 'delegate_task') {
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
  return Array.isArray(agentDetail?.workers)
    ? agentDetail.workers.filter(
        (worker): worker is Record<string, unknown> => asRecord(worker) !== undefined,
      )
    : []
}

function mergeWorker(
  workers: Map<string, WorkerStatusItem>,
  rawWorker: Record<string, unknown>,
  index: number,
  fallbackTitle?: string,
) {
  const workerSessionId = pickString(rawWorker, 'workerSessionId', 'worker_session_id', 'id')
  const agentId = pickString(rawWorker, 'agentId', 'agent_id')
  const id = workerSessionId ?? agentId ?? `worker-${index}`
  const existing = workers.get(id)
  const tasks = Array.isArray(rawWorker.tasks) ? rawWorker.tasks : []
  const firstTask = asRecord(tasks[0])
  const title =
    pickString(firstTask, 'title', 'goal', 'name') ??
    pickString(rawWorker, 'goal', 'title', 'name') ??
    fallbackTitle ??
    pickString(rawWorker, 'profileKey', 'profile_key') ??
    `worker ${index + 1}`
  const normalizedTitle = toWorkerDisplayTitle(toUserFacingTaskTitle(title))
  const shouldReplaceTitle = existing?.title === undefined || isGenericWorkerTitle(existing.title)

  workers.set(id, {
    id,
    title: shouldReplaceTitle ? normalizedTitle : existing.title,
    status: pickString(rawWorker, 'status') ?? existing?.status,
    summary: pickString(rawWorker, 'summary') ?? existing?.summary,
  })
}

function isGenericWorkerTitle(value: string) {
  const normalized = value.trim().toLowerCase()
  return (
    normalized === '' ||
    normalized === 'worker.default' ||
    normalized === 'worker' ||
    /^worker \d+$/.test(normalized)
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
