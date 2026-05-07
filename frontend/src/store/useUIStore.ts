import { create } from 'zustand'

export const DEFAULT_SIDEBAR_WIDTH = 156

interface UIState {
  // 좌측 사이드바
  sidebarCollapsed: boolean
  settingsOpen: boolean
  settingsInitialTab: string
  setSidebarCollapsed: (collapsed: boolean) => void
  setSettingsOpen: (open: boolean, initialTab?: string) => void

  // 채팅 활동 패널
  taskActivityPanelOpen: boolean
  setTaskActivityPanelOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  settingsOpen: false,
  settingsInitialTab: 'general',
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setSettingsOpen: (open, initialTab) =>
    set({ settingsOpen: open, ...(initialTab ? { settingsInitialTab: initialTab } : {}) }),
  taskActivityPanelOpen: false,
  setTaskActivityPanelOpen: (open) => set({ taskActivityPanelOpen: open }),
}))
