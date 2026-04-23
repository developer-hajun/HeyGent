import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/index.css'

// Apply theme class before first render to prevent flash of wrong theme
const savedTheme = localStorage.getItem('heygent-theme') ?? 'dark'
if (savedTheme === 'dark') {
  document.documentElement.classList.add('dark')
} else {
  document.documentElement.classList.remove('dark')
}

createRoot(document.getElementById('root')!).render(<App />)
