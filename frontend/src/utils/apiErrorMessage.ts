import { isAxiosError } from 'axios'

type ErrorMessageOptions = {
  fallback: string
}

export function getApiErrorMessage(error: unknown, options: ErrorMessageOptions): string {
  if (!isAxiosError(error)) {
    return error instanceof Error && error.message.trim() !== '' ? error.message : options.fallback
  }

  const status = error.response?.status
  const detail = readDetailMessage(error.response?.data)

  if (status === 409) {
    return getConflictMessage(detail)
  }

  if (detail) {
    return detail
  }

  if (status === 401) {
    return '로그인이 만료되었습니다. 다시 로그인해 주세요.'
  }

  if (status === 403) {
    return '이 작업을 수행할 권한이 없습니다.'
  }

  if (status === 404) {
    return '요청한 대상을 찾지 못했습니다.'
  }

  return options.fallback
}

function getConflictMessage(detail: string | null): string {
  if (
    detail?.includes('active task already exists') ||
    detail?.includes('session has a running task')
  ) {
    return '이 세션에서 다른 작업이 실행 중입니다. 현재 실행이 끝나거나 취소된 뒤 다시 시도해 주세요.'
  }

  if (detail?.includes('work already has an active run')) {
    return '이 작업은 이미 실행 중입니다. 현재 실행이 끝난 뒤 다시 시도해 주세요.'
  }

  if (detail?.includes('blocked by unresolved blockers')) {
    return '먼저 완료해야 하는 연결 작업이 있습니다. 차단 작업을 끝낸 뒤 다시 실행해 주세요.'
  }

  return detail ?? '요청이 현재 작업 상태와 충돌했습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.'
}

function readDetailMessage(data: unknown): string | null {
  if (typeof data === 'string') {
    return data.trim() || null
  }

  if (typeof data !== 'object' || data === null) {
    return null
  }

  const record = data as Record<string, unknown>
  const detail = record.detail
  if (typeof detail === 'string') {
    return detail.trim() || null
  }
  if (typeof detail === 'object' && detail !== null) {
    const message = (detail as Record<string, unknown>).message
    return typeof message === 'string' && message.trim() !== '' ? message.trim() : null
  }

  const message = record.message
  return typeof message === 'string' && message.trim() !== '' ? message.trim() : null
}
