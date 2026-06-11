import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserInfo } from '@/apis/users'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useChatStore } from '@/store/useChatStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  userInfo: UserInfo | null
  setTokens: (accessToken: string, refreshToken: string) => void
  setUserInfo: (userInfo: UserInfo) => void
  clearTokens: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      userInfo: null,
      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken, isAuthenticated: true }),
      setUserInfo: (userInfo) => set({ userInfo }),
      clearTokens: () => {
        useAiRealtimeStore.getState().resetRealtimeState()
        useChatStore.getState().clearChatState()
        useTaskRunStore.getState().clearTaskRunState()
        set({ accessToken: null, refreshToken: null, isAuthenticated: false, userInfo: null })
      },
    }),
    {
      name: 'heygent-auth',
      // 새로고침 후에도 AI WebSocket auth.start를 바로 보낼 수 있게 accessToken도 로그아웃 전까지 유지한다.
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        userInfo: state.userInfo,
      }),
    },
  ),
)
