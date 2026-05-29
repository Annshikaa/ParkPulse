import { useEffect, useState } from "react";
import client from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Camera, Plus, Trash2, RefreshCw, Pencil, CheckCircle, AlertCircle, X,
} from "lucide-react";

interface CameraRecord {
  id: number;
  name: string;
  rtsp_url: string;
  location: string | null;
  status: string;
  is_active: boolean;
}

interface FormState {
  name: string;
  rtsp_url: string;
  location: string;
}

const emptyForm = (): FormState => ({ name: "", rtsp_url: "", location: "" });

export function CameraManagerPage() {
  const [cameras, setCameras] = useState<CameraRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [restarting, setRestarting] = useState<number | null>(null);

  const fetchCameras = async () => {
    setLoading(true);
    try {
      const res = await client.get("/cameras");
      setCameras(res.data);
    } catch {
      setMsg({ text: "Failed to load cameras", ok: false });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCameras(); }, []);

  const openAdd = () => {
    setEditId(null);
    setForm(emptyForm());
    setShowForm(true);
    setMsg(null);
  };

  const openEdit = (cam: CameraRecord) => {
    setEditId(cam.id);
    setForm({ name: cam.name, rtsp_url: cam.rtsp_url, location: cam.location ?? "" });
    setShowForm(true);
    setMsg(null);
  };

  const closeForm = () => { setShowForm(false); setEditId(null); setForm(emptyForm()); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.rtsp_url.trim()) {
      setMsg({ text: "Name and RTSP URL are required", ok: false });
      return;
    }
    setSubmitting(true);
    setMsg(null);
    try {
      const payload = {
        name: form.name.trim(),
        rtsp_url: form.rtsp_url.trim(),
        location: form.location.trim() || null,
      };
      if (editId !== null) {
        await client.put(`/cameras/${editId}`, payload);
        setMsg({ text: `Camera updated`, ok: true });
      } else {
        await client.post("/cameras", payload);
        setMsg({ text: `Camera added and pipeline starting`, ok: true });
      }
      closeForm();
      await fetchCameras();
    } catch (e: any) {
      setMsg({ text: e?.response?.data?.detail ?? "Request failed", ok: false });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this camera? Its pipeline will be stopped.")) return;
    try {
      await client.delete(`/cameras/${id}`);
      setCameras(prev => prev.filter(c => c.id !== id));
      setMsg({ text: "Camera deleted", ok: true });
    } catch (e: any) {
      setMsg({ text: e?.response?.data?.detail ?? "Delete failed", ok: false });
    }
  };

  const handleToggleActive = async (cam: CameraRecord) => {
    try {
      await client.put(`/cameras/${cam.id}`, { is_active: !cam.is_active });
      await fetchCameras();
    } catch {
      setMsg({ text: "Failed to update camera", ok: false });
    }
  };

  const handleRestart = async (id: number) => {
    setRestarting(id);
    try {
      await client.post(`/cameras/${id}/restart`);
      setMsg({ text: "Restart triggered", ok: true });
      setTimeout(fetchCameras, 2000);
    } catch {
      setMsg({ text: "Restart failed", ok: false });
    } finally {
      setRestarting(null);
    }
  };

  const statusBadge = (status: string) => {
    if (status === "online") return <Badge variant="success" className="text-xs">Online</Badge>;
    if (status === "error") return <Badge variant="destructive" className="text-xs">Error</Badge>;
    return <Badge variant="secondary" className="text-xs">Offline</Badge>;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Camera Manager</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Add RTSP/IP cameras — each gets its own CV pipeline thread
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchCameras} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button onClick={openAdd} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Camera
          </Button>
        </div>
      </div>

      {msg && (
        <div className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm ${
          msg.ok ? "bg-emerald-950 text-emerald-300" : "bg-red-950 text-red-300"
        }`}>
          {msg.ok ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {msg.text}
          <button className="ml-auto" onClick={() => setMsg(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}

      {/* Add / Edit form */}
      {showForm && (
        <Card className="border-primary/40">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Camera className="h-4 w-4" />
              {editId ? "Edit Camera" : "Add New Camera"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Camera Name *</label>
                <Input
                  placeholder="e.g. Entrance Camera"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">RTSP / Source URL *</label>
                <Input
                  placeholder="rtsp://… or 0 for webcam"
                  value={form.rtsp_url}
                  onChange={e => setForm(f => ({ ...f, rtsp_url: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Location (optional)</label>
                <Input
                  placeholder="e.g. Level B1"
                  value={form.location}
                  onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
                />
              </div>
              <div className="md:col-span-3 flex gap-2 pt-1">
                <Button type="submit" disabled={submitting} className="gap-2">
                  <CheckCircle className="h-4 w-4" />
                  {submitting ? "Saving…" : editId ? "Update" : "Add Camera"}
                </Button>
                <Button type="button" variant="outline" onClick={closeForm}>Cancel</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Camera list */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-36 rounded-lg bg-accent animate-pulse" />
          ))}
        </div>
      ) : cameras.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-4 text-muted-foreground">
            <Camera className="h-12 w-12 opacity-30" />
            <p className="text-sm">No cameras configured yet.</p>
            <Button onClick={openAdd} variant="outline" className="gap-2">
              <Plus className="h-4 w-4" />
              Add your first camera
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {cameras.map(cam => (
            <Card key={cam.id} className={!cam.is_active ? "opacity-60" : ""}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <CardTitle className="text-base truncate">{cam.name}</CardTitle>
                    {cam.location && (
                      <p className="text-xs text-muted-foreground mt-0.5">{cam.location}</p>
                    )}
                  </div>
                  {statusBadge(cam.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-muted-foreground font-mono truncate bg-muted rounded px-2 py-1">
                  {cam.rtsp_url}
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => handleToggleActive(cam)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      cam.is_active
                        ? "border-emerald-700 text-emerald-400 hover:bg-emerald-950"
                        : "border-muted text-muted-foreground hover:bg-accent"
                    }`}
                  >
                    {cam.is_active ? "Active" : "Inactive"}
                  </button>
                  <div className="flex gap-1.5 ml-auto">
                    <button
                      title="Restart pipeline"
                      onClick={() => handleRestart(cam.id)}
                      disabled={restarting === cam.id}
                      className="text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded hover:bg-accent"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${restarting === cam.id ? "animate-spin" : ""}`} />
                    </button>
                    <button
                      title="Edit"
                      onClick={() => openEdit(cam)}
                      className="text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded hover:bg-accent"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      title="Delete"
                      onClick={() => handleDelete(cam.id)}
                      className="text-muted-foreground hover:text-red-400 transition-colors p-1.5 rounded hover:bg-accent"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
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
