import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { bookingsApi } from "@/api/bookings";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";
import type { Booking, BookingStatus } from "@/types";

const statusVariant: Record<BookingStatus, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  confirmed: "success",
  active: "success",
  completed: "outline",
  cancelled: "destructive",
  pending_payment: "warning",
};

export function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    bookingsApi.get(Number(id))
      .then((r) => setBooking(r.data))
      .finally(() => setLoading(false));
  }, [id]);

  const cancel = async () => {
    if (!booking) return;
    try {
      await bookingsApi.cancel(booking.id);
      toast.success("Booking cancelled");
      navigate("/app/bookings");
    } catch {
      toast.error("Failed to cancel");
    }
  };

  if (loading) return <Skeleton className="h-64" />;
  if (!booking) return <div className="text-muted-foreground">Booking not found.</div>;

  const rows = [
    { label: "Booking ID", value: `#${booking.id}` },
    { label: "Slot", value: `Slot ${booking.slot_number}` },
    { label: "Vehicle", value: booking.license_plate || "—" },
    { label: "Booked From", value: new Date(booking.booked_from).toLocaleString() },
    { label: "Booked Until", value: new Date(booking.booked_until).toLocaleString() },
    { label: "Estimated Amount", value: formatCurrency(booking.estimated_amount) },
    { label: "Final Amount", value: booking.final_amount ? formatCurrency(booking.final_amount) : "—" },
    { label: "Entry Time", value: booking.actual_entry_time ? new Date(booking.actual_entry_time).toLocaleString() : "Not yet detected" },
    { label: "Exit Time", value: booking.actual_exit_time ? new Date(booking.actual_exit_time).toLocaleString() : "Not yet detected" },
  ];

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Booking #{booking.id}</h1>
          <p className="text-sm text-muted-foreground">Reservation details</p>
        </div>
        <Badge variant={statusVariant[booking.status]}>{booking.status}</Badge>
      </div>

      <Card>
        <CardContent className="p-0">
          <dl className="divide-y divide-border">
            {rows.map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between px-6 py-3">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="text-sm font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      {booking.actual_entry_time && (
        <div className="rounded-md bg-emerald-500/10 border border-emerald-500/30 p-3 text-sm text-emerald-400">
          Vehicle detected entering at {new Date(booking.actual_entry_time).toLocaleTimeString()}
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={() => navigate("/app/bookings")}>Back</Button>
        {["pending_payment", "confirmed"].includes(booking.status) && (
          <Button variant="destructive" onClick={cancel}>Cancel Booking</Button>
        )}
      </div>
    </div>
  );
}
