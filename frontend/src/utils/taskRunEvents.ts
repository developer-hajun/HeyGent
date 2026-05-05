import type { RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'

export type TaskRunEventMergeResult = {
  events: RawTaskEventPayload[]
  addedEvents: RawTaskEventPayload[]
  duplicateEvents: RawTaskEventPayload[]
  hasGap: boolean
  expectedSequence?: number
  lastSequence?: number
}

export const getTaskEventId = (event: RawTaskEventPayload) => event.event_id

export const getTaskEventSequence = (event: RawTaskEventPayload) =>
  typeof event.sequence === 'number' && Number.isFinite(event.sequence) ? event.sequence : undefined

export const getTaskEventTaskRunId = (event: RawTaskEventPayload) => event.task_run_id

// 서버 event_id를 우선 dedupe 기준으로 삼고, sequence는 replay gap 감지에만 사용한다.
export const mergeTaskRunEvents = (
  currentEvents: RawTaskEventPayload[],
  incomingEvents: RawTaskEventPayload[],
): TaskRunEventMergeResult => {
  const eventIds = new Set(currentEvents.map(getTaskEventId))
  const merged = [...currentEvents]
  const addedEvents: RawTaskEventPayload[] = []
  const duplicateEvents: RawTaskEventPayload[] = []
  let hasGap = false
  let expectedSequence: number | undefined
  let lastSequence = getLastTaskRunSequence(currentEvents)

  incomingEvents.forEach((event) => {
    if (eventIds.has(event.event_id)) {
      duplicateEvents.push(event)
      return
    }

    const sequence = getTaskEventSequence(event)
    if (
      sequence !== undefined &&
      lastSequence !== undefined &&
      sequence > lastSequence + 1 &&
      !hasGap
    ) {
      hasGap = true
      expectedSequence = lastSequence + 1
    }

    if (sequence !== undefined) {
      lastSequence = Math.max(lastSequence ?? sequence, sequence)
    }

    eventIds.add(event.event_id)
    merged.push(event)
    addedEvents.push(event)
  })

  return {
    events: sortTaskRunEvents(merged),
    addedEvents,
    duplicateEvents,
    hasGap,
    expectedSequence,
    lastSequence,
  }
}

export const sortTaskRunEvents = (events: RawTaskEventPayload[]) =>
  [...events].sort((first, second) => {
    const firstSequence = getTaskEventSequence(first)
    const secondSequence = getTaskEventSequence(second)

    if (firstSequence !== undefined && secondSequence !== undefined) {
      return firstSequence - secondSequence
    }

    if (firstSequence !== undefined) {
      return -1
    }

    if (secondSequence !== undefined) {
      return 1
    }

    return first.event_id.localeCompare(second.event_id)
  })

export const getLastTaskRunSequence = (events: RawTaskEventPayload[]) =>
  events.reduce<number | undefined>((lastSequence, event) => {
    const sequence = getTaskEventSequence(event)
    if (sequence === undefined) {
      return lastSequence
    }
    return Math.max(lastSequence ?? sequence, sequence)
  }, undefined)

export const shouldReplayTaskRunEvents = (
  currentEvents: RawTaskEventPayload[],
  incomingEvent: RawTaskEventPayload,
) => {
  const lastSequence = getLastTaskRunSequence(currentEvents)
  const incomingSequence = getTaskEventSequence(incomingEvent)

  return (
    lastSequence !== undefined &&
    incomingSequence !== undefined &&
    incomingSequence > lastSequence + 1
  )
}
