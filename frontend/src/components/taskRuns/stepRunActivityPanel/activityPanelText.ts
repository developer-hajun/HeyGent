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
      return status
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

export function toUserFacingTaskTitle(value?: string | null) {
  const text = typeof value === 'string' ? value.trim() : ''
  if (!text) {
    return '답변 준비'
  }

  const normalized = text.toLowerCase()
  if (normalized.includes('agent.loop') || normalized.includes('agent loop')) {
    return '질문에 대한 답변'
  }
  if (normalized.includes('taskrun') || normalized.includes('steprun')) {
    return '답변 진행'
  }
  return text
}

export function toProgressSentence(status?: string | null) {
  switch (status) {
    case 'PENDING':
    case 'accepted':
    case 'task.created':
      return '요청을 확인하고 있습니다.'
    case 'RUNNING':
    case 'step.started':
    case 'tool.started':
    case 'search.started':
    case 'session.message.delta':
      return '답변을 준비하는 중입니다.'
    case 'WAITING':
    case 'approval.required':
      return '추가 확인이 필요합니다.'
    case 'COMPLETED':
    case 'step.completed':
    case 'tool.completed':
    case 'search.completed':
    case 'session.message.completed':
      return '답변 준비가 완료되었습니다.'
    case 'FAILED':
      return '답변을 준비하는 중 문제가 발생했습니다.'
    case 'CANCELLED':
    case 'CANCELED':
      return '요청이 취소되었습니다.'
    default:
      return toTaskRunStatusText(status)
  }
}
