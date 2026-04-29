import { LayoutDashboard, Activity, Sun, Moon } from 'lucide-react'
import { NavLink } from 'react-router'
import { useUIStore } from '@/store/useUIStore'

export function TopNavBar() {
  const { theme, setTheme } = useUIStore()

  return (
    <div className="z-40 flex h-14 shrink-0 items-center justify-between border-b border-white/10 bg-[#111111] px-6">
      {/* Left: Logo + Nav */}
      <div className="flex items-center gap-16">
        {/* Logo */}
        <span
          className="text-white select-none"
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '22px',
            fontWeight: 900,
            letterSpacing: '0.12em',
            display: 'inline-block',
            transform: 'scaleY(1.5)',
            transformOrigin: 'center',
          }}
        >
          HEYGENT
        </span>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-white/10 font-medium text-white'
                  : 'text-white/50 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <LayoutDashboard className="h-4 w-4" />
            <span>대시보드</span>
          </NavLink>

          <NavLink
            to="/agent-status"
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-white/10 font-medium text-white'
                  : 'text-white/50 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Activity className="h-4 w-4" />
            <span>에이전트 상태</span>
          </NavLink>
        </nav>
      </div>

      {/* Right: Theme toggle */}
      <button
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-white/50 transition-colors hover:bg-white/10 hover:text-white"
        title={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </div>
  )
}
