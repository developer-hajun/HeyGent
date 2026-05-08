import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/index.css'

localStorage.removeItem('heygent-theme')
document.documentElement.classList.remove('dark')

createRoot(document.getElementById('root')!).render(<App />)
