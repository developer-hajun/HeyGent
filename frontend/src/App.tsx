import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { LeftSidebar } from './components/layout/LeftSidebar'
import { TopNavBar } from './components/layout/TopNavBar'
import { RightPanel } from './components/layout/RightPanel'
import { DashboardPage } from './pages/DashboardPage'
import { AgentStatusPage } from './pages/AgentStatusPage'
import { SessionChatPage } from './pages/SessionChatPage'
import { useState } from 'react'
import type { Agent } from './components/layout/RightPanel'

export default function App() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  return (
    <BrowserRouter>
      {/* Fixed right-side floating tabs */}
      <RightPanel selectedAgent={selectedAgent} onCloseAgent={() => setSelectedAgent(null)} />

      <div className="bg-background flex size-full flex-col">
        <TopNavBar />

        <div className="flex flex-1 overflow-hidden">
          <LeftSidebar />

          <Routes>
            <Route path="/" element={<DashboardPage onAgentSelect={setSelectedAgent} />} />
            <Route path="/agent-status" element={<AgentStatusPage />} />
            <Route path="/session/:sessionId" element={<SessionChatPage />} />

            {/* Legacy redirects */}
            <Route path="/chat" element={<Navigate to="/" replace />} />
            <Route path="/agents" element={<Navigate to="/agent-status" replace />} />
            <Route path="/reminders" element={<Navigate to="/" replace />} />
            <Route path="/wellness" element={<Navigate to="/" replace />} />
            <Route path="/devices" element={<Navigate to="/" replace />} />
            <Route path="/settings" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
