import { useEffect, useRef } from 'react'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import { useAgentVisualizationStore } from '@/store/useAgentVisualizationStore'
import { listSessionAgents, getSessionMainAgent } from '@/apis/agents'
import type { AgentActivityStatus, TaskStatus, VisualizationTask } from '@/components/office/types'
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

function pickCurrentTask(
  taskRun: RawTaskRun,
  stepRuns: RawStepRun[],
): VisualizationTask | undefined {
  if (TERMINAL_STATUSES.has(taskRun.status?.toUpperCase() ?? '')) return undefined

  // 현재 실행 중인 step (step_order 높은 순)
  const activeStep = stepRuns
    .filter((sr) => sr.status === 'RUNNING' || sr.status === 'WAITING')
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

  // 활성 step 없으면 task run 자체 title 사용
  const s = taskRun.status?.toUpperCase()
  if (!s || s === 'PENDING') return undefined

  return {
    taskId: taskRun.task_run_id,
    title: taskRun.title ?? '작업 진행 중',
    description: typeof taskRun.goal === 'string' ? taskRun.goal : '',
    status: toTaskStatus(taskRun.status),
    startedAt: taskRun.created_at ?? undefined,
  }
}

function pickTaskHistory(stepRuns: RawStepRun[]): VisualizationTask[] {
  return stepRuns
    .filter((sr) => sr.status === 'COMPLETED')
    .sort(
      (a, b) => new Date(b.completed_at ?? 0).getTime() - new Date(a.completed_at ?? 0).getTime(),
    )
    .slice(0, 5)
    .map((sr) => ({
      taskId: sr.step_run_id,
      title: sr.title ?? '완료된 작업',
      description: '',
      status: 'completed' as TaskStatus,
      completedAt: sr.completed_at ?? undefined,
    }))
}

/**
 * useTaskRunStore의 snapshot 데이터를 useAgentVisualizationStore의 agentInfoMap에 반영한다.
 * - 세션 첫 진입 시 agents REST API로 name/role/skills/profileImage 로드
 * - taskRunsById/stepRunsById 변화 → activityStatus, currentTask, taskHistory 갱신
 * - 에이전트 선택 시 fetchSnapshot 호출 → 상세 step 데이터 로드 (Spec 3 연동)
 */
export function useAgentInfoSync() {
  const taskRunsById = useTaskRunStore((s) => s.taskRunsById)
  const stepRunsById = useTaskRunStore((s) => s.stepRunsById)
  const fetchSnapshot = useTaskRunStore((s) => s.fetchSnapshot)
  const updateAgentInfo = useAgentVisualizationStore((s) => s.updateAgentInfo)
  const selectedAgentId = useAgentVisualizationStore((s) => s.selectedAgentId)
  const fetchedTaskRunIds = useRef<Set<string>>(new Set())
  const fetchedSessionIds = useRef<Set<string>>(new Set())

  // 세션 첫 진입 시 에이전트 프로필(name/role/skills/profileImage) REST API 로드
  useEffect(() => {
    const sessionIds = new Set<string>()
    for (const taskRun of Object.values(taskRunsById)) {
      if (typeof taskRun.session_id === 'string' && taskRun.session_id) {
        sessionIds.add(taskRun.session_id)
      }
    }

    for (const sessionId of sessionIds) {
      if (fetchedSessionIds.current.has(sessionId)) continue
      fetchedSessionIds.current.add(sessionId)

      void listSessionAgents(sessionId)
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

      void getSessionMainAgent(sessionId)
        .then((profile) => {
          const profileData = {
            name: profile.name,
            role: profile.role,
            skills: profile.skills,
            ...(profile.profileImage ? { profileImage: profile.profileImage } : {}),
          }
          // REST API profileKey와 시각화 키('ceo') 양쪽에 동기화
          if (profile.profileKey) updateAgentInfo(profile.profileKey, profileData)
          updateAgentInfo('ceo', profileData)
        })
        .catch(() => {})
    }
  }, [taskRunsById, updateAgentInfo])

  // task run 상태·스텝 변화 → agentInfoMap 갱신 (동적 필드만 덮어씀)
  useEffect(() => {
    for (const taskRun of Object.values(taskRunsById)) {
      const actorAgent = taskRun.displayContext?.actorAgent
      // CEO(kind='main')는 profileKey가 null이므로 'ceo'로 대체
      const profileKey = actorAgent?.profileKey ?? (actorAgent?.kind === 'main' ? 'ceo' : null)
      if (!profileKey) continue

      const agentStepRuns = Object.values(stepRunsById).filter(
        (sr) => sr.task_run_id === taskRun.task_run_id,
      )
      const taskHistory = pickTaskHistory(agentStepRuns)

      updateAgentInfo(profileKey, {
        activityStatus: toActivityStatus(taskRun.status),
        currentTask: pickCurrentTask(taskRun, agentStepRuns),
        ...(taskHistory.length > 0 ? { taskHistory } : {}),
      })
    }
  }, [taskRunsById, stepRunsById, updateAgentInfo])

  // 에이전트 선택 시 snapshot 조회 → 상세 step 데이터 로드
  useEffect(() => {
    if (!selectedAgentId) return

    const taskRun = Object.values(taskRunsById).find((tr) => {
      const agent = tr.displayContext?.actorAgent
      const key = agent?.profileKey ?? (agent?.kind === 'main' ? 'ceo' : null)
      return key === selectedAgentId
    })
    if (!taskRun) return
    if (fetchedTaskRunIds.current.has(taskRun.task_run_id)) return

    fetchedTaskRunIds.current.add(taskRun.task_run_id)
    void fetchSnapshot(taskRun.task_run_id)
  }, [selectedAgentId, taskRunsById, fetchSnapshot])
}
