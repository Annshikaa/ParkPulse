import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { bookingsApi } from "@/api/bookings";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export function MyBookingsPage() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    bookingsApi.myBookings()
      .then((r) => setBookings(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const cancel = async (id: number) => {
    try {
      await bookingsApi.cancel(id);
      toast.success("Booking cancelled");
      load();
    } catch {
      toast.error("Failed to cancel booking");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Bookings</h1>
        <p className="text-sm text-muted-foreground">All your parking reservations</p>
      </div>

      <Button onClick={() => navigate("/app/book/0")}>New Booking</Button>

      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : bookings.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center text-muted-foreground">
            <p className="mb-4">No bookings yet.</p>
            <Button onClick={() => navigate("/app/book/0")}>Book Your First Slot</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => (
            <Card key={b.id} className="hover:border-primary/20 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">Slot {b.slot_number}</span>
                      <Badge variant={statusVariant[b.status]}>{b.status}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {new Date(b.booked_from).toLocaleString()} → {new Date(b.booked_until).toLocaleString()}
                    </div>
                    <div className="text-sm font-medium text-primary">
                      {formatCurrency(b.final_amount ?? b.estimated_amount)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => navigate(`/app/bookings/${b.id}`)}>
                      View
                    </Button>
                    {["pending_payment", "confirmed"].includes(b.status) && (
                      <Button variant="destructive" size="sm" onClick={() => cancel(b.id)}>
                        Cancel
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
