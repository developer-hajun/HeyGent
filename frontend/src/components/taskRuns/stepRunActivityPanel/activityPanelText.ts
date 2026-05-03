import type { ChatMessageView } from '@/types/aiChat'
import type { RawTaskRun } from '@/types/taskRuns'
import { toTaskRunStatusText } from '@/utils/taskRunStatusView'

export function getTime(value?: string | null) {
  if (value === undefined || value === null) {
    return 0
  }
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : 0
}

export function toApprovalStatusText(status?: string | null) {
  switch (status) {
    case 'APPROVED':
      return '승인됨'
    case 'REJECTED':
      return '거절됨'
    case 'CANCELLED':
      return '취소됨'
    case 'PENDING':
    case undefined:
    case null:
      return '대기 중'
    default:
      return '상태 확인 중'
  }
}

export function findPromptForTaskRun(messages: ChatMessageView[], taskRunId?: string) {
  if (taskRunId === undefined) {
    return undefined
  }

  return messages.find((message) => message.role === 'user' && message.taskRunId === taskRunId)
    ?.content
}

export function getAnswerProgressTitle(taskRun?: RawTaskRun, prompt?: string) {
  if (prompt !== undefined && prompt.trim() !== '') {
    return '질문에 대한 답변'
  }

  return toUserFacingTaskTitle(taskRun?.title ?? taskRun?.goal ?? '답변 준비')
}

// backend/raw payload의 agent loop, TaskRun, StepRun 같은 내부 이름을 사용자용 진행 문구로 숨긴다.
export function toUserFacingTaskTitle(value?: string | null) {
  const text = typeof value === 'string' ? value.trim() : ''
  if (!text) {
    return '답변 준비'
  }

  const normalized = text.toLowerCase().replaceAll(/[\s_-]+/g, '.')
  if (normalized.includes('agent.loop')) {
    return '질문에 대한 답변'
  }
  if (normalized.includes('taskrun') || normalized.includes('task.run')) {
    return '답변 진행'
  }
  if (normalized.includes('steprun') || normalized.includes('step.run')) {
    return '답변 진행'
  }
  return text
}

// TaskRun 상태값과 raw event_type이 섞여 들어와도 한곳에서 자연스러운 설명 문장으로 바꾼다.
export function toProgressSentence(status?: string | null) {
  switch (status) {
    case 'PENDING':
    case 'accepted':
    case 'task.created':
      return '요청을 확인하고 있습니다.'
    case 'RUNNING':
    case 'task.started':
      return '답변 흐름을 진행하고 있습니다.'
    case 'step.started':
      return '현재 단계를 처리하고 있습니다.'
    case 'tool.started':
      return '필요한 도구를 실행하고 있습니다.'
    case 'search.started':
      return '관련 자료를 확인하고 있습니다.'
    case 'session.message.delta':
      return '답변을 작성하고 있습니다.'
    case 'WAITING':
    case 'task.waiting':
    case 'step.waiting':
    case 'approval.required':
      return '추가 확인이 필요합니다.'
    case 'COMPLETED':
    case 'task.completed':
    case 'session.message.completed':
      return 'AI 답변이 완료되었습니다.'
    case 'step.completed':
      return '현재 단계를 완료했습니다.'
    case 'tool.completed':
      return '도구 실행을 완료했습니다.'
    case 'search.completed':
      return '자료 확인을 완료했습니다.'
    case 'FAILED':
    case 'task.failed':
    case 'step.failed':
      return '답변을 준비하는 중 문제가 발생했습니다.'
    case 'CANCELLED':
    case 'CANCELED':
    case 'task.canceled':
    case 'step.canceled':
      return '요청이 취소되었습니다.'
    default:
      return toTaskRunStatusText(status)
  }
}
