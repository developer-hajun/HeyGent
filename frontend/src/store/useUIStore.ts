import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const DEFAULT_SIDEBAR_WIDTH = 195
export const DEFAULT_SIDEBAR_COLLAPSED_WIDTH = 64

// 앱 테마 토글 시 favicon 도 함께 교체.
// 파일 이름은 로고 색상을 의미:
//  - favicon_dark.png  = 어두운 색 로고 → 라이트 모드(밝은 배경)에 사용
//  - favicon_light.png = 밝은 색 로고 → 다크 모드(어두운 배경)에 사용
function applyFavicon(theme: 'dark' | 'light') {
  const path = theme === 'dark' ? '/favicon_light.png' : '/favicon_dark.png'
  // cache-busting — 브라우저 favicon 캐시 강제 무효화
  const href = `${path}?v=${Date.now()}`

  // 1. 정적 HTML 의 prefers-color-scheme 기반 favicon link 모두 제거
  //    (OS 테마와 앱 테마가 다를 때 브라우저가 정적 link 를 우선해서 동적 갱신이 무시되는 문제 방지)
  document
    .querySelectorAll<HTMLLinkElement>('link[rel~="icon"]:not([data-app])')
    .forEach((el) => el.remove())

  // 2. 동적 (data-app="1") favicon link 갱신
  let appLink = document.querySelector<HTMLLinkElement>('link[rel="icon"][data-app="1"]')
  if (!appLink) {
    appLink = document.createElement('link')
    appLink.rel = 'icon'
    appLink.type = 'image/png'
    appLink.dataset.app = '1'
    document.head.appendChild(appLink)
  }
  appLink.setAttribute('sizes', 'any')
  appLink.href = href

  // 3. shortcut icon (구형 브라우저 호환)
  let shortcut = document.querySelector<HTMLLinkElement>('link[rel="shortcut icon"][data-app="1"]')
  if (!shortcut) {
    shortcut = document.createElement('link')
    shortcut.rel = 'shortcut icon'
    shortcut.dataset.app = '1'
    document.head.appendChild(shortcut)
  }
  shortcut.href = href

  // 4. apple-touch-icon 도 동기 갱신 (홈 화면 바로가기용)
  let touch = document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"][data-app="1"]')
  if (!touch) {
    touch = document.createElement('link')
    touch.rel = 'apple-touch-icon'
    touch.dataset.app = '1'
    document.head.appendChild(touch)
  }
  touch.href = href
}

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
      setTheme: (theme) => {
        document.documentElement.classList.toggle('dark', theme === 'dark')
        applyFavicon(theme)
        set({ theme })
      },
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
