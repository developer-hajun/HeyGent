import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserInfo } from '@/apis/users'

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
      clearTokens: () =>
        set({ accessToken: null, refreshToken: null, isAuthenticated: false, userInfo: null }),
    }),
    {
      name: 'heygent-auth',
      // accessToken은 메모리에만, refreshToken만 localStorage에 유지
      partialize: (state) => ({ refreshToken: state.refreshToken }),
    },
  ),
)
