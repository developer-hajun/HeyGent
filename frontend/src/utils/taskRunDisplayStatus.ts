type TaskRunStatusSource = {
  status?: string | null
}

type ActivityStatusSource = {
  raw?: {
    status?: string | null
    event_type?: string | null
  }
}

const TERMINAL_TASK_STATUSES = new Set([
  'COMPLETED',
  'FAILED',
  'CANCELLED',
  'CANCELED',
  'task.completed',
  'task.failed',
  'task.canceled',
  'task.cancelled',
])

export function isTerminalTaskRunStatus(status?: string | null) {
  return typeof status === 'string' && TERMINAL_TASK_STATUSES.has(status)
}

export function resolveTaskRunDisplayStatus(
  taskRun: TaskRunStatusSource | undefined,
  activities: ActivityStatusSource[],
) {
  const taskStatus = taskRun?.status
  if (isTerminalTaskRunStatus(taskStatus)) {
    return taskStatus
  }

  const latestActivity = activities.at(-1)
  return latestActivity?.raw?.status ?? latestActivity?.raw?.event_type ?? taskStatus
}

export function shouldShowAssistantTaskRunProgress({
  messageStatus,
  taskStatus,
  stepRunCount,
}: {
  messageStatus?: string | null
  taskStatus?: string | null
  stepRunCount: number
}) {
  if (messageStatus === 'completed' || messageStatus === 'failed') {
    return false
  }
  if (messageStatus === 'streaming') {
    return stepRunCount > 0
  }
  return !isTerminalTaskRunStatus(taskStatus) && stepRunCount > 0
}
