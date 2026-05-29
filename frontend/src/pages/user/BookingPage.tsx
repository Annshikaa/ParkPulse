import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { bookingsApi } from "@/api/bookings";
import { slotsApi } from "@/api/slots";
import client from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import type { Slot, Vehicle } from "@/types";
import { Plus, X, CheckCircle, AlertCircle } from "lucide-react";

function toLocalDatetimeString(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function BookingPage() {
  const { slotId } = useParams<{ slotId: string }>();
  const navigate = useNavigate();

  const [slot, setSlot] = useState<Slot | null>(null);
  const [slotError, setSlotError] = useState("");
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehicleId, setVehicleId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [bookingError, setBookingError] = useState("");
  const [bookingSuccess, setBookingSuccess] = useState("");

  const now = new Date();
  const [fromDate, setFromDate] = useState(toLocalDatetimeString(new Date(now.getTime() + 30 * 60000)));
  const [untilDate, setUntilDate] = useState(toLocalDatetimeString(new Date(now.getTime() + 90 * 60000)));

  // Add vehicle form
  const [showAddVehicle, setShowAddVehicle] = useState(false);
  const [newPlate, setNewPlate] = useState("");
  const [newMakeModel, setNewMakeModel] = useState("");
  const [newColor, setNewColor] = useState("");
  const [addingVehicle, setAddingVehicle] = useState(false);
  const [vehicleError, setVehicleError] = useState("");

  const estimatedHours = fromDate && untilDate
    ? Math.max(0, (new Date(untilDate).getTime() - new Date(fromDate).getTime()) / 3600000)
    : 0;
  const estimatedAmount = slot ? estimatedHours * slot.hourly_rate : 0;

  const fetchVehicles = () =>
    client.get<Vehicle[]>("/auth/me/vehicles").then((r) => {
      setVehicles(r.data);
      if (r.data.length > 0 && vehicleId === null) setVehicleId(r.data[0].id);
    }).catch(() => null);

  useEffect(() => {
    if (slotId && slotId !== "0") {
      slotsApi.get(Number(slotId))
        .then((r) => setSlot(r.data))
        .catch(() => {
          // Slot ID not found — fall back to any free slot
          slotsApi.list().then((r) => {
            const free = r.data.find((s) => !s.occupied);
            if (free) setSlot(free);
            else setSlotError("No available slots found. Please go back and choose a slot.");
          }).catch(() => setSlotError("Could not load slots. Is the backend running?"));
        });
    } else {
      slotsApi.list().then((r) => {
        const free = r.data.find((s) => !s.occupied);
        if (free) setSlot(free);
        else setSlotError("No available slots found.");
      }).catch(() => setSlotError("Could not load slots. Is the backend running?"));
    }
    fetchVehicles();
  }, [slotId]);

  useEffect(() => {
    if (!slot || !fromDate || !untilDate) return;
    if (new Date(untilDate) <= new Date(fromDate)) return;
    const t = setTimeout(() => {
      bookingsApi
        .checkAvailability(slot.id, new Date(fromDate).toISOString(), new Date(untilDate).toISOString())
        .then((r) => setAvailable(r.data.available))
        .catch(() => setAvailable(null));
    }, 400);
    return () => clearTimeout(t);
  }, [slot, fromDate, untilDate]);

  const handleAddVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlate.trim()) { setVehicleError("License plate is required"); return; }
    setAddingVehicle(true);
    setVehicleError("");
    try {
      const res = await client.post("/auth/me/vehicles", {
        license_plate: newPlate.trim().toUpperCase(),
        make_model: newMakeModel.trim() || null,
        color: newColor.trim() || null,
      });
      setVehicles((prev) => [...prev, res.data]);
      setVehicleId(res.data.id);
      setShowAddVehicle(false);
      setNewPlate(""); setNewMakeModel(""); setNewColor("");
    } catch (err: any) {
      setVehicleError(err?.response?.data?.detail ?? "Failed to add vehicle");
    } finally {
      setAddingVehicle(false);
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!fromDate) errs.from = "Start time required";
    if (!untilDate) errs.until = "End time required";
    else if (untilDate <= fromDate) errs.until = "End time must be after start time";
    if (!vehicleId) errs.vehicle = "Select a vehicle";
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setBookingError("");
    setBookingSuccess("");
    if (!slot) { setBookingError("No slot loaded. Go back to the dashboard and select a slot."); return; }

    setLoading(true);
    try {
      const res = await bookingsApi.create({
        slot_id: slot.id,
        vehicle_id: vehicleId!,
        booked_from: new Date(fromDate).toISOString(),
        booked_until: new Date(untilDate).toISOString(),
      });
      await bookingsApi.confirm(res.data.id);
      setBookingSuccess("Booking confirmed! Redirecting…");
      setTimeout(() => navigate(`/app/bookings/${res.data.id}`), 1200);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? "Booking failed. Please try again.";
      setBookingError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Book a Slot</h1>
        <p className="text-sm text-muted-foreground">Reserve your parking spot in advance</p>
      </div>

      {slotError && (
        <div className="flex items-center gap-2 rounded-md bg-red-950 text-red-300 px-4 py-3 text-sm">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {slotError}
        </div>
      )}

      {slot && (
        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="font-semibold text-lg">Slot {slot.slot_number}</div>
              <div className="text-sm text-muted-foreground capitalize">{slot.slot_type} · ₹{slot.hourly_rate}/hr</div>
            </div>
            <Badge variant={slot.occupied ? "destructive" : "success"}>
              {slot.occupied ? "Occupied" : "Available"}
            </Badge>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Booking Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">

            {/* Time range */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">From</label>
                <Input type="datetime-local" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
                {errors.from && <p className="text-xs text-red-400">{errors.from}</p>}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Until</label>
                <Input type="datetime-local" value={untilDate} onChange={(e) => setUntilDate(e.target.value)} />
                {errors.until && <p className="text-xs text-red-400">{errors.until}</p>}
              </div>
            </div>

            {available !== null && estimatedHours > 0 && (
              <p className={`text-sm font-medium ${available ? "text-emerald-400" : "text-red-400"}`}>
                {available ? "✓ Slot available for this time" : "✗ Slot already booked for this time"}
              </p>
            )}

            {/* Vehicle */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-muted-foreground">Vehicle</label>
                <button
                  type="button"
                  onClick={() => { setShowAddVehicle(!showAddVehicle); setVehicleError(""); }}
                  className="flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  {showAddVehicle ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                  {showAddVehicle ? "Cancel" : "Add vehicle"}
                </button>
              </div>

              {vehicles.length > 0 ? (
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-secondary px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={vehicleId ?? ""}
                  onChange={(e) => setVehicleId(Number(e.target.value) || null)}
                >
                  <option value="">Select vehicle…</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.license_plate}{v.make_model ? ` — ${v.make_model}` : ""}{v.color ? ` (${v.color})` : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="text-xs text-amber-400 bg-amber-500/10 rounded-md px-3 py-2 border border-amber-500/20">
                  No vehicles registered. Add one below to continue.
                </p>
              )}
              {errors.vehicle && <p className="text-xs text-red-400">{errors.vehicle}</p>}

              {/* Inline add vehicle form */}
              {showAddVehicle && (
                <div className="rounded-md border border-border bg-secondary/50 p-3 space-y-2">
                  <p className="text-xs font-medium text-foreground">Add New Vehicle</p>
                  <Input
                    placeholder="License plate *  e.g. MH12AB1234"
                    value={newPlate}
                    onChange={(e) => setNewPlate(e.target.value)}
                    autoComplete="off"
                  />
                  <Input
                    placeholder="Make & model  e.g. Maruti Swift"
                    value={newMakeModel}
                    onChange={(e) => setNewMakeModel(e.target.value)}
                  />
                  <Input
                    placeholder="Color  e.g. White"
                    value={newColor}
                    onChange={(e) => setNewColor(e.target.value)}
                  />
                  {vehicleError && <p className="text-xs text-red-400">{vehicleError}</p>}
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleAddVehicle}
                    disabled={addingVehicle}
                    className="w-full gap-2"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {addingVehicle ? "Adding…" : "Add Vehicle"}
                  </Button>
                </div>
              )}
            </div>

            {/* Price estimate */}
            {estimatedHours > 0 && slot && (
              <div className="rounded-md bg-secondary p-3 space-y-1.5 text-sm">
                <div className="flex justify-between text-muted-foreground">
                  <span>Duration</span>
                  <span>{estimatedHours.toFixed(1)} hrs</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Rate</span>
                  <span>₹{slot.hourly_rate}/hr</span>
                </div>
                <div className="border-t border-border pt-1.5 flex justify-between font-semibold text-foreground">
                  <span>Estimated Total</span>
                  <span className="text-primary">{formatCurrency(estimatedAmount)}</span>
                </div>
              </div>
            )}

            <p className="text-xs text-muted-foreground bg-amber-500/10 border border-amber-500/20 rounded-md p-2">
              Demo mode: payment is mocked. Booking will be confirmed immediately.
            </p>

            {bookingError && (
              <div className="flex items-start gap-2 rounded-md bg-red-950 text-red-300 px-3 py-2 text-sm">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                {bookingError}
              </div>
            )}
            {bookingSuccess && (
              <div className="flex items-center gap-2 rounded-md bg-emerald-950 text-emerald-300 px-3 py-2 text-sm">
                <CheckCircle className="h-4 w-4" />
                {bookingSuccess}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={loading || available === false}
            >
              {loading ? "Processing…" : "Confirm Booking"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
