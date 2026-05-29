import { useEffect, useState } from "react";
import { Activity, Car, ParkingSquare, TrendingUp, Zap } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatDuration } from "@/lib/utils";
import type { WSEvent } from "@/types";

function StatCard({ label, value, icon: Icon, sub }: {
  label: string; value: string | number; icon: React.ElementType; sub?: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div className="text-2xl font-bold num-flip">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  );
}

export function AdminLivePage() {
  const { stats, slots, lastEvent, connected } = useWebSocket();
  const [events, setEvents] = useState<(WSEvent & { id: number })[]>([]);
  let eventCounter = 0;

  useEffect(() => {
    if (!lastEvent) return;
    setEvents((prev) => [
      { ...lastEvent, id: ++eventCounter },
      ...prev.slice(0, 19),
    ]);
  }, [lastEvent]);

  const occupancyPct = stats ? Math.round(stats.occupancy_rate * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Live Monitor</h1>
          <p className="text-sm text-muted-foreground">Real-time CV pipeline output</p>
        </div>
        {stats && (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">{stats.backend}</Badge>
            <Badge variant="success" className="text-xs">{stats.fps?.toFixed(1)} FPS</Badge>
          </div>
        )}
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total" value={stats?.total ?? "—"} icon={ParkingSquare} />
        <StatCard label="Occupied" value={stats?.occupied ?? "—"} icon={Car} sub="detected by CV" />
        <StatCard label="Free" value={stats?.free ?? "—"} icon={Activity} />
        <StatCard
          label="Occupancy"
          value={`${occupancyPct}%`}
          icon={TrendingUp}
          sub={`Avg dwell: ${stats ? formatDuration(stats.avg_dwell_seconds) : "—"}`}
        />
      </div>

      {/* Video + slots grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Full-width-ish video */}
        <Card className="xl:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              CV Feed
              {connected && <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <img
              src={import.meta.env.VITE_STREAM_URL ?? "http://localhost:8000/stream/video"}
              alt="CV pipeline output"
              className="w-full rounded-md border border-border"
              style={{ minHeight: 280, objectFit: "cover" }}
            />
          </CardContent>
        </Card>

        {/* Slot detail grid */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Slot Detail</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {slots.length === 0 ? (
                <div className="text-xs text-muted-foreground">Waiting for CV data…</div>
              ) : (
                slots.map((s) => (
                  <div
                    key={s.slot_id}
                    className={cn(
                      "flex items-center justify-between rounded-md px-3 py-2 text-sm border",
                      s.occupied
                        ? "border-red-500/30 bg-red-500/10"
                        : "border-emerald-500/30 bg-emerald-500/10"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold w-8">{s.slot_number}</span>
                      {s.track_id !== -1 && (
                        <span className="text-xs text-muted-foreground">T{s.track_id}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {s.occupied && s.dwell_seconds > 0 && (
                        <span className="text-xs text-muted-foreground">{formatDuration(s.dwell_seconds)}</span>
                      )}
                      <span className={cn("text-xs font-medium", s.occupied ? "text-red-400" : "text-emerald-400")}>
                        {s.occupied ? "OCC" : "FREE"}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Events feed */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            CV Events Feed
            <span className="text-xs text-muted-foreground font-normal">(last 20)</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <div className="text-sm text-muted-foreground py-4 text-center">
              No events yet — events appear here when vehicles enter or exit slots
            </div>
          ) : (
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {events.map((ev) => (
                <div
                  key={ev.id}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm animate-slide-in",
                    ev.event_type === "enter"
                      ? "bg-red-500/10 border border-red-500/20"
                      : "bg-emerald-500/10 border border-emerald-500/20"
                  )}
                >
                  <span className={cn("font-bold text-xs w-10", ev.event_type === "enter" ? "text-red-400" : "text-emerald-400")}>
                    {ev.event_type.toUpperCase()}
                  </span>
                  <span className="text-muted-foreground">Slot {ev.slot_id}</span>
                  <span className="text-muted-foreground text-xs">Track #{ev.track_id}</span>
                  {ev.dwell_seconds > 0 && (
                    <span className="text-xs text-muted-foreground ml-auto">{formatDuration(ev.dwell_seconds)}</span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
