import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Car, ParkingSquare, TrendingUp, Activity } from "lucide-react";
import { toast } from "sonner";
import { useWebSocket } from "@/hooks/useWebSocket";
import { bookingsApi } from "@/api/bookings";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDuration, formatCurrency } from "@/lib/utils";
import type { Booking, SlotWS } from "@/types";

function StatCard({
  label,
  value,
  icon: Icon,
  variant = "default",
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  variant?: "default" | "success" | "warning" | "destructive";
}) {
  const colorMap = {
    default: "text-foreground",
    success: "text-emerald-400",
    warning: "text-amber-400",
    destructive: "text-red-400",
  };
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-muted-foreground">{label}</span>
          <div className="rounded-md bg-primary/10 p-1.5">
            <Icon className="h-4 w-4 text-primary" />
          </div>
        </div>
        <div className={cn("text-3xl font-bold num-flip", colorMap[variant])}>{value}</div>
      </CardContent>
    </Card>
  );
}

function SlotTile({
  slot,
  onClick,
  isMyBooking,
}: {
  slot: SlotWS;
  onClick: () => void;
  isMyBooking: boolean;
}) {
  const canBook = !slot.occupied && !isMyBooking;

  return (
    <button
      onClick={canBook ? onClick : undefined}
      disabled={!canBook && !isMyBooking}
      className={cn(
        "slot-tile relative rounded-lg border-2 p-3 text-left w-full",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        slot.occupied
          ? "border-red-500/40 bg-red-500/10"
          : isMyBooking
          ? "border-blue-500/40 bg-blue-500/10"
          : "border-emerald-500/40 bg-emerald-500/10 cursor-pointer hover:bg-emerald-500/20",
        !canBook && !isMyBooking && "opacity-90 cursor-default"
      )}
    >
      <div className="text-sm font-bold mb-1">{slot.slot_number}</div>
      {slot.occupied ? (
        <>
          <div className="text-xs text-red-400 font-medium">Occupied</div>
          {slot.dwell_seconds > 0 && (
            <div className="text-xs text-muted-foreground mt-0.5">
              {formatDuration(slot.dwell_seconds)}
            </div>
          )}
        </>
      ) : isMyBooking ? (
        <div className="text-xs text-blue-400 font-medium">Your Booking</div>
      ) : (
        <div className="text-xs text-emerald-400 font-medium">Available</div>
      )}
    </button>
  );
}

export function DashboardPage() {
  const { stats, slots, connected } = useWebSocket();
  const navigate = useNavigate();
  const [activeBooking, setActiveBooking] = useState<Booking | null>(null);
  const [loadingBookings, setLoadingBookings] = useState(true);
  const [bookedSlotIds, setBookedSlotIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    bookingsApi.myBookings()
      .then((res) => {
        const active = res.data.find(
          (b) => b.status === "active" || b.status === "confirmed"
        );
        setActiveBooking(active || null);
        const ids = new Set(
          res.data
            .filter((b) => ["active", "confirmed"].includes(b.status))
            .map((b) => b.slot_id)
        );
        setBookedSlotIds(ids);
      })
      .finally(() => setLoadingBookings(false));
  }, []);

  const occupancyPct = stats
    ? Math.round(stats.occupancy_rate * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Live parking availability</p>
      </div>

      {/* Stat cards */}
      {stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Slots" value={stats.total} icon={ParkingSquare} />
          <StatCard label="Available" value={stats.free} icon={Car} variant="success" />
          <StatCard label="Occupied" value={stats.occupied} icon={Activity} variant="destructive" />
          <StatCard
            label="Occupancy"
            value={`${occupancyPct}%`}
            icon={TrendingUp}
            variant={occupancyPct > 75 ? "destructive" : occupancyPct > 50 ? "warning" : "success"}
          />
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      )}

      {/* Book CTA */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Live Slot Map</h2>
        <Button onClick={() => navigate("/app/book/0")}>
          <Car className="h-4 w-4" />
          Book a Slot
        </Button>
      </div>

      {/* Video feed + slot grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* MJPEG feed */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              Live Camera Feed
              {connected && (
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <img
              src={import.meta.env.VITE_STREAM_URL ?? "http://localhost:8000/stream/video"}
              alt="Live parking feed"
              className="w-full rounded-md border border-border"
              style={{ minHeight: 220, objectFit: "cover" }}
            />
          </CardContent>
        </Card>

        {/* Slot grid */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Slot Status</CardTitle>
          </CardHeader>
          <CardContent>
            {slots.length === 0 ? (
              <div className="grid grid-cols-3 gap-2">
                {[...Array(7)].map((_, i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {slots.map((slot) => (
                  <SlotTile
                    key={slot.slot_id}
                    slot={slot}
                    isMyBooking={bookedSlotIds.has(slot.slot_id)}
                    onClick={() => navigate(`/app/book/${slot.slot_id}`)}
                  />
                ))}
              </div>
            )}
            <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-emerald-500/60" /> Available
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-red-500/60" /> Occupied
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-blue-500/60" /> Your Booking
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active booking card */}
      {!loadingBookings && activeBooking && (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Your Active Booking
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="font-semibold">Slot {activeBooking.slot_number}</div>
                <div className="text-sm text-muted-foreground">
                  {new Date(activeBooking.booked_from).toLocaleString()} →{" "}
                  {new Date(activeBooking.booked_until).toLocaleString()}
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      activeBooking.status === "active"
                        ? "success"
                        : activeBooking.status === "confirmed"
                        ? "warning"
                        : "secondary"
                    }
                  >
                    {activeBooking.status}
                  </Badge>
                  <span className="text-sm font-medium text-primary">
                    {formatCurrency(activeBooking.estimated_amount)}
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/app/bookings/${activeBooking.id}`)}
                >
                  View
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
