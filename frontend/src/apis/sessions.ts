import aiAxiosInstance from './aiAxiosInstance'
import type { AiSessionSettingsPatch, RawAiSession } from '@/types/aiChat'
import type { JsonObject } from '@/realtime/aiRealtimeTypes'

type CreateSessionInput = {
  title?: string
  model?: string
  settings?: AiSessionSettingsPatch
  metadataPatch?: JsonObject
}

export async function createSession(input: CreateSessionInput): Promise<RawAiSession> {
  const { data } = await aiAxiosInstance.post<Record<string, unknown>>('/sessions', input)
  return normalizeSession(data)
}

function normalizeSession(data: Record<string, unknown>): RawAiSession {
  const sessionId = getString(data.session_id) ?? getString(data.sessionId)
  if (sessionId === null) {
    throw new Error('세션 응답에 sessionId가 없습니다.')
  }
  return {
    ...data,
    session_id: sessionId,
    archived_at: getNullableString(data.archived_at, data.archivedAt),
    deleted_at: getNullableString(data.deleted_at, data.deletedAt),
    created_at: getNullableString(data.created_at, data.createdAt),
    updated_at: getNullableString(data.updated_at, data.updatedAt),
    metadata: isRecord(data.metadata) ? data.metadata : null,
    settings: isRecord(data.settings) ? data.settings : null,
  }
}

function getNullableString(...values: unknown[]): string | null | undefined {
  for (const value of values) {
    if (typeof value === 'string') return value
    if (value === null) return null
  }
  return undefined
}

function getString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() !== '' ? value : null
}

function isRecord(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
