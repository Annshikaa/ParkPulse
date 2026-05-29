import { useEffect, useState } from "react";
import { toast } from "sonner";
import client from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";
import type { BookingStatus } from "@/types";

interface AdminBooking {
  id: number;
  user_email: string;
  slot_number: string;
  status: BookingStatus;
  estimated_amount: number;
  final_amount: number | null;
  booked_from: string;
  booked_until: string;
  created_at: string;
}

const statusVariant: Record<BookingStatus, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  confirmed: "success",
  active: "success",
  completed: "outline",
  cancelled: "destructive",
  pending_payment: "warning",
};

const STATUS_OPTIONS = ["", "pending_payment", "confirmed", "active", "completed", "cancelled"];

export function AdminBookingsPage() {
  const [bookings, setBookings] = useState<AdminBooking[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const qs = new URLSearchParams({ page: String(page) });
    if (status) qs.set("status", status);
    client.get<{ total: number; page: number; items: AdminBooking[] }>(`/admin/bookings?${qs}`)
      .then((r) => { setBookings(r.data.items); setTotal(r.data.total); })
      .finally(() => setLoading(false));
  };

  useEffect(load, [page, status]);

  const cancel = async (id: number) => {
    try {
      await client.patch(`/bookings/${id}/cancel`);
      toast.success("Booking cancelled");
      load();
    } catch {
      toast.error("Failed to cancel");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">All Bookings</h1>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="h-9 rounded-md border border-border bg-secondary px-3 text-sm"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s || "All statuses"}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-16" />)}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground border-b border-border">
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">User</th>
                  <th className="px-4 py-3 text-left">Slot</th>
                  <th className="px-4 py-3 text-left">From</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {bookings.map((b) => (
                  <tr key={b.id} className="hover:bg-accent/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">#{b.id}</td>
                    <td className="px-4 py-3 text-xs truncate max-w-[150px]">{b.user_email}</td>
                    <td className="px-4 py-3 font-mono font-medium">{b.slot_number}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {new Date(b.booked_from).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant[b.status]} className="text-[10px]">
                        {b.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-primary">
                      {formatCurrency(b.final_amount ?? b.estimated_amount)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {["pending_payment", "confirmed"].includes(b.status) && (
                        <Button variant="destructive" size="sm" onClick={() => cancel(b.id)}>
                          Cancel
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">Page {page}</span>
        <Button
          variant="outline"
          size="sm"
          disabled={page * 20 >= total}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
