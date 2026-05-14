import { useEffect, useRef } from 'react'
import { listSessionAgents, getSessionMainAgent } from '@/apis/agents'
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

function resolveTaskRunProfileKey(taskRun: RawTaskRun): string | null {
  const actorAgent = taskRun.displayContext?.actorAgent
  return actorAgent?.profileKey ?? (actorAgent?.kind === 'main' ? 'ceo' : null)
}

function resolveSessionTaskRunProfileKey(taskRun: RawTaskRun, sessionId?: string): string | null {
  return (
    resolveTaskRunProfileKey(taskRun) ??
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
      description: typeof activeStep.goal === 'string' ? activeStep.goal : '',
      status: 'in_progress',
      startedAt: activeStep.started_at ?? undefined,
    }
  }

  const status = taskRun.status?.toUpperCase()
  if (!status || status === 'PENDING') return undefined

  return {
    taskId: taskRun.task_run_id,
    title: taskRun.title ?? '작업 진행 중',
    description: typeof taskRun.goal === 'string' ? taskRun.goal : '',
    status: toTaskStatus(taskRun.status),
    startedAt: taskRun.created_at ?? undefined,
  }
}

function pickTaskHistory(taskRun: RawTaskRun, stepRuns: RawStepRun[]): VisualizationTask[] {
  const stepHistory = stepRuns
    .filter((sr) => TERMINAL_STATUSES.has(sr.status?.toUpperCase() ?? ''))
    .sort(
      (a, b) =>
        getTimestamp(b.completed_at ?? getStepRunUpdatedAt(b)) -
        getTimestamp(a.completed_at ?? getStepRunUpdatedAt(a)),
    )
    .map((sr) => ({
      taskId: sr.step_run_id,
      title: sr.title ?? '완료된 작업',
      description: '',
      status: toTaskStatus(sr.status),
      completedAt: sr.completed_at ?? undefined,
    }))

  if (stepHistory.length > 0) return stepHistory.slice(0, 5)

  if (!TERMINAL_STATUSES.has(taskRun.status?.toUpperCase() ?? '')) {
    return []
  }

  return [
    {
      taskId: taskRun.task_run_id,
      title: taskRun.title ?? '작업',
      description: typeof taskRun.goal === 'string' ? taskRun.goal : '',
      status: toTaskStatus(taskRun.status),
      completedAt: taskRun.completed_at ?? taskRun.updated_at ?? undefined,
    },
  ]
}

export function useAgentInfoSync(sessionId?: string) {
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
            if (!profile.profileKey) continue
            updateAgentInfo(profile.profileKey, {
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
    const updatesByProfileKey = new Map<
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
      const profileKey = resolveSessionTaskRunProfileKey(taskRun, sessionId)
      if (!profileKey) continue

      const agentStepRuns = Object.values(stepRunsById).filter(
        (sr) => sr.task_run_id === taskRun.task_run_id,
      )
      const currentTask = pickCurrentTask(taskRun, agentStepRuns)
      const taskHistory = pickTaskHistory(taskRun, agentStepRuns)
      const update = updatesByProfileKey.get(profileKey)

      if (update === undefined) {
        updatesByProfileKey.set(profileKey, {
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

    for (const [profileKey, update] of updatesByProfileKey) {
      updateAgentInfo(profileKey, {
        activityStatus:
          update.currentTask !== undefined
            ? 'working'
            : toActivityStatus(update.latestTaskRun.status),
        currentTask: update.currentTask,
        ...(update.taskHistory.length > 0 ? { taskHistory: update.taskHistory.slice(0, 5) } : {}),
      })
    }
  }, [sessionId, taskRunsById, stepRunsById, updateAgentInfo])

  useEffect(() => {
    if (!selectedAgentId) return

    const taskRun = Object.values(taskRunsById)
      .filter((tr) => resolveSessionTaskRunProfileKey(tr, sessionId) === selectedAgentId)
      .sort((a, b) => getTaskRunSortTime(b) - getTaskRunSortTime(a))[0]
    if (!taskRun) return
    if (fetchedTaskRunIds.current.has(taskRun.task_run_id)) return

    fetchedTaskRunIds.current.add(taskRun.task_run_id)
    void fetchSnapshot(taskRun.task_run_id)
  }, [fetchSnapshot, selectedAgentId, sessionId, taskRunsById])
}
