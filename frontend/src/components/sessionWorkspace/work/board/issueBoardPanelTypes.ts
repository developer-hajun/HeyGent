import type { LucideIcon } from 'lucide-react'
import type { IssueBoardIssue, IssueBoardLabel, IssueBoardStatus } from '../model/issueBoardModel'

export type ViewMode = 'list' | 'board' | 'flow'
export type SortField = 'updated' | 'title' | 'status'
export type DetailTab =
  | 'chat'
  | 'runs'
  | 'activity'
  | 'related'
  | 'documents'
  | 'products'
  | 'interactions'
  | 'recovery'

export type BoardAssignee = {
  id: string
  name: string
  icon: LucideIcon
  templateKey?: string
}

export interface PersistedTodoBoardState {
  issues: IssueBoardIssue[]
  labels: IssueBoardLabel[]
  query: string
  viewMode: ViewMode
  sortField: SortField
  selectedStatuses: IssueBoardStatus[]
  selectedAssignees: string[]
  selectedLabels: string[]
  liveOnly: boolean
}
