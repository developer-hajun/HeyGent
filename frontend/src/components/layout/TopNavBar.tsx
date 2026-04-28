import { LayoutDashboard, Activity, Sun, Moon } from 'lucide-react'
import { NavLink } from 'react-router'
import { useUIStore } from '@/store/useUIStore'

export function TopNavBar() {
  const { theme, setTheme } = useUIStore()

  return (
    <div className="border-border bg-background/80 z-40 flex h-14 shrink-0 items-center justify-between border-b px-6 backdrop-blur-xl">
      {/* Left: Logo + Nav */}
      <div className="flex items-center gap-8">
        {/* Logo */}
        <div className="flex flex-col items-start leading-none">
          <span
            className="tracking-tight select-none"
            style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 800 }}
          >
            <span className="text-foreground">Hey</span>
            <span
              style={{
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--chart-5) 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              G
            </span>
            <span className="text-foreground">ent</span>
          </span>
          <span
            className="text-muted-foreground tracking-widest select-none"
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: '8px',
              fontWeight: 500,
              marginTop: '1px',
            }}
          >
            AI 협업 생중계
          </span>
        </div>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
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
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
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
        className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
        title={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </div>
  )
}
