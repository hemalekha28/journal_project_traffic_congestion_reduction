# Cognitive VANET-Based Traffic Congestion Detection with 
# Real-Time Dashboard Visualization for Smart Urban Mobility

## Overview
This project is a smart traffic congestion detection system that 
builds upon and extends the research paper:

> "Integrating Cognitive Intelligence and VANET for Effective 
> Traffic Congestion Detection in Smart Urban Mobility" 
> (Mohanty et al., IEEE Access, 2025)

The system detects traffic congestion using an improved machine 
learning algorithm on VANET-simulated data and delivers results 
through a real-time web dashboard and mobile application — 
bridging the gap between academic research and usable product.

---

## Problem Statement
Existing VANET-based congestion detection systems produce results 
as static numbers visible only to researchers. There is no 
end-to-end system that detects congestion, improves upon classic 
fuzzy methods, and delivers actionable information to traffic 
authorities and drivers in real time.

---

## Our Solution
- Simulate realistic urban traffic using SUMO simulator
- Improve detection algorithm beyond FKM + FAHP (base paper)
- Expose results through a REST API backend
- Visualize congestion live on a web dashboard (for authorities)
- Notify and reroute via mobile app (for drivers)

---

## Key Features
- Real-time congestion detection from SUMO traffic simulation
- Improved ML-based detection over classical fuzzy clustering
- Color-coded live road map (Green / Yellow / Red)
- Alternate route suggestions for congested roads
- Web dashboard for traffic authority monitoring
- Mobile app for driver notifications and rerouting
- Statistical validation using ANOVA

---

## How We Differ From The Base Paper

| Factor | Base Paper | Our System |
|---|---|---|
| Algorithm | FKM + FAHP | Improved ML |
| Output | MATLAB tables | Live visual map |
| Interface | None | Web + Mobile |
| Real-time | No | Yes |
| End users | Researchers only | Authorities + Drivers |
| Route suggestion | No | Yes |

---

## Tech Stack

### Simulation
- SUMO (Simulation of Urban Mobility)
- Python TraCI API

### Backend
- Python
- FastAPI / Flask
- WebSockets (real-time data streaming)

### Web Dashboard
- React.js
- Leaflet.js / OpenStreetMap
- Chart.js (congestion graphs)

### Mobile App
- React Native

### Database
- Firebase / MongoDB

