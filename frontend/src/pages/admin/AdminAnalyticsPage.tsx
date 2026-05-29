import { useEffect, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";
import client from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";

type Range = "1h" | "6h" | "24h" | "7d";

interface TimeseriesPoint {
  timestamp: string;
  occupied: number;
  total: number;
  rate: number;
}

interface SlotUtil {
  slot_id: number;
  slot_number: string;
  slot_type: string;
  completed_bookings: number;
  total_revenue: number;
}

interface Revenue {
  total_revenue: number;
  completed_bookings: number;
  range: string;
}

interface HeatmapPoint {
  hour: number;
  avg_occupancy_rate: number;
}

export function AdminAnalyticsPage() {
  const [range, setRange] = useState<Range>("24h");
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [revenue, setRevenue] = useState<Revenue | null>(null);
  const [slots, setSlots] = useState<SlotUtil[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      client.get<TimeseriesPoint[]>(`/analytics/occupancy-timeseries?range=${range}`),
      client.get<Revenue>(`/analytics/revenue?range=${range}`),
      client.get<SlotUtil[]>("/analytics/slot-utilization"),
      client.get<HeatmapPoint[]>("/analytics/hourly-heatmap"),
    ]).then(([ts, rev, su, hm]) => {
      setTimeseries(ts.data);
      setRevenue(rev.data);
      setSlots(su.data);
      setHeatmap(hm.data);
    }).finally(() => setLoading(false));
  }, [range]);

  const ranges: Range[] = ["1h", "6h", "24h", "7d"];

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-48" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-sm text-muted-foreground">Occupancy, revenue, and utilization</p>
        </div>
        <div className="flex gap-1">
          {ranges.map((r) => (
            <Button
              key={r}
              size="sm"
              variant={range === r ? "default" : "outline"}
              onClick={() => setRange(r)}
            >
              {r}
            </Button>
          ))}
        </div>
      </div>

      {/* Revenue card */}
      {revenue && (
        <Card>
          <CardContent className="p-6 flex items-center gap-8">
            <div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Revenue ({range})</div>
              <div className="text-3xl font-bold text-primary">{formatCurrency(revenue.total_revenue)}</div>
            </div>
            <div className="w-px h-10 bg-border" />
            <div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Completed Bookings</div>
              <div className="text-3xl font-bold">{revenue.completed_bookings}</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Occupancy timeseries */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Occupancy Rate Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {timeseries.length === 0 ? (
            <div className="text-sm text-muted-foreground py-8 text-center">No data for this range</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={timeseries}>
                <defs>
                  <linearGradient id="occ" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(160,84%,39%)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(160,84%,39%)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  tick={{ fontSize: 11, fill: "hsl(215,20%,65%)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: "hsl(215,20%,65%)" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  contentStyle={{ background: "hsl(222,47%,14%)", border: "1px solid hsl(216,34%,20%)", borderRadius: 6 }}
                  labelFormatter={(v) => new Date(v as string).toLocaleString()}
                  formatter={(v: number) => [`${v}%`, "Occupancy"]}
                />
                <Area
                  type="monotone"
                  dataKey="rate"
                  stroke="hsl(160,84%,39%)"
                  fill="url(#occ)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Hourly heatmap */}
      {heatmap.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Average Occupancy by Hour</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={heatmap}>
                <XAxis
                  dataKey="hour"
                  tickFormatter={(h) => `${h}:00`}
                  tick={{ fontSize: 10, fill: "hsl(215,20%,65%)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "hsl(215,20%,65%)" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  contentStyle={{ background: "hsl(222,47%,14%)", border: "1px solid hsl(216,34%,20%)", borderRadius: 6 }}
                  formatter={(v: number) => [`${v}%`, "Avg Occupancy"]}
                />
                <Bar dataKey="avg_occupancy_rate" fill="hsl(160,84%,39%)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Slot utilization table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Slot Utilization</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground border-b border-border">
                <th className="pb-2 text-left">Slot</th>
                <th className="pb-2 text-left">Type</th>
                <th className="pb-2 text-right">Bookings</th>
                <th className="pb-2 text-right">Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {slots.map((s) => (
                <tr key={s.slot_id}>
                  <td className="py-2 font-mono font-medium">{s.slot_number}</td>
                  <td className="py-2 text-muted-foreground capitalize">{s.slot_type}</td>
                  <td className="py-2 text-right tabular-nums">{s.completed_bookings}</td>
                  <td className="py-2 text-right tabular-nums text-primary">{formatCurrency(s.total_revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
