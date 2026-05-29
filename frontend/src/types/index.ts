export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: "user" | "admin";
  created_at: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}

export interface Slot {
  id: number;
  slot_number: string;
  polygon: number[][];
  slot_type: "regular" | "handicap" | "ev";
  hourly_rate: number;
  occupied: boolean;
  track_id: number;
  dwell_seconds: number;
}

export interface SlotWS {
  slot_id: number;
  slot_number: string;
  occupied: boolean;
  track_id: number;
  dwell_seconds: number;
}

export interface Stats {
  total: number;
  occupied: number;
  free: number;
  occupancy_rate: number;
  avg_dwell_seconds: number;
  fps: number;
  backend: string;
  uptime_seconds: number;
}

export interface WSTick {
  type: "tick";
  stats: Stats;
  fps: number;
  backend: string;
  slots: SlotWS[];
  timestamp: number;
}

export interface WSEvent {
  type: "event";
  slot_id: number;
  event_type: "enter" | "exit";
  track_id: number;
  dwell_seconds: number;
  timestamp: number;
}

export type WSMessage = WSTick | WSEvent;

export interface Vehicle {
  id: number;
  user_id: number;
  license_plate: string;
  make_model: string | null;
  color: string | null;
}

export interface Booking {
  id: number;
  slot_id: number;
  slot_number: string | null;
  vehicle_id: number;
  license_plate: string | null;
  booked_from: string;
  booked_until: string;
  status: BookingStatus;
  estimated_amount: number;
  final_amount: number | null;
  actual_entry_time: string | null;
  actual_exit_time: string | null;
  created_at: string;
}

export type BookingStatus =
  | "pending_payment"
  | "confirmed"
  | "active"
  | "completed"
  | "cancelled";

export interface BenchmarkResult {
  backend: string;
  passes?: number;
  mean_ms?: number;
  std_ms?: number;
  fps?: number;
  skipped?: boolean;
  reason?: string;
}

export interface SettingsResponse {
  current_backend: string;
  available_backends: string[];
  fps: number;
  preprocessor_enabled: boolean;
  benchmarks: BenchmarkResult[];
  video_source: string;
  slot_count: number;
}
