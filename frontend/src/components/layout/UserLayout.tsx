import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Car, CalendarDays, LayoutDashboard, LogOut, Wifi, WifiOff } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/bookings", label: "My Bookings", icon: CalendarDays },
];

export function UserLayout() {
  const { user, logout } = useAuth();
  const { connected } = useWebSocket();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 flex flex-col border-r border-border bg-card">
        <div className="flex items-center gap-2 px-6 py-5 border-b border-border">
          <Car className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg text-foreground">ParkPulse</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-border">
          <div className="px-3 py-2 text-xs text-muted-foreground mb-2 truncate">
            {user?.full_name}
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-14 flex items-center justify-between px-6 border-b border-border bg-card">
          <span className="text-sm text-muted-foreground">Welcome, {user?.full_name}</span>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {connected ? (
              <><Wifi className="h-3 w-3 text-emerald-400" /> Live</>
            ) : (
              <><WifiOff className="h-3 w-3 text-red-400" /> Reconnecting…</>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
