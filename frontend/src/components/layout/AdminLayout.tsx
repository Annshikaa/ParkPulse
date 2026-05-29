import { NavLink, Outlet } from "react-router-dom";
import { Car, BarChart3, Settings, CalendarDays, Monitor, LogOut, Wifi, WifiOff, Camera, PenTool } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { to: "/admin/live", label: "Live Monitor", icon: Monitor },
  { to: "/admin/bookings", label: "Bookings", icon: CalendarDays },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/admin/cameras", label: "Cameras", icon: Camera },
  { to: "/admin/slot-editor", label: "Slot Editor", icon: PenTool },
  { to: "/admin/settings", label: "Settings", icon: Settings },
];

export function AdminLayout() {
  const { user, logout } = useAuth();
  const { connected, stats } = useWebSocket();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="w-60 flex-shrink-0 flex flex-col border-r border-border bg-card">
        <div className="flex items-center gap-2 px-6 py-5 border-b border-border">
          <Car className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg text-foreground">ParkPulse</span>
          <Badge variant="warning" className="ml-auto text-[10px]">ADMIN</Badge>
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
            {user?.email}
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

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 flex items-center justify-between px-6 border-b border-border bg-card">
          <div className="flex items-center gap-3">
            {stats?.backend && (
              <Badge variant="outline" className="text-xs font-mono">
                {stats.backend}
              </Badge>
            )}
            {stats?.fps !== undefined && (
              <Badge variant="success" className="text-xs">
                {stats.fps.toFixed(1)} FPS
              </Badge>
            )}
          </div>
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
