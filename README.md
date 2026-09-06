# 🚦 TrafficIQ: Smart Urban Mobility & Traffic Congestion AI Platform

> **VANET-based Real-Time Congestion Detection, Predictive Forecasting, Adaptive Signal Control, and Google Maps Navigation Platform.**

---

## 📌 Executive Summary & Purpose

Urban traffic congestion leads to severe economic losses, travel delays, fuel wastage, and environmental pollution. Existing VANET (Vehicular Ad-hoc Network) research relies heavily on SUMO simulations and static numerical outputs with no visual or end-user interface.

**TrafficIQ** bridges this gap by translating multi-sensor SUMO data into an **interactive, Google Maps-style AI Navigation Platform**. It combines Fuzzy Analytical Hierarchy Process (FAHP) and Entropy Weight Method (EWM) hybrid scoring with real-time predictive forecasting, adaptive traffic signal automation, emergency vehicle green corridors, and environmental carbon offset tracking.

---

## 🏗️ System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Data Ingestion Layer
        A[SUMO Simulation & Sensor Data] --> B[Sensor Fusion Engine]
    end

    subgraph AI Algorithm Engine
        B --> C[Fuzzy K-Means Clustering]
        C --> D[FAHP + EWM Hybrid Scoring]
        D --> E[ANOVA Statistical Validation]
    end

    subgraph Backend API Layer (Flask)
        E --> F[Flask REST API Server :5000]
        F --> G[Predictive Time-Series AI Engine]
        F --> H[Adaptive Signal Phase Controller ASCS]
        F --> I[Emergency Green Corridor & Incident Injector]
    end

    subgraph Frontend Layer (React + Vite + Leaflet)
        G --> J[Google Maps Navigation Dashboard :5173]
        H --> J
        I --> J
    end
```

---

## 🚀 Complete Feature & Roadmap Breakdown

### 1. 🗺️ Google Maps Navigation UI & Callout Tooltips
- **Speech Bubble Badges**: Direct map tooltips anchored to route midpoints displaying travel time (e.g., `21 min`), toll/fuel cost in Indian Rupees (`₹25`), and route recommendations.
- **Teardrop Location Pins**: Red destination teardrop pin at *Kalinga Hospital Junction* and blue origin pulsing pins at entry corridors.
- **Suggested Routes Side Panel**: Ranked stack of routes highlighting the **★ RECOMMENDED BEST ROUTE**.

### 2. 🚗 Multi-Modal Transport Routing
- Supports 4 vehicle modes:
  - 🚗 **Passenger Car**: Standard congestion routing.
  - 🛵 **Two-Wheeler / Scooter**: Filters narrow bypasses and accounts for faster traffic filtering.
  - ⚡ **Electric Vehicle (EV)**: Prioritizes energy-efficient routes.
  - 🚛 **Heavy Freight Truck**: Restricts narrow corridor passages and applies weight delay multipliers.

### 3. 🔮 AI Predictive Traffic Forecasting (`/api/forecast`)
- Time-series exponential trend forecasting for **T+15 min**, **T+30 min**, and **T+60 min**.
- Dynamic `AreaChart` visualizing future traffic curves for all 4 Bhubaneswar corridors.
- Proactive travel window recommendations (*"Clear to proceed"* vs. *"Peak traffic alert in 30m"*).

### 4. 🚦 Adaptive Traffic Signal Control System (ASCS) (`/api/signals`)
- Automates traffic light timings at Kalinga Hospital Junction.
- Dynamically allocates **green signal extensions** (+0s to +25s) based on FAHP congestion indices.

### 5. 🚑 Emergency Vehicle Green Corridor Override (`/api/emergency`)
- One-click **"Ambulance Green Wave"** activation button in the topbar.
- Forces a zero-delay priority green phase along the designated emergency corridor while clearing alternative routes.

### 6. 💥 Interactive Incident Injector Simulator (`/api/simulate_incident`)
- Inject simulated real-time incidents: **Accident (💥)**, **Heavy Rain (🌧)**, or **Construction Work (🚧)**.
- Triggers instant recalculation of FAHP weights, re-ranks optimal routes, and updates speech bubbles on the map.

### 7. 🧠 Explainable AI (XAI) Congestion Inspector (`/api/xai/<route_id>`)
- Provides human-readable AI rationale explaining bottleneck root causes (e.g. *"Vehicle speed drops to 3.20 m/s with high CO₂ idling emissions"*).

### 8. 🌿 Eco-Routing & Carbon Offset Calculator (`/api/eco_summary`)
- Calculates net CO₂ reduction in grams/hour.
- Calculates fuel cost savings in **Indian Rupees (₹)** per hour.
- Displays tree offset equivalents (`🌳 4.2 Trees Offset Equivalent`).

### 9. 📡 VANET V2X Mesh Network Health Inspector (`/api/vanet_mesh`)
- Tracks Packet Delivery Ratio (**98.6% PDR**), network latency (**12.4 ms**), and active vehicle OBU nodes.
- Monitors individual Roadside Units (RSUs) across Bhubaneswar junctions.

### 10. 🔊 Hands-Free Voice AI Guidance Assistant
- Integrates browser Web Speech Synthesis API (`window.speechSynthesis`).
- Speaks turn-by-turn rerouting instructions and incident alerts.

### 11. 📄 Scientific Research Report Exporter
- One-click print/export generating a publication-formatted summary including ANOVA statistical validation, FAHP matrices, and route rankings.

---

## 💻 Installation & How to Run

### Prerequisites
- **Python 3.8+**
- **Node.js (v18+)** and **npm**

---

### Step 1: Run the Backend API Server

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python main.py
```
> Server will start at **`http://127.0.0.1:5000`**.

---

### Step 2: Run the Web Dashboard Frontend

```powershell
cd web-dashboard
npm install
npm run dev
```
> Access the web dashboard at **`http://localhost:5173`**.

---

## 🎯 Presentation & Review Script (5-Minute Demonstration)

1. **Problem & Overview (30s)**: Open `http://localhost:5173` and introduce how VANET SUMO research is translated into a live Google Maps AI UI.
2. **Google Maps Navigation & Modes (1m)**: Demonstrate speech bubble badges (`₹25 · 21 min`), route cards, and switch between Car (🚗) and Two-Wheeler (🛵) modes.
3. **Incident Injection & Dynamic Rerouting (1.5m)**: Click `💥 Accident` on Route 1. Watch the AI recalculate FAHP scores and reroute traffic live while Voice AI announces the alert.
4. **Novel Features (1m)**: Showcase **AI Forecasting** (`AreaChart`), **Ambulance Green Wave**, and **VANET V2X Mesh** tabs.
5. **Conclusion & Scientific Export (30s)**: Click **"Export Scientific Report"** to show ANOVA statistics, FAHP matrices, and carbon savings in Indian Rupees (₹).
