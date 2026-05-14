import { useEffect, useRef } from 'react'
import { listSessionAgents, getSessionMainAgent, deriveSpriteId } from '@/apis/agents'
import type { AgentActivityStatus, TaskStatus, VisualizationTask } from '@/components/office/types'
import { useAgentVisualizationStore } from '@/store/useAgentVisualizationStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import type { RawStepRun, RawTaskRun } from '@/types/taskRuns'

const TERMINAL_STATUSES = new Set(['COMPLETED', 'FAILED', 'CANCELED', 'CANCELLED'])

function toActivityStatus(status?: string | null): AgentActivityStatus {
  const s = status?.toUpperCase()
  if (!s || s === 'PENDING') return 'inactive'
  if (TERMINAL_STATUSES.has(s)) return 'resting'
  return 'working'
}

function toTaskStatus(status?: string | null): TaskStatus {
  const s = status?.toUpperCase()
  if (s === 'COMPLETED' || s === 'CANCELED' || s === 'CANCELLED') return 'completed'
  if (s === 'FAILED') return 'failed'
  if (s === 'RUNNING' || s === 'WAITING' || s === 'BLOCKED') return 'in_progress'
  return 'pending'
}

function getTimestamp(value?: string | null): number {
  if (!value) return 0
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : 0
}

function getTaskRunSortTime(taskRun: RawTaskRun): number {
  return getTimestamp(taskRun.updated_at ?? taskRun.completed_at ?? taskRun.created_at)
}

function getStepRunUpdatedAt(stepRun: RawStepRun): string | undefined {
  return typeof stepRun.updated_at === 'string' ? stepRun.updated_at : undefined
}

// 백엔드는 completed_at 대신 ended_at을 사용한다.
function getStepRunEndedAt(stepRun: RawStepRun): string | undefined {
  const raw = stepRun as Record<string, unknown>
  if (typeof raw.ended_at === 'string') return raw.ended_at
  if (typeof raw.endedAt === 'string') return raw.endedAt
  return undefined
}

// 백엔드는 goal을 StepRunResponse.semantic.goal에 중첩해서 제공한다.
function getStepRunGoal(stepRun: RawStepRun): string {
  if (typeof stepRun.goal === 'string') return stepRun.goal
  const raw = stepRun as Record<string, unknown>
  const semantic = raw.semantic
  if (typeof semantic === 'object' && semantic !== null) {
    const goal = (semantic as Record<string, unknown>).goal
    if (typeof goal === 'string') return goal
  }
  return ''
}

// profileIdMap(profileId → spriteId)을 사용해 actorAgent를 spriteId로 해석한다.
// useVisualizationSync의 resolveProfileKey와 동일한 우선순위로 처리한다.
function resolveTaskRunSpriteId(
  taskRun: RawTaskRun,
  profileIdMap?: Record<string, string>,
): string | null {
  const actorAgent = taskRun.displayContext?.actorAgent
  if (!actorAgent) return null
  if (actorAgent.kind === 'main') return 'ceo'
  const mappedKey = actorAgent.profileId ?? actorAgent.id
  const fromMap = mappedKey != null ? profileIdMap?.[mappedKey] : undefined
  if (fromMap) return fromMap
  return actorAgent.profileKey ?? null
}

function resolveSessionTaskRunSpriteId(
  taskRun: RawTaskRun,
  sessionId?: string,
  profileIdMap?: Record<string, string>,
): string | null {
  return (
    resolveTaskRunSpriteId(taskRun, profileIdMap) ??
    (sessionId !== undefined && taskRun.session_id === sessionId ? 'ceo' : null)
  )
}

function pickCurrentTask(
  taskRun: RawTaskRun,
  stepRuns: RawStepRun[],
): VisualizationTask | undefined {
  if (TERMINAL_STATUSES.has(taskRun.status?.toUpperCase() ?? '')) return undefined

  const activeStep = stepRuns
    .filter((sr) => {
      const status = sr.status?.toUpperCase()
      return status === 'RUNNING' || status === 'WAITING'
    })
    .sort((a, b) => (b.step_order ?? b.stepOrder ?? 0) - (a.step_order ?? a.stepOrder ?? 0))[0]

  if (activeStep) {
    return {
      taskId: activeStep.step_run_id,
      title: activeStep.title ?? taskRun.title ?? '작업 진행 중',
      description: getStepRunGoal(activeStep),
      status: 'in_progress',
      startedAt: activeStep.started_at ?? undefined,
    }
  }

  const status = taskRun.status?.toUpperCase()
  if (!status || status === 'PENDING') return undefined

  return {
    taskId: taskRun.task_run_id,
    title: taskRun.title ?? '작업 진행 중',
    description: '',
    status: toTaskStatus(taskRun.status),
    startedAt: taskRun.created_at ?? undefined,
  }
}

function pickTaskHistory(taskRun: RawTaskRun, stepRuns: RawStepRun[]): VisualizationTask[] {
  const stepHistory = stepRuns
    .filter((sr) => TERMINAL_STATUSES.has(sr.status?.toUpperCase() ?? ''))
    .sort(
      (a, b) =>
        getTimestamp(b.completed_at ?? getStepRunEndedAt(b) ?? getStepRunUpdatedAt(b)) -
        getTimestamp(a.completed_at ?? getStepRunEndedAt(a) ?? getStepRunUpdatedAt(a)),
    )
    .map((sr) => ({
      taskId: sr.step_run_id,
      title: sr.title ?? '완료된 작업',
      description: '',
      status: toTaskStatus(sr.status),
      completedAt: sr.completed_at ?? getStepRunEndedAt(sr) ?? undefined,
    }))

  if (stepHistory.length > 0) return stepHistory.slice(0, 5)

  if (!TERMINAL_STATUSES.has(taskRun.status?.toUpperCase() ?? '')) {
    return []
  }

  const rawTaskRun = taskRun as Record<string, unknown>
  const taskEndedAt =
    typeof rawTaskRun.ended_at === 'string'
      ? rawTaskRun.ended_at
      : typeof rawTaskRun.endedAt === 'string'
        ? rawTaskRun.endedAt
        : undefined

  return [
    {
      taskId: taskRun.task_run_id,
      title: taskRun.title ?? '작업',
      description: '',
      status: toTaskStatus(taskRun.status),
      completedAt: taskRun.completed_at ?? taskEndedAt ?? taskRun.updated_at ?? undefined,
    },
  ]
}

export function useAgentInfoSync(sessionId?: string, profileIdMap?: Record<string, string>) {
  const taskRunsById = useTaskRunStore((s) => s.taskRunsById)
  const stepRunsById = useTaskRunStore((s) => s.stepRunsById)
  const fetchSessionTaskRuns = useTaskRunStore((s) => s.fetchSessionTaskRuns)
  const fetchSnapshot = useTaskRunStore((s) => s.fetchSnapshot)
  const updateAgentInfo = useAgentVisualizationStore((s) => s.updateAgentInfo)
  const selectedAgentId = useAgentVisualizationStore((s) => s.selectedAgentId)
  const fetchedTaskRunIds = useRef<Set<string>>(new Set())
  const fetchedSessionIds = useRef<Set<string>>(new Set())

  useEffect(() => {
    const sessionIds = new Set<string>()
    if (sessionId !== undefined && sessionId !== '') {
      sessionIds.add(sessionId)
    }

    for (const taskRun of Object.values(taskRunsById)) {
      if (typeof taskRun.session_id === 'string' && taskRun.session_id) {
        sessionIds.add(taskRun.session_id)
      }
    }

    for (const currentSessionId of sessionIds) {
      if (fetchedSessionIds.current.has(currentSessionId)) continue
      fetchedSessionIds.current.add(currentSessionId)

      void listSessionAgents(currentSessionId)
        .then((profiles) => {
          for (const profile of profiles) {
            // profileImage URL에서 spriteId(agentXX)를 추출해 키로 사용한다.
            // profileImage가 없으면 profileKey를 fallback으로 쓴다.
            const key = deriveSpriteId(profile.profileImage) ?? profile.profileKey
            if (!key) continue
            updateAgentInfo(key, {
              name: profile.name,
              role: profile.role,
              skills: profile.skills,
              ...(profile.profileImage ? { profileImage: profile.profileImage } : {}),
            })
          }
        })
        .catch(() => {})

      void getSessionMainAgent(currentSessionId)
        .then((profile) => {
          const profileData = {
            name: profile.name,
            role: profile.role,
            skills: profile.skills,
            ...(profile.profileImage ? { profileImage: profile.profileImage } : {}),
          }
          if (profile.profileKey) updateAgentInfo(profile.profileKey, profileData)
          updateAgentInfo('ceo', profileData)
        })
        .catch(() => {})

      void fetchSessionTaskRuns(currentSessionId).catch(() => {})
    }
  }, [fetchSessionTaskRuns, sessionId, taskRunsById, updateAgentInfo])

  useEffect(() => {
    const updatesBySpriteId = new Map<
      string,
      {
        latestTaskRun: RawTaskRun
        currentTask?: VisualizationTask
        taskHistory: VisualizationTask[]
      }
    >()

    const taskRuns = Object.values(taskRunsById).sort(
      (a, b) => getTaskRunSortTime(b) - getTaskRunSortTime(a),
    )

    for (const taskRun of taskRuns) {
      const spriteId = resolveSessionTaskRunSpriteId(taskRun, sessionId, profileIdMap)
      if (!spriteId) continue

      const agentStepRuns = Object.values(stepRunsById).filter(
        (sr) => sr.task_run_id === taskRun.task_run_id,
      )
      const currentTask = pickCurrentTask(taskRun, agentStepRuns)
      const taskHistory = pickTaskHistory(taskRun, agentStepRuns)
      const update = updatesBySpriteId.get(spriteId)

      if (update === undefined) {
        updatesBySpriteId.set(spriteId, {
          latestTaskRun: taskRun,
          currentTask,
          taskHistory,
        })
        continue
      }

      for (const task of taskHistory) {
        if (!update.taskHistory.some((existing) => existing.taskId === task.taskId)) {
          update.taskHistory.push(task)
        }
      }
    }

    for (const [spriteId, update] of updatesBySpriteId) {
      updateAgentInfo(spriteId, {
        activityStatus:
          update.currentTask !== undefined
            ? 'working'
            : toActivityStatus(update.latestTaskRun.status),
        currentTask: update.currentTask,
        ...(update.taskHistory.length > 0 ? { taskHistory: update.taskHistory.slice(0, 5) } : {}),
      })
    }
  }, [sessionId, taskRunsById, stepRunsById, updateAgentInfo, profileIdMap])

  useEffect(() => {
    if (!selectedAgentId) return

    const taskRun = Object.values(taskRunsById)
      .filter(
        (tr) => resolveSessionTaskRunSpriteId(tr, sessionId, profileIdMap) === selectedAgentId,
      )
      .sort((a, b) => getTaskRunSortTime(b) - getTaskRunSortTime(a))[0]
    if (!taskRun) return
    if (fetchedTaskRunIds.current.has(taskRun.task_run_id)) return

    fetchedTaskRunIds.current.add(taskRun.task_run_id)
    void fetchSnapshot(taskRun.task_run_id)
  }, [fetchSnapshot, selectedAgentId, sessionId, taskRunsById, profileIdMap])
}
