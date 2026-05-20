import { useMemo } from 'react'
import { Bot, UserRound } from 'lucide-react'
import { useSessionStore } from '@/store/useSessionStore'
import type { BoardAssignee } from './issueBoardPanelTypes'
import { WorkflowTemplateEditor } from './WorkflowTemplateEditor'

const MAIN_AGENT_ASSIGNEE: BoardAssignee = {
  id: 'CEO',
  name: '팀장 에이전트',
  icon: UserRound,
  imageUrl: '/assets/agents/ceo/ceo_profile_img.png',
}

const EMPTY_AGENT_PANELS: ReturnType<
  typeof useSessionStore.getState
>['agentPanelsBySessionId'][string] = []

export function WorkflowPanel({ sessionId }: { sessionId: string }) {
  const agentPanelsBySessionId = useSessionStore((state) => state.agentPanelsBySessionId)
  const assignees = useMemo<BoardAssignee[]>(() => {
    const agentPanels = agentPanelsBySessionId[sessionId] ?? EMPTY_AGENT_PANELS
    return [
      MAIN_AGENT_ASSIGNEE,
      ...agentPanels.map((panel) => ({
        id: panel.id,
        name: panel.agent.name,
        icon: Bot,
        templateKey: panel.agent.templateKey,
        imageUrl: panel.agent.profileImage ?? null,
      })),
    ]
  }, [agentPanelsBySessionId, sessionId])

  return (
    <div className="bg-background flex h-full min-h-0 w-full flex-col">
      <WorkflowTemplateEditor assignees={assignees} sessionId={sessionId} />
    </div>
  )
}
