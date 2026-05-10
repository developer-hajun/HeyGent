import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/index.css'

// 저장된 테마를 React 렌더링 전에 적용해 깜박임 방지
try {
  const saved = JSON.parse(localStorage.getItem('heygent-ui-state') ?? '{}')
  document.documentElement.classList.toggle('dark', (saved?.theme ?? 'dark') === 'dark')
} catch {
  document.documentElement.classList.add('dark')
}

createRoot(document.getElementById('root')!).render(<App />)
