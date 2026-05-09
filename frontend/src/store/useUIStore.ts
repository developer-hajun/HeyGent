import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const DEFAULT_SIDEBAR_WIDTH = 260
export const DEFAULT_SIDEBAR_COLLAPSED_WIDTH = 64

interface UIState {
  // 좌측 사이드바
  sidebarCollapsed: boolean
  sessionWorkspaceCollapsed: boolean
  settingsOpen: boolean
  settingsInitialTab: string
  setSidebarCollapsed: (collapsed: boolean) => void
  setSessionWorkspaceCollapsed: (collapsed: boolean) => void
  setSettingsOpen: (open: boolean, initialTab?: string) => void

  // 채팅 활동 패널
  taskActivityPanelOpen: boolean
  setTaskActivityPanelOpen: (open: boolean) => void

  // 테마
  theme: 'dark' | 'light'
  setTheme: (theme: 'dark' | 'light') => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      sessionWorkspaceCollapsed: false,
      settingsOpen: false,
      settingsInitialTab: 'general',
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setSessionWorkspaceCollapsed: (collapsed) => set({ sessionWorkspaceCollapsed: collapsed }),
      setSettingsOpen: (open, initialTab) =>
        set({ settingsOpen: open, ...(initialTab ? { settingsInitialTab: initialTab } : {}) }),
      taskActivityPanelOpen: false,
      setTaskActivityPanelOpen: (open) => set({ taskActivityPanelOpen: open }),
      theme: 'dark',
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'heygent-ui-state',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        sessionWorkspaceCollapsed: state.sessionWorkspaceCollapsed,
        theme: state.theme,
      }),
    },
  ),
)
