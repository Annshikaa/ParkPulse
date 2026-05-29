import client from "./client";
import type { Booking } from "@/types";

export const bookingsApi = {
  create: (data: {
    slot_id: number;
    vehicle_id: number;
    booked_from: string;
    booked_until: string;
  }) => client.post<Booking>("/bookings", data),

  myBookings: () => client.get<Booking[]>("/bookings/my"),

  get: (id: number) => client.get<Booking>(`/bookings/${id}`),

  cancel: (id: number) => client.patch(`/bookings/${id}/cancel`),

  confirm: (id: number) => client.patch(`/bookings/${id}/confirm`),

  checkAvailability: (slotId: number, from: string, until: string) =>
    client.get<{ available: boolean; slot_id: number }>(
      `/bookings/availability?slot_id=${slotId}&from=${encodeURIComponent(from)}&until=${encodeURIComponent(until)}`
    ),

  vehicles: () => client.get<import("@/types").Vehicle[]>("/auth/me/vehicles"),
};
