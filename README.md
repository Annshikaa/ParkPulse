<div align="center">

# 🚗 ParkPulse AI

### Next-Generation Smart Parking Intelligence Platform

Transforming ordinary CCTV cameras into autonomous parking management systems using Artificial Intelligence, Computer Vision, and Real-Time Analytics.

<img src="https://img.shields.io/badge/AI-Powered-00C853?style=for-the-badge" />
<img src="https://img.shields.io/badge/YOLOv8-Computer%20Vision-orange?style=for-the-badge" />
<img src="https://img.shields.io/badge/Real--Time-WebSockets-blue?style=for-the-badge" />
<img src="https://img.shields.io/badge/FastAPI-Backend-success?style=for-the-badge" />
<img src="https://img.shields.io/badge/React-TypeScript-61DAFB?style=for-the-badge" />
<img src="https://img.shields.io/badge/Production-Ready-brightgreen?style=for-the-badge" />

### 🎯 Detect • Track • Analyze • Automate

> Monitor parking occupancy in real time using CCTV cameras and AI-powered vehicle detection.

---

![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange?style=flat-square)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=flat-square&logo=pytorch)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-38BDF8?style=flat-square&logo=tailwindcss)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

</div>

---

# 🌍 Why ParkPulse?

Finding parking spaces remains one of the most frustrating urban mobility challenges.

Studies show that drivers spend a significant portion of their journey searching for available parking spaces, leading to:

- Increased traffic congestion
- Fuel wastage
- Carbon emissions
- Revenue loss for parking operators
- Poor user experience

ParkPulse solves this problem using Artificial Intelligence and Computer Vision.

By leveraging CCTV camera feeds and real-time vehicle detection, ParkPulse automatically identifies occupied and vacant parking spaces, updates slot availability instantly, and provides actionable insights through analytics dashboards.

### No sensors.
### No manual monitoring.
### Just cameras and intelligence.

---

# 🚀 Overview

ParkPulse transforms ordinary CCTV cameras into intelligent parking monitoring systems.

The platform continuously analyzes live video streams, detects vehicles using AI models, maps them to parking spaces, updates occupancy status in real time, manages bookings, processes payments, and generates advanced analytics.

```text
CCTV Camera
      │
      ▼
YOLOv8 Vehicle Detection
      │
      ▼
Vehicle Tracking (ByteTrack)
      │
      ▼
Parking Slot Mapping
      │
      ▼
Occupancy Detection
      │
      ▼
Database Update
      │
      ▼
WebSocket Broadcast
      │
      ▼
Live Dashboard
```

---

# 💼 Business Impact

ParkPulse is designed for:

🏢 Corporate Campuses

🏬 Shopping Malls

🏥 Hospitals

🎓 Universities

✈️ Airports

🚉 Railway Stations

🏙️ Smart Cities

### Benefits

✔ Reduce parking search time

✔ Improve parking utilization

✔ Automate parking monitoring

✔ Reduce manpower requirements

✔ Increase operator revenue

✔ Enhance customer experience

✔ Generate operational insights

✔ Enable data-driven decision making

---

# ✨ Key Features

## 🤖 AI-Powered Computer Vision

- YOLOv8 vehicle detection
- ByteTrack multi-object tracking
- Real-time occupancy detection
- Polygon-based parking slot mapping
- IoU-based occupancy classification
- Hysteresis smoothing to prevent flickering
- Multi-camera support
- GPU and CPU inference

---

## 🗺️ Smart Slot Editor

- Draw parking slots visually
- Polygon and rectangle support
- Row generation tool
- Slot customization
- Auto-detect parking areas
- Live synchronization with CV engine

---

## 📡 Real-Time Monitoring

- Live CCTV feed
- Vehicle detection overlays
- Occupancy tracking
- WebSocket updates
- Per-slot monitoring
- Live event logs
- FPS monitoring

---

## 📅 Booking Management

- Live slot availability
- Online booking system
- Vehicle registration
- Conflict detection
- Booking lifecycle management
- Auto-completion on vehicle exit

---

## 💳 Payment Integration

- Razorpay integration
- Secure transactions
- Demo payment mode
- Actual dwell-time billing
- Automated billing calculations

---

## 📊 Analytics Dashboard

- Occupancy heatmaps
- Revenue analytics
- Peak hour analysis
- Historical occupancy tracking
- Slot utilization reports
- Vehicle turnover metrics
- Trend analysis

---

## 🔔 Smart Alerts

- Camera offline detection
- Unauthorized parking alerts
- Reserved slot violations
- Detection failures
- System health monitoring
- Alert severity classification

---

# ⚡ Performance Metrics

| Metric | Value |
|----------|----------|
| Detection Model | YOLOv8 |
| Tracking Engine | ByteTrack |
| Detection Accuracy | 95%+ |
| Stream Support | RTSP / IP Cameras / CCTV |
| Processing Speed | 25–30 FPS |
| Update Latency | < 500 ms |
| Occupancy Detection | Real-Time |
| Multi-Camera Support | Yes |
| Dashboard Updates | WebSocket |
| Deployment | Local / Cloud |

---

# 🏗️ System Architecture

```text
┌──────────────────────────────────────────┐
│                FRONTEND                  │
│ React + TypeScript + Tailwind + ShadCN   │
└─────────────────────┬────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────┐
│            FASTAPI BACKEND               │
│ REST APIs + Authentication + WebSockets  │
└───────────────┬───────────────┬──────────┘
                │               │
                ▼               ▼
      ┌────────────────┐  ┌───────────────┐
      │ PostgreSQL     │  │ Redis Cache   │
      └────────────────┘  └───────────────┘

                ▲
                │
                ▼

┌──────────────────────────────────────────┐
│          COMPUTER VISION ENGINE          │
│ YOLOv8 + ByteTrack + OpenCV + Shapely    │
└──────────────────────────────────────────┘
```

---

# 🧠 AI Processing Pipeline

```text
Video Frame
      │
      ▼
YOLOv8 Detection
      │
      ▼
ByteTrack Tracking
      │
      ▼
Bounding Box Extraction
      │
      ▼
Polygon IoU Calculation
      │
      ▼
Occupancy Classification
      │
      ▼
Database Update
      │
      ▼
WebSocket Push
      │
      ▼
Dashboard Refresh
```

---

# 📸 Application Screenshots

## Live Monitoring Dashboard

![Dashboard](assets/dashboard.png)

---

## AI Vehicle Detection

![Detection](assets/detection.png)

---

## Slot Editor

![Slot Editor](assets/slot-editor.png)

---

## Analytics Dashboard

![Analytics](assets/analytics.png)

---

# 🛠️ Technology Stack

| Layer | Technology |
|---------|------------|
| Frontend | React 18 |
| Language | TypeScript |
| Styling | TailwindCSS |
| UI Components | ShadCN UI |
| Backend | FastAPI |
| ORM | SQLAlchemy |
| Authentication | JWT |
| Database | SQLite / PostgreSQL |
| CV Framework | YOLOv8 |
| Tracking | ByteTrack |
| Video Processing | OpenCV |
| Geometry Engine | Shapely |
| State Management | Zustand |
| Charts | Recharts |
| Real-Time | WebSockets |
| Payments | Razorpay |

---

# 🚀 Getting Started

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/park-pulse.git

cd park-pulse
```

---

## Backend Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

---

## Run Backend

```bash
uvicorn backend.app.main:app --reload
```

---

## Open Application

```text
Frontend:
http://localhost:5173

Backend:
http://localhost:8000

API Docs:
http://localhost:8000/docs
```

---

# 🔑 Demo Credentials

| Role | Email | Password |
|--------|--------|----------|
| Admin | admin@parkpulse.io | Admin@123 |
| User | user@parkpulse.io | User@123 |

---

# 📂 Project Structure

```text
park-pulse/
│
├── backend/
│   ├── routers/
│   ├── models/
│   ├── services/
│   ├── auth/
│   └── main.py
│
├── cv/
│   ├── detector.py
│   ├── tracker.py
│   ├── slot_manager.py
│   └── pipeline.py
│
├── frontend/
│   ├── pages/
│   ├── components/
│   ├── hooks/
│   └── api/
│
├── scripts/
├── assets/
├── data/
└── requirements.txt
```

---

# 🏆 Project Highlights

✅ AI-Powered Smart Parking System

✅ Real-Time CCTV Monitoring

✅ YOLOv8 Vehicle Detection

✅ Multi-Camera Support

✅ Polygon-Based Slot Detection

✅ Booking & Payment Integration

✅ Live Analytics Dashboard

✅ Occupancy Heatmaps

✅ WebSocket-Based Updates

✅ Enterprise-Grade Architecture

---

# 🚀 Future Roadmap

- [ ] Automatic Number Plate Recognition (ANPR)
- [ ] Mobile Application
- [ ] Smart Parking Recommendations
- [ ] Parking Demand Forecasting
- [ ] Edge Deployment on NVIDIA Jetson
- [ ] Cloud Monitoring Platform
- [ ] Multi-Floor Parking Support
- [ ] Smart City API Integration

---

# 👩‍💻 Developer

## Anshika Jain

B.Tech Computer Science Engineering  
VIT Bhopal University

🌐 Portfolio: https://anshika-portfolio-seven.vercel.app/

💼 LinkedIn: https://linkedin.com/in/anshika-jain-44672a250

🐙 GitHub: https://github.com/Annshikaa

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to GitHub
5. Open a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a star!

Built with ❤️ using FastAPI, React, OpenCV, YOLOv8, and TypeScript.

</div>
