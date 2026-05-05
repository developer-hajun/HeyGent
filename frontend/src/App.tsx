import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { LeftSidebar } from '@/components/layout/LeftSidebar'
import { TopNavBar } from '@/components/layout/TopNavBar'
import { RightPanel } from '@/components/layout/RightPanel'
import { DashboardPage } from '@/pages/DashboardPage'
import { AgentStatusPage } from '@/pages/AgentStatusPage'
import { NewChatPage } from '@/pages/NewChatPage'
import { ChatSessionPage } from '@/pages/ChatSessionPage'
import { LoginPage } from '@/pages/LoginPage'
import { KakaoCallbackPage } from '@/pages/KakaoCallbackPage'
import { AiRealtimeProvider } from '@/providers/AiRealtimeProvider'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/kakao/callback" element={<KakaoCallbackPage />} />
        <Route
          path="*"
          element={
            <>
              <RightPanel />
              <AiRealtimeProvider>
                <div className="bg-background flex h-screen w-full flex-col overflow-hidden">
                  <TopNavBar />
                  <div className="flex min-h-0 flex-1 overflow-hidden">
                    <LeftSidebar />
                    <Routes>
                      <Route path="/" element={<DashboardPage />} />
                      <Route path="/new-chat" element={<NewChatPage />} />
                      <Route path="/agent-status" element={<AgentStatusPage />} />
                      <Route path="/session/:sessionId" element={<ChatSessionPage />} />
                      <Route path="/chat" element={<Navigate to="/new-chat" replace />} />
                      <Route path="/agents" element={<Navigate to="/agent-status" replace />} />
                      <Route path="/reminders" element={<Navigate to="/" replace />} />
                      <Route path="/wellness" element={<Navigate to="/" replace />} />
                      <Route path="/devices" element={<Navigate to="/" replace />} />
                      <Route path="/settings" element={<Navigate to="/" replace />} />
                    </Routes>
                  </div>
                </div>
              </AiRealtimeProvider>
            </>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
