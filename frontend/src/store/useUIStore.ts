import { create } from 'zustand'

const MIN_WIDTH = 220
const MAX_WIDTH = 420
export const DEFAULT_SIDEBAR_WIDTH = 280

interface UIState {
  // 좌측 사이드바
  sidebarCollapsed: boolean
  sidebarWidth: number
  settingsOpen: boolean
  settingsInitialTab: string
  setSidebarCollapsed: (collapsed: boolean) => void
  setSidebarWidth: (width: number) => void
  clampSidebarWidth: (width: number) => void
  setSettingsOpen: (open: boolean, initialTab?: string) => void

  // 채팅 활동 패널
  taskActivityPanelOpen: boolean
  setTaskActivityPanelOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
  settingsOpen: false,
  settingsInitialTab: 'general',
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setSidebarWidth: (width) => set({ sidebarWidth: width }),
  clampSidebarWidth: (width) =>
    set({ sidebarWidth: Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width)) }),
  setSettingsOpen: (open, initialTab) =>
    set({ settingsOpen: open, ...(initialTab ? { settingsInitialTab: initialTab } : {}) }),
  taskActivityPanelOpen: false,
  setTaskActivityPanelOpen: (open) => set({ taskActivityPanelOpen: open }),
}))
