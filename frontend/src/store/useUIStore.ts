import { create } from 'zustand'

const MIN_WIDTH = 220
const MAX_WIDTH = 420
export const DEFAULT_SIDEBAR_WIDTH = 280

type RightPanelType = 'schedule' | 'agent' | null
type Theme = 'light' | 'dark'

interface UIState {
  // 테마
  theme: Theme
  setTheme: (theme: Theme) => void

  // 좌측 사이드바
  sidebarCollapsed: boolean
  sidebarWidth: number
  settingsOpen: boolean
  settingsInitialTab: string
  setSidebarCollapsed: (collapsed: boolean) => void
  setSidebarWidth: (width: number) => void
  clampSidebarWidth: (width: number) => void
  setSettingsOpen: (open: boolean, initialTab?: string) => void

  // 우측 패널
  rightPanelType: RightPanelType
  setRightPanelType: (type: RightPanelType) => void
  toggleRightPanel: (type: Exclude<RightPanelType, null>) => void
}

export const useUIStore = create<UIState>((set, get) => ({
  theme: (localStorage.getItem('heygent-theme') as Theme) ?? 'dark',
  setTheme: (theme) => {
    localStorage.setItem('heygent-theme', theme)
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    set({ theme })
  },

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

  rightPanelType: null,
  setRightPanelType: (type) => set({ rightPanelType: type }),
  toggleRightPanel: (type) => set({ rightPanelType: get().rightPanelType === type ? null : type }),
}))
