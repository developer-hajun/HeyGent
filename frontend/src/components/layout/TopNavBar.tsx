import { LayoutDashboard, Activity, Bot } from 'lucide-react'
import { NavLink } from 'react-router'

export function TopNavBar() {
  return (
    <div
      className="border-border z-40 flex h-14 flex-shrink-0 items-center justify-between border-b bg-white px-6"
      style={{ boxShadow: '0 1px 0 0 var(--border)' }}
    >
      {/* Left: Logo + Nav */}
      <div className="flex items-center gap-8">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="from-primary to-chart-5 flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br shadow-sm">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <span
            className="text-foreground font-semibold"
            style={{ fontFamily: 'var(--font-display)', fontSize: '17px' }}
          >
            Heygent
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
    </div>
  )
}
