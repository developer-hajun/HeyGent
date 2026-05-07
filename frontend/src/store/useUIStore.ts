import { create } from 'zustand'

export const DEFAULT_SIDEBAR_WIDTH = 260
export const DEFAULT_SIDEBAR_COLLAPSED_WIDTH = 48

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
}

export const useUIStore = create<UIState>((set) => ({
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
}))
