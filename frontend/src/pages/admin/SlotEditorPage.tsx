import { useCallback, useEffect, useRef, useState } from "react";
import client from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Camera, Trash2, Save, RefreshCw, CheckCircle, AlertCircle,
  Pencil, X, Database, Wand2, Grid3x3, Square, Rows3,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Pt { x: number; y: number }

interface DrawSlot {
  id: string;
  dbId?: number;
  points: Pt[];           // always 4 corners [TL, TR, BR, BL]
  slot_number: string;
  slot_type: "regular" | "handicap" | "ev";
  hourly_rate: number;
  saved: boolean;
  dirty: boolean;
}

type Tool = "rect" | "row" | "polygon";
type CameraOption = { id: number; name: string };

const SAVED_COLOR   = "#3b82f6";
const NEW_COLOR     = "#f59e0b";
const DIRTY_COLOR   = "#a855f7";
const PREVIEW_COLOR = "#22c55e";

function slotColor(s: DrawSlot, activeId: string | null) {
  if (s.id === activeId) return "#ffffff";
  if (!s.saved) return NEW_COLOR;
  if (s.dirty)  return DIRTY_COLOR;
  return SAVED_COLOR;
}

function rectPoints(x1: number, y1: number, x2: number, y2: number): Pt[] {
  const [lx, rx] = x1 < x2 ? [x1, x2] : [x2, x1];
  const [ty, by] = y1 < y2 ? [y1, y2] : [y2, y1];
  return [{ x: lx, y: ty }, { x: rx, y: ty }, { x: rx, y: by }, { x: lx, y: by }];
}

function autoLabel(existing: DrawSlot[], index: number) {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const row = Math.floor(index / 10);
  const col = (index % 10) + 1;
  return `${letters[row] ?? "Z"}${col}`;
}

// ── Component ─────────────────────────────────────────────────────────────────
export function SlotEditorPage() {
  const canvasRef    = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [imgSrc, setImgSrc]           = useState<string | null>(null);
  const [scale, setScale]             = useState(1);
  const [loadingSnap, setLoadingSnap] = useState(false);
  const [snapError, setSnapError]     = useState("");

  const [cameras, setCameras]             = useState<CameraOption[]>([]);
  const [camId, setCamId]                 = useState<number | "default">("default");

  const [slots, setSlots]           = useState<DrawSlot[]>([]);
  const [activeId, setActiveId]     = useState<string | null>(null);
  const [loadingSlots, setLoadingSlots] = useState(true);

  // Tool state
  const [tool, setTool] = useState<Tool>("rect");
  const [dragStart, setDragStart] = useState<Pt | null>(null);
  const [dragCurrent, setDragCurrent] = useState<Pt | null>(null);

  // Row tool: after drag finished, ask for count
  const [rowRect, setRowRect]       = useState<{ pts: Pt[] } | null>(null);
  const [rowCount, setRowCount]     = useState("6");
  const [rowHorizontal, setRowHorizontal] = useState(true);

  // Polygon tool (fallback)
  const [polyPts, setPolyPts]         = useState<Pt[]>([]);

  // Slot form
  const [editingId, setEditingId]   = useState<string | null>(null);
  const [frmNumber, setFrmNumber]   = useState("");
  const [frmType, setFrmType]       = useState<DrawSlot["slot_type"]>("regular");
  const [frmRate, setFrmRate]       = useState("50");

  // Auto-detect
  const [detecting, setDetecting]   = useState(false);
  const [detectMsg, setDetectMsg]   = useState("");

  // Save
  const [saving, setSaving]         = useState(false);
  const [saveMsg, setSaveMsg]       = useState<{ text: string; ok: boolean } | null>(null);

  // ── Boot: load cameras + existing slots ──────────────────────────────────
  useEffect(() => {
    client.get("/cameras").then(r => setCameras(r.data)).catch(() => {});
    client.get("/slots").then(r => {
      setSlots(r.data.map((s: any) => ({
        id: `db-${s.id}`,
        dbId: s.id,
        points: (s.polygon as number[][]).map(([x, y]: number[]) => ({ x, y })),
        slot_number: s.slot_number,
        slot_type: s.slot_type ?? "regular",
        hourly_rate: s.hourly_rate ?? 50,
        saved: true,
        dirty: false,
      })));
    }).catch(() => {}).finally(() => setLoadingSlots(false));
  }, []);

  // ── Load snapshot ────────────────────────────────────────────────────────
  const loadSnapshot = useCallback(async () => {
    setLoadingSnap(true); setSnapError("");
    try {
      const url = camId === "default" ? "/settings/snapshot" : `/cameras/${camId}/snapshot`;
      const res = await client.get(url, { responseType: "blob" });
      setImgSrc(URL.createObjectURL(res.data));
    } catch (e: any) {
      setSnapError(e?.response?.data?.detail ?? "Cannot capture frame. Is the video running?");
    } finally { setLoadingSnap(false); }
  }, [camId]);

  // ── Canvas helpers ────────────────────────────────────────────────────────
  const toNative = (e: React.MouseEvent<HTMLCanvasElement>): Pt => {
    const r = canvasRef.current!.getBoundingClientRect();
    return { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale };
  };

  // ── Draw canvas ───────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !imgSrc) return;
    const img = new Image();
    img.src = imgSrc;
    img.onload = () => {
      const w = container.clientWidth;
      const r = w / img.naturalWidth;
      canvas.width = w;
      canvas.height = img.naturalHeight * r;
      setScale(r);
      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      const drawPoly = (pts: Pt[], color: string, label: string, bold = false) => {
        if (pts.length < 2) return;
        const sp = pts.map(p => ({ x: p.x * r, y: p.y * r }));
        ctx.beginPath();
        ctx.moveTo(sp[0].x, sp[0].y);
        sp.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
        ctx.closePath();
        ctx.fillStyle = color + "30";
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = bold ? 2.5 : 1.5;
        ctx.stroke();
        if (label) {
          const cx = sp.reduce((s, p) => s + p.x, 0) / sp.length;
          const cy = sp.reduce((s, p) => s + p.y, 0) / sp.length;
          ctx.font = `bold ${bold ? 12 : 10}px sans-serif`;
          ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillStyle = "#fff";
          ctx.fillText(label, cx, cy);
        }
      };

      slots.forEach(s => drawPoly(s.points, slotColor(s, activeId), s.slot_number, s.id === activeId));

      // Drag preview
      if (dragStart && dragCurrent) {
        if (tool === "rect") {
          drawPoly(rectPoints(dragStart.x, dragStart.y, dragCurrent.x, dragCurrent.y), PREVIEW_COLOR, "");
        } else if (tool === "row") {
          const pts = rectPoints(dragStart.x, dragStart.y, dragCurrent.x, dragCurrent.y);
          drawPoly(pts, PREVIEW_COLOR, "");
          // Show division lines
          const n = Math.max(1, parseInt(rowCount) || 6);
          const dx = (dragCurrent.x - dragStart.x) / n;
          const dy = (dragCurrent.y - dragStart.y) / n;
          ctx.strokeStyle = PREVIEW_COLOR + "80";
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 3]);
          for (let i = 1; i < n; i++) {
            const [lx, rx] = dragStart.x < dragCurrent.x ? [dragStart.x, dragCurrent.x] : [dragCurrent.x, dragStart.x];
            const [ty, by] = dragStart.y < dragCurrent.y ? [dragStart.y, dragCurrent.y] : [dragCurrent.y, dragStart.y];
            const isHoriz = (rx - lx) >= (by - ty);
            if (isHoriz) {
              const x = (lx + i * (rx - lx) / n) * r;
              ctx.beginPath(); ctx.moveTo(x, ty * r); ctx.lineTo(x, by * r); ctx.stroke();
            } else {
              const y = (ty + i * (by - ty) / n) * r;
              ctx.beginPath(); ctx.moveTo(lx * r, y); ctx.lineTo(rx * r, y); ctx.stroke();
            }
          }
          ctx.setLineDash([]);
        }
      }

      // Row confirmation overlay
      if (rowRect) {
        drawPoly(rowRect.pts, PREVIEW_COLOR, "Divide into rows?");
      }

      // Polygon in-progress
      if (tool === "polygon" && polyPts.length > 0) {
        const sp = polyPts.map(p => ({ x: p.x * r, y: p.y * r }));
        ctx.beginPath(); ctx.moveTo(sp[0].x, sp[0].y);
        sp.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
        if (dragCurrent) ctx.lineTo(dragCurrent.x * r, dragCurrent.y * r);
        ctx.strokeStyle = NEW_COLOR; ctx.lineWidth = 2;
        ctx.setLineDash([6, 3]); ctx.stroke(); ctx.setLineDash([]);
        sp.forEach((p, i) => {
          ctx.beginPath(); ctx.arc(p.x, p.y, i === 0 ? 7 : 4, 0, Math.PI * 2);
          ctx.fillStyle = i === 0 ? NEW_COLOR : "#fff"; ctx.fill();
        });
      }
    };
  }, [imgSrc, slots, activeId, dragStart, dragCurrent, rowRect, polyPts, tool, rowCount, scale]);

  // ── Mouse handlers ────────────────────────────────────────────────────────
  const onMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button !== 0) return;
    const pt = toNative(e);

    if (tool === "rect" || tool === "row") {
      setDragStart(pt); setDragCurrent(pt);
      return;
    }

    if (tool === "polygon") {
      if (polyPts.length >= 3) {
        const first = polyPts[0];
        if (Math.hypot(pt.x - first.x, pt.y - first.y) < 15 / scale) {
          commitPolygon(); return;
        }
      }
      setPolyPts(prev => [...prev, pt]);
    }
  };

  const onMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pt = toNative(e);
    if ((tool === "rect" || tool === "row") && dragStart) setDragCurrent(pt);
    if (tool === "polygon") setDragCurrent(pt);
  };

  const onMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!dragStart || !dragCurrent) return;
    const dx = Math.abs(dragCurrent.x - dragStart.x);
    const dy = Math.abs(dragCurrent.y - dragStart.y);
    if (dx < 5 && dy < 5) { // tiny drag = click — select existing slot
      const pt = toNative(e);
      const hit = slots.find(s => pointInPoly(pt, s.points));
      if (hit) {
        setActiveId(hit.id === activeId ? null : hit.id);
        if (hit.id !== activeId) { openEdit(hit); }
      } else { setActiveId(null); setEditingId(null); }
      setDragStart(null); setDragCurrent(null);
      return;
    }

    if (tool === "rect") {
      commitRect(dragStart, dragCurrent);
      setDragStart(null); setDragCurrent(null);
    } else if (tool === "row") {
      const pts = rectPoints(dragStart.x, dragStart.y, dragCurrent.x, dragCurrent.y);
      const isHoriz = (Math.abs(dragCurrent.x - dragStart.x)) >= (Math.abs(dragCurrent.y - dragStart.y));
      setRowHorizontal(isHoriz);
      setRowRect({ pts });
      setDragStart(null); setDragCurrent(null);
    }
  };

  const onDblClick = () => { if (tool === "polygon" && polyPts.length >= 3) commitPolygon(); };

  // ── Slot creation helpers ─────────────────────────────────────────────────
  const nextLabel = (offset = 0) => frmNumber.trim() || autoLabel(slots, slots.length + offset);

  const commitRect = (a: Pt, b: Pt) => {
    const pts = rectPoints(a.x, a.y, b.x, b.y);
    addSlot(pts, nextLabel());
    setFrmNumber("");
  };

  const commitRow = () => {
    if (!rowRect) return;
    const n = Math.max(1, parseInt(rowCount) || 1);
    const [p0, p1, p2, p3] = rowRect.pts; // TL, TR, BR, BL
    const newSlots: DrawSlot[] = [];
    for (let i = 0; i < n; i++) {
      const t = i / n, t2 = (i + 1) / n;
      let pts: Pt[];
      if (rowHorizontal) {
        const tl = lerp2(p0, p1, t),  tr = lerp2(p0, p1, t2);
        const bl = lerp2(p3, p2, t),  br = lerp2(p3, p2, t2);
        pts = [tl, tr, br, bl];
      } else {
        const tl = lerp2(p0, p3, t),  tr = lerp2(p1, p2, t);
        const bl = lerp2(p0, p3, t2), br = lerp2(p1, p2, t2);
        pts = [tl, tr, br, bl];
      }
      newSlots.push(makeSlot(pts, nextLabel(i + newSlots.length)));
    }
    setSlots(prev => [...prev, ...newSlots]);
    setRowRect(null);
    setFrmNumber("");
  };

  const commitPolygon = () => {
    if (polyPts.length < 3) return;
    addSlot([...polyPts], nextLabel());
    setPolyPts([]); setDragCurrent(null); setFrmNumber("");
  };

  const makeSlot = (pts: Pt[], label: string): DrawSlot => ({
    id: crypto.randomUUID(),
    points: pts,
    slot_number: label,
    slot_type: frmType,
    hourly_rate: parseFloat(frmRate) || 50,
    saved: false, dirty: false,
  });

  const addSlot = (pts: Pt[], label: string) => setSlots(prev => [...prev, makeSlot(pts, label)]);

  // ── Edit ──────────────────────────────────────────────────────────────────
  const openEdit = (s: DrawSlot) => {
    setEditingId(s.id); setFrmNumber(s.slot_number);
    setFrmType(s.slot_type); setFrmRate(String(s.hourly_rate));
  };

  const applyEdit = () => {
    if (!editingId) return;
    setSlots(prev => prev.map(s => s.id !== editingId ? s : {
      ...s, slot_number: frmNumber.trim() || s.slot_number,
      slot_type: frmType, hourly_rate: parseFloat(frmRate) || s.hourly_rate,
      dirty: s.saved,
    }));
    setEditingId(null); setActiveId(null);
  };

  const deleteSlot = (id: string) => {
    setSlots(prev => prev.filter(s => s.id !== id));
    if (activeId === id) setActiveId(null);
    if (editingId === id) setEditingId(null);
  };

  const clearAll = () => {
    if (!confirm(`Delete all ${slots.length} slots?`)) return;
    setSlots([]); setActiveId(null); setEditingId(null);
    setPolyPts([]); setRowRect(null);
  };

  // ── Auto-detect ───────────────────────────────────────────────────────────
  const autoDetect = async () => {
    setDetecting(true); setDetectMsg("");
    try {
      const res = await client.get("/settings/detect-slots");
      const detected: DrawSlot[] = res.data.slots.map((s: any) => ({
        id: crypto.randomUUID(),
        points: (s.polygon as number[][]).map(([x, y]: number[]) => ({ x, y })),
        slot_number: s.slot_number,
        slot_type: s.slot_type ?? "regular",
        hourly_rate: s.hourly_rate ?? 50,
        saved: false, dirty: false,
      }));
      setSlots(prev => [...prev, ...detected]);
      setDetectMsg(`Auto-detected ${detected.length} slots — review and save.`);
    } catch (e: any) {
      setDetectMsg("Auto-detect failed: " + (e?.response?.data?.detail ?? e.message));
    } finally { setDetecting(false); }
  };

  // ── Save ──────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!slots.length) return;
    setSaving(true); setSaveMsg(null);
    try {
      const payload = slots.map((s, i) => ({
        id: s.dbId ?? i + 1,
        slot_number: s.slot_number,
        polygon: s.points.map(p => [Math.round(p.x), Math.round(p.y)]),
        slot_type: s.slot_type,
        hourly_rate: s.hourly_rate,
      }));
      await client.post("/settings/slots", { slots: payload });
      setSlots(prev => prev.map((s, i) => ({ ...s, saved: true, dirty: false, dbId: s.dbId ?? i + 1 })));
      setSaveMsg({ text: `Saved ${slots.length} slots. CV pipeline reloading…`, ok: true });
    } catch (e: any) {
      setSaveMsg({ text: "Error: " + (e?.response?.data?.detail ?? e.message), ok: false });
    } finally { setSaving(false); }
  };

  const newCount   = slots.filter(s => !s.saved).length;
  const dirtyCount = slots.filter(s => s.dirty).length;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Slot Editor</h1>
          <p className="text-muted-foreground text-sm">
            Drag to draw · Row tool for entire rows · Auto-detect from live CV
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground mr-1">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm" style={{ background: SAVED_COLOR }} />Saved</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm" style={{ background: NEW_COLOR }} />New</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm" style={{ background: DIRTY_COLOR }} />Edited</span>
          </div>
          {slots.length > 0 && (
            <Button variant="outline" size="sm" onClick={clearAll}
              className="gap-1.5 text-red-400 hover:text-red-300 border-red-900 hover:bg-red-950">
              <Trash2 className="h-3.5 w-3.5" />Clear All
            </Button>
          )}
          <Button onClick={handleSave} disabled={saving || !slots.length} className="gap-2">
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : `Save All (${slots.length})`}
          </Button>
        </div>
      </div>

      {saveMsg && (
        <div className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm ${saveMsg.ok ? "bg-emerald-950 text-emerald-300" : "bg-red-950 text-red-300"}`}>
          {saveMsg.ok ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {saveMsg.text}
          <button className="ml-auto" onClick={() => setSaveMsg(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_290px] gap-4">
        {/* Canvas card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Camera + load */}
              <select value={camId} onChange={e => setCamId(e.target.value === "default" ? "default" : Number(e.target.value))}
                className="text-sm rounded-md border border-border bg-background px-2 py-1 text-foreground">
                <option value="default">Default source</option>
                {cameras.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <Button size="sm" variant="outline" onClick={loadSnapshot} disabled={loadingSnap} className="gap-1.5">
                <Camera className="h-3.5 w-3.5" />{loadingSnap ? "Loading…" : imgSrc ? "Refresh" : "Load Frame"}
              </Button>

              <div className="h-4 w-px bg-border mx-1" />

              {/* Tool selector */}
              {([
                { id: "rect",    icon: Square,   label: "Drag Rect" },
                { id: "row",     icon: Rows3,    label: "Row Tool" },
                { id: "polygon", icon: Grid3x3,  label: "Polygon" },
              ] as const).map(t => (
                <button key={t.id} onClick={() => { setTool(t.id as Tool); setPolyPts([]); setRowRect(null); }}
                  className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border transition-colors ${
                    tool === t.id
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}>
                  <t.icon className="h-3.5 w-3.5" />{t.label}
                </button>
              ))}

              <div className="h-4 w-px bg-border mx-1" />

              {/* Auto-detect */}
              <Button size="sm" variant="outline" onClick={autoDetect} disabled={detecting} className="gap-1.5">
                <Wand2 className="h-3.5 w-3.5" />{detecting ? "Detecting…" : "Auto-detect"}
              </Button>
            </div>

            {/* Tool hint */}
            <p className="text-xs text-muted-foreground mt-1">
              {tool === "rect"    && "Click and drag to draw a single parking slot rectangle."}
              {tool === "row"     && "Drag across a full row of bays → enter slot count → confirm to split into equal slots."}
              {tool === "polygon" && "Click to add vertices. Click near first dot or double-click to close."}
            </p>
            {detectMsg && (
              <p className={`text-xs mt-1 ${detectMsg.startsWith("Auto-detect failed") ? "text-red-400" : "text-emerald-400"}`}>
                {detectMsg}
              </p>
            )}
          </CardHeader>
          <CardContent>
            {snapError && (
              <div className="flex items-center gap-2 rounded-md bg-red-950 text-red-300 px-4 py-3 text-sm mb-3">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />{snapError}
              </div>
            )}

            {!imgSrc ? (
              <div className="flex flex-col items-center justify-center h-72 rounded-lg border-2 border-dashed border-border text-muted-foreground gap-3">
                <Camera className="h-10 w-10 opacity-30" />
                <p className="text-sm">Load a camera frame to start</p>
                {!loadingSlots && slots.length > 0 && (
                  <p className="text-xs text-primary">{slots.length} saved slot{slots.length !== 1 ? "s" : ""} will be shown when you load a frame</p>
                )}
                <Button onClick={loadSnapshot} disabled={loadingSnap}>{loadingSnap ? "Loading…" : "Load Frame"}</Button>
              </div>
            ) : (
              <div className="space-y-2">
                <div ref={containerRef} className="w-full relative select-none">
                  <canvas
                    ref={canvasRef}
                    className="w-full rounded-lg border border-border"
                    style={{ cursor: tool === "polygon" ? "crosshair" : "crosshair" }}
                    onMouseDown={onMouseDown}
                    onMouseMove={onMouseMove}
                    onMouseUp={onMouseUp}
                    onDoubleClick={onDblClick}
                    onMouseLeave={() => { if (tool !== "polygon") { setDragStart(null); setDragCurrent(null); } }}
                  />
                  {/* Row tool confirmation popup */}
                  {rowRect && (
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-card border border-border rounded-lg p-3 shadow-xl flex items-center gap-2 z-10">
                      <span className="text-sm font-medium">Split into</span>
                      <Input
                        type="number" min="1" max="50" value={rowCount}
                        onChange={e => setRowCount(e.target.value)}
                        className="w-16 h-8 text-center"
                        autoFocus
                        onKeyDown={e => { if (e.key === "Enter") commitRow(); if (e.key === "Escape") setRowRect(null); }}
                      />
                      <span className="text-sm font-medium">slots</span>
                      <Button size="sm" onClick={commitRow} className="gap-1"><CheckCircle className="h-3.5 w-3.5" />OK</Button>
                      <button onClick={() => setRowRect(null)} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
                    </div>
                  )}
                  {polyPts.length > 0 && (
                    <div className="absolute top-2 right-2 flex gap-2">
                      <Badge variant="warning">{polyPts.length} pts</Badge>
                      {polyPts.length >= 3 && (
                        <button onClick={commitPolygon}
                          className="bg-amber-700/80 hover:bg-amber-600 text-white text-xs px-2 py-0.5 rounded">
                          Close
                        </button>
                      )}
                      <button onClick={() => setPolyPts([])}
                        className="bg-red-900/80 hover:bg-red-800 text-white text-xs px-2 py-0.5 rounded">
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Form */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                {editingId ? <><Pencil className="h-4 w-4 text-purple-400" />Edit Slot</> : <><Square className="h-4 w-4" />Slot Settings</>}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  {editingId ? "Slot Number" : "Slot Number (next)"}
                </label>
                <Input
                  placeholder={`e.g. ${autoLabel(slots, slots.length)} (auto if blank)`}
                  value={frmNumber}
                  onChange={e => setFrmNumber(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Type</label>
                <select value={frmType} onChange={e => setFrmType(e.target.value as DrawSlot["slot_type"])}
                  className="w-full text-sm rounded-md border border-border bg-background px-3 py-2 text-foreground">
                  {["regular", "handicap", "ev"].map(t => (
                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Hourly Rate (₹)</label>
                <Input type="number" min="0" step="5" value={frmRate} onChange={e => setFrmRate(e.target.value)} />
              </div>
              {editingId && (
                <div className="flex gap-2">
                  <Button className="flex-1 gap-1" onClick={applyEdit}><CheckCircle className="h-3.5 w-3.5" />Apply</Button>
                  <Button variant="outline" className="flex-1" onClick={() => { setEditingId(null); setActiveId(null); }}>Cancel</Button>
                </div>
              )}
              {tool === "row" && rowRect && (
                <div className="rounded-md bg-emerald-950 text-emerald-300 px-3 py-2 text-xs">
                  Set count in the popup on the canvas, then click OK.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Slot list */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Slots</CardTitle>
                <div className="flex gap-1.5">
                  {newCount > 0   && <Badge variant="warning"   className="text-xs">{newCount} new</Badge>}
                  {dirtyCount > 0 && <Badge variant="secondary" className="text-xs">{dirtyCount} edited</Badge>}
                  <Badge variant="outline" className="text-xs">{slots.length} total</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {loadingSlots ? (
                <div className="flex items-center gap-2 px-4 py-3 text-xs text-muted-foreground">
                  <Database className="h-3.5 w-3.5 animate-pulse" />Loading…
                </div>
              ) : slots.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-6 px-4">
                  Load a frame and draw your first slot using one of the tools above.
                </p>
              ) : (
                <div className="max-h-[380px] overflow-y-auto divide-y divide-border">
                  {slots.map(slot => (
                    <div key={slot.id}
                      onClick={() => { setActiveId(slot.id === activeId ? null : slot.id); if (slot.id !== activeId) openEdit(slot); else setEditingId(null); }}
                      className={`flex items-center gap-2 px-4 py-2.5 cursor-pointer transition-colors ${activeId === slot.id ? "bg-accent" : "hover:bg-accent/40"}`}>
                      <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: slotColor(slot, null) }} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{slot.slot_number}</div>
                        <div className="text-xs text-muted-foreground">
                          {slot.slot_type} · ₹{slot.hourly_rate}/hr
                          {!slot.saved && <span className="ml-1 text-amber-400">unsaved</span>}
                          {slot.dirty  && <span className="ml-1 text-purple-400">edited</span>}
                        </div>
                      </div>
                      <button onClick={e => { e.stopPropagation(); deleteSlot(slot.id); }}
                        className="text-muted-foreground hover:text-red-400 p-1 transition-colors">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ── Geometry helpers ──────────────────────────────────────────────────────────
function lerp2(a: Pt, b: Pt, t: number): Pt {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function pointInPoly(pt: Pt, poly: Pt[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i].x, yi = poly[i].y, xj = poly[j].x, yj = poly[j].y;
    if ((yi > pt.y) !== (yj > pt.y) && pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi) + xi)
      inside = !inside;
  }
  return inside;
}
