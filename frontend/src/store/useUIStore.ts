import { create } from 'zustand'

const MIN_WIDTH = 220
const MAX_WIDTH = 420
export const DEFAULT_SIDEBAR_WIDTH = 280

type RightPanelType = 'schedule' | 'agent' | null

interface UIState {
  // 좌측 사이드바
  sidebarCollapsed: boolean
  sidebarWidth: number
  settingsOpen: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  setSidebarWidth: (width: number) => void
  clampSidebarWidth: (width: number) => void
  setSettingsOpen: (open: boolean) => void

  // 우측 패널
  rightPanelType: RightPanelType
  setRightPanelType: (type: RightPanelType) => void
  toggleRightPanel: (type: Exclude<RightPanelType, null>) => void

  // 현재 활성 페이지 경로
  activePage: string
  setActivePage: (path: string) => void
}

export const useUIStore = create<UIState>((set, get) => ({
  sidebarCollapsed: false,
  sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
  settingsOpen: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setSidebarWidth: (width) => set({ sidebarWidth: width }),
  clampSidebarWidth: (width) =>
    set({ sidebarWidth: Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width)) }),
  setSettingsOpen: (open) => set({ settingsOpen: open }),

  rightPanelType: null,
  setRightPanelType: (type) => set({ rightPanelType: type }),
  toggleRightPanel: (type) => set({ rightPanelType: get().rightPanelType === type ? null : type }),

  activePage: '/',
  setActivePage: (path) => set({ activePage: path }),
}))
