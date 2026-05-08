import { Key } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { LeftSidebar } from '@/components/layout/LeftSidebar'
import { TopNavBar } from '@/components/layout/TopNavBar'
import { RightPanel } from '@/components/layout/RightPanel'
import { DashboardPage } from '@/pages/DashboardPage'
import { AgentStatusPage } from '@/pages/AgentStatusPage'
import { BuildingOverviewPage } from '@/pages/BuildingOverviewPage'
import { NewChatPage } from '@/pages/NewChatPage'
import { ChatSessionPage } from '@/pages/ChatSessionPage'
import { LoginPage } from '@/pages/LoginPage'
import { KakaoCallbackPage } from '@/pages/KakaoCallbackPage'
import { NotionCallbackPage } from '@/pages/NotionCallbackPage'
import { AiRealtimeProvider } from '@/providers/AiRealtimeProvider'
import { useAuthStore } from '@/store/useAuthStore'
import { useUIStore } from '@/store/useUIStore'
import { getOpenAiProviders } from '@/apis/openaiProviders'

function ApiKeyOverlay() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const settingsOpen = useUIStore((s) => s.settingsOpen)
  const setSettingsOpen = useUIStore((s) => s.setSettingsOpen)
  const [dismissedFor, setDismissedFor] = useState<string | null>(null)
  const [hasNoApiKeys, setHasNoApiKeys] = useState(false)

  // 로그인한 유저가 바뀌면 dismissed 초기화 (파생값으로 처리)
  const dismissed = dismissedFor === (isAuthenticated ? 'yes' : null)

  const fetchProviderStatus = useCallback(() => {
    if (!isAuthenticated) return
    getOpenAiProviders()
      .then((res) => {
        const anyConnected = res.providers.some((p) => p.connected)
        setHasNoApiKeys(!anyConnected)
      })
      .catch(() => setHasNoApiKeys(false))
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    fetchProviderStatus()
  }, [isAuthenticated, fetchProviderStatus])

  useEffect(() => {
    if (!settingsOpen) fetchProviderStatus()
  }, [settingsOpen, fetchProviderStatus])

  if (!isAuthenticated || dismissed || !hasNoApiKeys || settingsOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 배경 딤 */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* 카드 */}
      <div className="bg-card border-border relative mx-4 w-full max-w-sm space-y-5 rounded-2xl border p-6 shadow-2xl">
        {/* 아이콘 */}
        <div className="flex justify-center">
          <div className="bg-muted flex h-12 w-12 items-center justify-center rounded-2xl">
            <Key className="text-muted-foreground h-6 w-6" />
          </div>
        </div>

        {/* 텍스트 */}
        <div className="space-y-1.5 text-center">
          <h2 className="text-foreground text-lg font-semibold">API 키를 등록해 주세요</h2>
          <p className="text-muted-foreground text-sm leading-6">
            서비스를 이용하려면 OpenAI, Anthropic 등의 API 키가 필요합니다. 지금 등록하면 바로
            사용할 수 있어요.
          </p>
        </div>

        {/* 버튼 */}
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => setSettingsOpen(true, 'apiKeys')}
            className="bg-foreground hover:bg-foreground/85 text-background w-full rounded-xl py-2.5 text-sm font-medium transition-colors"
          >
            API 키 등록하기
          </button>
          <button
            type="button"
            onClick={() => setDismissedFor('yes')}
            className="text-muted-foreground hover:text-foreground w-full rounded-xl py-2 text-sm transition-colors"
          >
            나중에 하기
          </button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/kakao/callback" element={<KakaoCallbackPage />} />
        <Route path="/auth/notion/callback" element={<NotionCallbackPage />} />
        <Route
          path="*"
          element={
            <>
              <RightPanel />
              <ApiKeyOverlay />
              <AiRealtimeProvider>
                <div className="bg-background flex h-screen w-full flex-col overflow-hidden">
                  <TopNavBar />
                  <div className="flex min-h-0 flex-1 overflow-hidden">
                    <LeftSidebar />
                    <Routes>
                      <Route path="/" element={<DashboardPage />} />
                      <Route path="/new-chat" element={<NewChatPage />} />
                      <Route path="/agent-status" element={<BuildingOverviewPage />} />
                      <Route path="/agent-status/:sessionId" element={<AgentStatusPage />} />
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
