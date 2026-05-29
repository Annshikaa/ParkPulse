<div align="center">

<img src="https://img.shields.io/badge/ParkPulse-Smart%20Parking-0ea5e9?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xOC41IDJoLTEzQTMuNSAzLjUgMCAwIDAgMiA1LjV2MTNBMy41IDMuNSAwIDAgMCA1LjUgMjJoMTNhMy41IDMuNSAwIDAgMCAzLjUtMy41di0xM0EzLjUgMy41IDAgMCAwIDE4LjUgMnpNMTIgMTdhNSA1IDAgMSAxIDAtMTAgNSA1IDAgMCAxIDAgMTB6bTAtOGEzIDMgMCAxIDAgMCA2IDMgMyAwIDAgMCAwLTZ6Ii8+PC9zdmc+" />

# 🅿️ ParkPulse

### AI-Powered Smart Parking Management System

*Real-time vehicle detection · Computer vision slot tracking · Seamless booking · Live analytics*

---

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-FF6B35?style=flat-square)](https://ultralytics.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=flat-square&logo=pytorch)](https://pytorch.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript)](https://typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3-38BDF8?style=flat-square&logo=tailwindcss)](https://tailwindcss.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 🌟 What is ParkPulse?

ParkPulse transforms any CCTV camera into an intelligent parking management system. Connect a camera, draw slot boundaries once, and the system automatically tracks every vehicle that enters or leaves — updating slot availability in real-time, managing bookings, processing payments, and generating rich analytics.

**No more manual counting. No more guesswork. Just intelligence.**

```
CCTV Camera ──▶ YOLOv8 Detection ──▶ Slot IoU Matching ──▶ WebSocket Push ──▶ Live Dashboard
                      │                       │
                 ByteTrack IDs          DB Persistence
                 (track vehicles)       (events, bookings)
```

---

## ✨ Features

### 🤖 Computer Vision Core
- **YOLOv8 + ByteTrack** vehicle detection and multi-object tracking across frames
- **IoU-based slot occupancy** — polygon intersection to detect if a vehicle is inside a slot
- **Hysteresis smoothing** — 3 frames to mark occupied, 8 frames to mark free (no flickering)
- **Multi-backend support** — PyTorch (GPU/CPU), ONNX FP32, ONNX INT8 quantized
- **Hot-swap backends** without restarting the pipeline
- **Multi-camera support** — each camera runs in its own thread

### 🗺️ Interactive Slot Editor
- **Drag-to-draw rectangles** — one drag per slot
- **Row tool** — drag across a row, type the slot count → instant row of equal slots
- **Polygon tool** — for non-rectangular bays
- **Auto-detect** — uses live YOLO detections as slot anchors
- **Click to edit** — select any slot on the canvas to rename, retype, change rate
- All changes sync to DB and reload the CV pipeline instantly

### 📡 Real-time Dashboard
- Live MJPEG video feed with detection overlays
- WebSocket slot status updates every 500ms
- Occupancy stats: total, occupied, free, % rate, avg dwell time
- Per-slot grid with track ID and dwell duration
- Event log: every vehicle entry/exit in real time

### 📅 Booking System
- Users browse live slot availability and book a time window
- Drag-to-add vehicle inline on the booking page
- Availability conflict detection
- **Early departure auto-complete** — CV exit event triggers prorated charge calculation
- Full booking lifecycle: `pending_payment → confirmed → active → completed`

### 💳 Payments
- Razorpay integration (live/test mode)
- Demo mode: mock payment confirms instantly (no keys needed)
- Final amount computed from actual dwell time, not booked duration

### 📊 Analytics
- 7-day occupancy heatmap
- Peak hour analysis
- Revenue trends
- Per-slot utilization breakdown
- Historical occupancy snapshots (saved every 10 seconds)

### 🔔 Alert System
- Camera offline detection
- Filter by severity (info / warning / critical)
- Mark resolved, delete alerts

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  React 18 + TypeScript + Vite + TailwindCSS + ShadCN UI    │
│                                                             │
│  /admin/live      → Live monitor + MJPEG stream            │
│  /admin/cameras   → Camera CRUD + pipeline status          │
│  /admin/slot-editor → Interactive slot polygon editor      │
│  /admin/analytics → Charts + heatmaps                      │
│  /app/dashboard   → User slot map + booking CTA            │
│  /app/book/:id    → Booking form + vehicle management      │
└────────────────────┬────────────────────────────────────────┘
                     │  HTTP/REST + WebSocket
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                     │
│                                                             │
│  /auth          JWT auth, user registration                 │
│  /slots         Live slot states (CV + DB merged)          │
│  /bookings      CRUD + availability check + confirm        │
│  /cameras       Camera CRUD + per-camera pipeline control  │
│  /alerts        Alert management                           │
│  /settings      Backend switch, video source, slot editor  │
│  /stream/video  MJPEG stream                               │
│  /stream/ws     WebSocket tick (500ms)                     │
│  /analytics     Occupancy history, revenue, peak hours     │
└────────────────────┬────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐   ┌──────────────────────────────────┐
│   SQLite / PG    │   │      CV Pipeline (threads)       │
│                  │   │                                  │
│  users           │   │  PipelineWorker (per camera)     │
│  slots           │   │  ├─ cv2.VideoCapture             │
│  bookings        │   │  ├─ YOLOv8 detector              │
│  vehicles        │   │  ├─ ByteTrack tracker            │
│  cameras         │   │  ├─ SlotManager (IoU check)      │
│  payments        │   │  ├─ AppState (shared memory)     │
│  cv_events       │   │  └─ OccupancySnapshot (10s)      │
│  occupancy_snap  │   └──────────────────────────────────┘
│  alerts          │
└──────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **CV Detection** | YOLOv8n (Ultralytics), ByteTrack, OpenCV |
| **CV Geometry** | Shapely (polygon IoU) |
| **Backend** | FastAPI, SQLAlchemy ORM, Pydantic v2 |
| **Auth** | JWT (python-jose), bcrypt |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Payments** | Razorpay |
| **Frontend** | React 18, TypeScript, Vite |
| **Styling** | TailwindCSS, ShadCN UI components |
| **State** | Zustand (auth), React hooks |
| **Charts** | Recharts |
| **Real-time** | WebSocket (FastAPI + Vite proxy) |
| **Video stream** | MJPEG over HTTP |
| **Logging** | structlog |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/park-pulse.git
cd park-pulse
```

### 2. Backend setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set JWT_SECRET to a random string at minimum
```

### 3. Frontend setup

```bash
cd frontend
npm install --legacy-peer-deps
cp .env.example .env
cd ..
```

### 4. Download YOLO weights

```bash
# Weights download automatically on first run, OR manually:
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 5. Seed demo data

```bash
python scripts/seed_demo_data.py
```

### 6. Run

**Terminal 1 — Backend:**
```bash
uvicorn backend.app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend && npm run dev
```

Open **http://localhost:5173**

---

## 🔑 Demo Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@parkpulse.io` | `Admin@123` |
| User | `rahul@demo.com` | `Demo@123` |
| User | `priya@demo.com` | `Demo@123` |

---

## 📖 Usage Guide

### Admin Flow

```
1. Login as admin
2. Go to Cameras → Add Camera (RTSP URL or webcam index)
3. Go to Slot Editor → Load Frame
4. Draw slot boundaries using:
   • Drag Rect  — single slot per drag
   • Row Tool   — drag a row, type count → N slots instantly
   • Auto-detect — one click uses live YOLO detections
5. Save All → CV pipeline reloads with your boundaries
6. Go to Live Monitor → watch real-time detection
```

### User Flow

```
1. Register / Login
2. Dashboard shows live slot availability + camera feed
3. Click any green (Available) slot → Book
4. Add your vehicle inline if needed
5. Pick time window → Confirm Booking (demo: instant)
6. If you leave early, the system detects the exit via CV
   and auto-completes the booking with prorated charge
```

---

## 🧠 How the CV Pipeline Works

```
Frame from camera
      │
      ▼
YOLOv8n inference (classes: car, motorcycle, bus, truck)
      │
      ▼
ByteTrack assigns stable IDs across frames
      │
      ▼
For each slot polygon:
  • Compute IoU(slot_polygon, detection_bbox)
  • If IoU > 0.05 → vote "present"
  • If vote count ≥ 3 frames → OCCUPIED  (hysteresis)
  • If vote absent ≥ 8 frames → FREE     (hysteresis)
      │
      ▼
AppState.update() → WebSocket tick → Frontend dashboard
      │
      ▼
CV exit event? → find active booking → auto-complete with
                 prorated charge (actual_hours × hourly_rate)
```

**Why hysteresis?** A single-frame decision would flicker every time a car moves slightly or YOLO misses one frame. Hysteresis smooths this out.

**Why IoU 0.05?** Aerial/angled cameras mean a car's bounding box may only partially overlap the slot polygon. Lower threshold catches these cases without false positives.

---

## 🗂️ Project Structure

```
park-pulse/
├── backend/
│   └── app/
│       ├── db/             # SQLAlchemy models + session
│       ├── routers/        # FastAPI route handlers
│       │   ├── auth.py
│       │   ├── slots.py
│       │   ├── bookings.py
│       │   ├── cameras.py
│       │   ├── alerts.py
│       │   ├── analytics.py
│       │   ├── settings.py
│       │   └── stream.py
│       ├── camera_manager.py   # Multi-camera thread registry
│       ├── pipeline_worker.py  # Single-camera CV worker
│       ├── state.py            # Shared in-memory app state
│       ├── config.py           # Pydantic settings (reads .env)
│       └── main.py             # FastAPI app factory
├── cv/
│   ├── pipeline.py         # Frame loop orchestrator
│   ├── detector.py         # YOLOv8 + ONNX inference
│   ├── slot_manager.py     # IoU occupancy + hysteresis
│   ├── auto_slot_detector.py  # Auto-detect slots from frame
│   └── config.py           # CV thresholds
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── admin/      # Live, Cameras, SlotEditor, Analytics, Settings
│       │   └── user/       # Dashboard, Booking, MyBookings
│       ├── components/     # Shared UI components
│       ├── api/            # Axios client + endpoint wrappers
│       ├── hooks/          # useWebSocket, useAuth
│       └── types/          # TypeScript interfaces
├── scripts/
│   ├── create_admin.py
│   ├── seed_demo_data.py
│   ├── generate_test_video.py
│   ├── benchmark.py
│   └── export_onnx.py
├── data/
│   └── parking_slots.json  # Slot polygon definitions
├── .env.example            # ← copy to .env
├── frontend/.env.example   # ← copy to frontend/.env
└── requirements.txt
```

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `VIDEO_SOURCE` | `sample_video.mp4` | File path, RTSP URL, or `0` for webcam |
| `JWT_SECRET` | *(must set)* | Random string, min 32 chars |
| `JWT_EXPIRE_HOURS` | `24` | Token lifetime |
| `DB_URL` | `sqlite:///./parkpulse.db` | SQLAlchemy DB URL |
| `RAZORPAY_KEY_ID` | *(blank)* | Leave blank for demo/mock mode |
| `RAZORPAY_KEY_SECRET` | *(blank)* | Leave blank for demo/mock mode |
| `PRICE_PER_HOUR_INR` | `50.0` | Default hourly rate |
| `VITE_STREAM_URL` | `http://localhost:8000/stream/video` | MJPEG stream URL |

---

## 🧪 Generate a Test Video

No RTSP camera? Generate a synthetic parking lot video:

```bash
python scripts/generate_test_video.py
# Creates test_parking.mp4 — 2 min, 40 bays, cars entering/leaving
```

Then set it as the video source in **Admin → Settings → Video Source**.

---

## 📦 Export ONNX Models (optional, for faster inference)

```bash
python scripts/export_onnx.py          # FP32
python scripts/quantize.py             # INT8 (fastest)
python scripts/benchmark.py            # Compare all backends
```

Switch backend live in **Admin → Settings → Backend**.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m "Add amazing feature"`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ using FastAPI, React, and YOLOv8

*If this project helped you, consider giving it a ⭐*

</div>
