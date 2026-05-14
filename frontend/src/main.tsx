import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/index.css'

// 저장된 테마를 React 렌더링 전에 적용해 깜박임 방지
let initialTheme: 'dark' | 'light' = 'dark'
try {
  const saved = JSON.parse(localStorage.getItem('heygent-ui-state') ?? '{}')
  initialTheme = saved?.state?.theme === 'light' || saved?.theme === 'light' ? 'light' : 'dark'
} catch {
  initialTheme = 'dark'
}
document.documentElement.classList.toggle('dark', initialTheme === 'dark')

// favicon 초기 적용 — 앱 테마 기준 (OS prefers-color-scheme 와 별개로 즉시 일치)
// 파일 이름은 로고 색상을 의미 (다크 모드 → 밝은 색 로고)
{
  const path = initialTheme === 'dark' ? '/favicon_dark.png' : '/favicon_light.png'
  const href = `${path}?v=${Date.now()}`

  // 정적 HTML 의 prefers-color-scheme favicon link 모두 제거 (앱 테마 우선)
  document
    .querySelectorAll<HTMLLinkElement>('link[rel~="icon"]:not([data-app])')
    .forEach((el) => el.remove())

  const appLink = document.createElement('link')
  appLink.rel = 'icon'
  appLink.type = 'image/png'
  appLink.setAttribute('sizes', 'any')
  appLink.dataset.app = '1'
  appLink.href = href
  document.head.appendChild(appLink)
}

createRoot(document.getElementById('root')!).render(<App />)
