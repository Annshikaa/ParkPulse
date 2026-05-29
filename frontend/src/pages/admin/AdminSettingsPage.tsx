import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Cpu, Zap, RefreshCw, Video, ScanSearch, Save, CheckCircle2 } from "lucide-react";
import client from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { SettingsResponse, BenchmarkResult } from "@/types";

interface ExtendedSettings extends SettingsResponse {
  video_source: string;
  slot_count: number;
}

interface DetectedSlots {
  detected: number;
  slots: object[];
}

const BACKEND_LABELS: Record<string, string> = {
  pytorch: "PyTorch FP32",
  onnx_fp32: "ONNX FP32",
  onnx_int8: "ONNX INT8",
};

const BACKEND_DESCRIPTIONS: Record<string, string> = {
  pytorch: "Full precision. Best accuracy, highest memory usage.",
  onnx_fp32: "ONNX runtime — faster startup, slightly lower latency.",
  onnx_int8: "INT8 dynamic quantization — smallest model, fastest on CPU.",
};

function BenchRow({ r }: { r: BenchmarkResult }) {
  if (r.skipped) {
    return (
      <tr className="text-muted-foreground text-xs">
        <td className="py-1 pr-4 font-mono">{r.backend}</td>
        <td colSpan={4} className="italic">not available — {r.reason}</td>
      </tr>
    );
  }
  return (
    <tr className="text-sm">
      <td className="py-1 pr-4 font-mono text-xs">{r.backend}</td>
      <td className="py-1 pr-4 tabular-nums">{r.mean_ms} ms</td>
      <td className="py-1 pr-4 tabular-nums">{r.std_ms} ms</td>
      <td className="py-1 pr-4 tabular-nums text-primary font-medium">{r.fps} FPS</td>
    </tr>
  );
}

export function AdminSettingsPage() {
  const [settings, setSettings] = useState<ExtendedSettings | null>(null);
  const [switching, setSwitching] = useState<string | null>(null);
  const [preprocessor, setPreprocessor] = useState(true);

  // CCTV source
  const [videoSource, setVideoSource] = useState("");
  const [connectingCctv, setConnectingCctv] = useState(false);

  // Slot detection
  const [detecting, setDetecting] = useState(false);
  const [detected, setDetected] = useState<DetectedSlots | null>(null);
  const [saving, setSaving] = useState(false);
  const [slotsSaved, setSlotsSaved] = useState(false);

  const load = () => {
    client.get<ExtendedSettings>("/settings").then((r) => {
      setSettings(r.data);
      setPreprocessor(r.data.preprocessor_enabled);
      setVideoSource(r.data.video_source ?? "");
    }).catch(() => toast.error("Failed to load settings"));
  };

  useEffect(load, []);

  // ── CCTV source ──────────────────────────────────────────────────
  const connectCctv = async () => {
    const src = videoSource.trim();
    if (!src) { toast.error("Enter a video source first"); return; }
    setConnectingCctv(true);
    try {
      await client.post("/settings/video-source", { source: src });
      toast.success("Pipeline switching to new source — live in a few seconds");
      setDetected(null);
      setSlotsSaved(false);
      setTimeout(load, 4000); // reload settings after pipeline restarts
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || "Could not connect to video source");
    } finally {
      setConnectingCctv(false);
    }
  };

  // ── Slot detection ───────────────────────────────────────────────
  const detectSlots = async () => {
    setDetecting(true);
    setDetected(null);
    setSlotsSaved(false);
    try {
      const res = await client.get<DetectedSlots>("/settings/detect-slots");
      setDetected(res.data);
      toast.success(`Auto-detected ${res.data.detected} parking slots from the live feed`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || "Detection failed — make sure the pipeline is running");
    } finally {
      setDetecting(false);
    }
  };

  const saveSlots = async () => {
    if (!detected) return;
    setSaving(true);
    try {
      const res = await client.post<{ message: string; count: number }>("/settings/slots", {
        slots: detected.slots,
      });
      toast.success(res.data.message);
      setSlotsSaved(true);
      setTimeout(load, 4000); // slot_count will update after pipeline reload
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || "Failed to save slots");
    } finally {
      setSaving(false);
    }
  };

  // ── Backend switching ────────────────────────────────────────────
  const switchBackend = async (backend: string) => {
    if (switching) return;
    setSwitching(backend);
    try {
      const res = await client.post<{ backend: string; fps: number; message: string }>(
        "/settings/backend", { backend }
      );
      toast.success(`Switched to ${backend} — ${res.data.fps.toFixed(1)} FPS`);
      load();
    } catch {
      toast.error("Failed to switch backend");
    } finally {
      setSwitching(null);
    }
  };

  const togglePreprocessor = async () => {
    const next = !preprocessor;
    try {
      await client.post("/settings/preprocessor", { enabled: next });
      setPreprocessor(next);
      toast.success(`Preprocessor ${next ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to toggle preprocessor");
    }
  };

  if (!settings) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-48" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure CCTV source, auto-detect slots, and control the CV pipeline
        </p>
      </div>

      {/* ── CCTV Source ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Video className="h-4 w-4 text-primary" />
            CCTV / Video Source
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-xs text-muted-foreground space-y-1">
            <p>Enter an RTSP URL, a local file path, or <code className="bg-secondary px-1 rounded">0</code> for the default webcam.</p>
            <p className="font-mono text-[11px] text-muted-foreground">
              Examples: &nbsp;rtsp://admin:pass@192.168.1.64/stream &nbsp;|&nbsp; C:\cam\parking.mp4 &nbsp;|&nbsp; 0
            </p>
          </div>
          <div className="flex gap-2">
            <Input
              value={videoSource}
              onChange={(e) => setVideoSource(e.target.value)}
              placeholder="rtsp://... or /path/to/video.mp4"
              className="font-mono text-sm"
              onKeyDown={(e) => e.key === "Enter" && connectCctv()}
            />
            <Button onClick={connectCctv} loading={connectingCctv} className="shrink-0">
              Connect
            </Button>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Active source: <code className="bg-secondary px-1 rounded">{settings.video_source}</code></span>
            <span>Slots loaded: <strong className="text-foreground">{settings.slot_count}</strong></span>
          </div>
        </CardContent>
      </Card>

      {/* ── Auto-detect Slots ────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <ScanSearch className="h-4 w-4 text-primary" />
            Auto-detect Parking Slots
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Captures one frame from the live feed and uses computer vision to find parking spaces
            automatically — no manual JSON editing needed. Works for any camera angle or slot count.
          </p>

          <div className="flex gap-3 items-center">
            <Button onClick={detectSlots} loading={detecting} variant="outline">
              <ScanSearch className="h-4 w-4" />
              {detecting ? "Analysing frame…" : "Detect Slots from Live Feed"}
            </Button>

            {detected && !slotsSaved && (
              <Button onClick={saveSlots} loading={saving}>
                <Save className="h-4 w-4" />
                Save {detected.detected} Slots
              </Button>
            )}

            {slotsSaved && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                Saved — pipeline reloading
              </span>
            )}
          </div>

          {detected && (
            <div className={cn(
              "rounded-lg border p-4 space-y-2",
              slotsSaved
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-primary/30 bg-primary/5"
            )}>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-primary">{detected.detected}</span>
                <div>
                  <div className="font-medium text-sm">Slots detected</div>
                  <div className="text-xs text-muted-foreground">
                    from the current live frame via edge + contour analysis
                  </div>
                </div>
              </div>
              {!slotsSaved && (
                <p className="text-xs text-muted-foreground">
                  Click <strong>Save</strong> to write these slot polygons to disk and reload the CV pipeline.
                  The live feed will immediately start tracking occupancy for all {detected.detected} slots.
                </p>
              )}
            </div>
          )}

          <div className="text-xs text-muted-foreground bg-secondary/60 rounded-md p-3 space-y-1">
            <p className="font-medium text-foreground">How it works</p>
            <p>1. Captures a snapshot from the active CCTV stream</p>
            <p>2. Canny edge detection + contour analysis finds rectangular parking regions</p>
            <p>3. Non-maximum suppression removes overlaps</p>
            <p>4. Saves polygons to <code className="bg-background px-1 rounded">data/parking_slots.json</code> and restarts the pipeline</p>
            <p>5. From that point, the CV pipeline tracks every detected slot in real-time — cars entering = occupied, cars leaving = free</p>
          </div>
        </CardContent>
      </Card>

      {/* ── Early Departure Info ─────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            Smart Early Departure
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            When the CV pipeline detects a car leaving a slot during an active booking window,
            the booking is <strong className="text-foreground">automatically completed</strong> and the
            slot is freed immediately — no waiting for the user's scheduled end time.
            The final charge is calculated from actual dwell time.
          </p>
          <div className="mt-3 flex items-center gap-2 text-xs text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Active — monitoring all booked slots continuously
          </div>
        </CardContent>
      </Card>

      {/* ── Detection Backend ────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            Detection Backend
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {settings.available_backends.map((backend) => {
            const bench = Array.isArray(settings.benchmarks)
              ? settings.benchmarks.find((b) => b.backend?.toLowerCase().includes(backend.replace("_", " ")))
              : null;
            const isActive = settings.current_backend === backend;
            return (
              <div
                key={backend}
                className={cn(
                  "flex items-center justify-between rounded-lg border p-4 transition-colors",
                  isActive ? "border-primary/50 bg-primary/5" : "border-border hover:border-primary/20"
                )}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm">{BACKEND_LABELS[backend] ?? backend}</span>
                    {isActive && <Badge variant="success" className="text-[10px]">ACTIVE</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">{BACKEND_DESCRIPTIONS[backend]}</p>
                  {bench && !bench.skipped && (
                    <p className="text-xs text-primary mt-1">{bench.mean_ms} ms avg · {bench.fps} FPS</p>
                  )}
                </div>
                {!isActive && (
                  <Button size="sm" variant="outline" loading={switching === backend} onClick={() => switchBackend(backend)}>
                    <RefreshCw className="h-3 w-3" />
                    Switch
                  </Button>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* ── Preprocessor ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            Image Preprocessor (CLAHE + Gamma)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm">Adaptive contrast enhancement</p>
              <p className="text-xs text-muted-foreground mt-1">
                Improves detection accuracy in low-light or over-exposed surveillance feeds.
              </p>
            </div>
            <Button variant={preprocessor ? "default" : "outline"} size="sm" onClick={togglePreprocessor}>
              {preprocessor ? "Enabled" : "Disabled"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── Benchmarks ───────────────────────────────────────────── */}
      {Array.isArray(settings.benchmarks) && settings.benchmarks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Benchmark Results</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground border-b border-border">
                  <th className="pb-2 text-left">Backend</th>
                  <th className="pb-2 text-left">Mean</th>
                  <th className="pb-2 text-left">Std</th>
                  <th className="pb-2 text-left">FPS</th>
                </tr>
              </thead>
              <tbody>
                {settings.benchmarks.map((r, i) => <BenchRow key={i} r={r} />)}
              </tbody>
            </table>
            <p className="text-xs text-muted-foreground mt-3">
              Run <code className="font-mono bg-secondary px-1 rounded">python scripts/benchmark.py</code> to regenerate.
            </p>
          </CardContent>
        </Card>
      )}

      {/* ── System Info ──────────────────────────────────────────── */}
      <Card>
        <CardHeader><CardTitle className="text-sm">System Info</CardTitle></CardHeader>
        <CardContent className="text-sm space-y-2">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Current FPS</span>
            <span className="font-mono">{settings.fps.toFixed(1)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Active Backend</span>
            <span className="font-mono">{settings.current_backend}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Slots Tracked</span>
            <span className="font-mono">{settings.slot_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">API Docs</span>
            <a href="/docs" target="_blank" className="text-primary hover:underline text-xs">/docs (Swagger UI)</a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
