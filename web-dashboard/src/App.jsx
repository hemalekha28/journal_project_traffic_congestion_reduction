import React, { useEffect, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Polyline, Popup, Marker } from 'react-leaflet';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  CartesianGrid, Legend, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, AreaChart, Area
} from 'recharts';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const API = 'http://localhost:5000';
const CENTER = [20.3147, 85.8203];

const ROUTE_GEOMETRIES = {
  route1: { name: 'Via Jaydev Vihar Corridor',   positions: [[20.2984, 85.8162], [20.3022, 85.8187], [20.3060, 85.8182], [20.3111, 85.8193], [20.3147, 85.8203]], distanceKm: '3.8 km' },
  route2: { name: 'Via Damana Square',         positions: [[20.3402, 85.8176], [20.3338, 85.8193], [20.3245, 85.8196], [20.3188, 85.8200], [20.3147, 85.8203]], distanceKm: '4.2 km' },
  route3: { name: 'Via Acharya Vihar Expressway',  positions: [[20.2949, 85.8275], [20.3005, 85.8252], [20.3051, 85.8234], [20.3102, 85.8217], [20.3147, 85.8203]], distanceKm: '4.5 km' },
  route4: { name: 'Main NH16 Arterial Road',          positions: [[20.3150, 85.8330], [20.3148, 85.8270], [20.3147, 85.8203]], distanceKm: '2.9 km' },
};

const STATUS_COLOR = { HIGH: '#d93025', MEDIUM: '#f9ab00', LOW: '#137333' };

const NAV_ITEMS = [
  { id: 'dashboard',  label: 'Google Navigation', icon: '🗺' },
  { id: 'forecast',   label: 'AI Forecasting',    icon: '🔮' },
  { id: 'vanet',      label: 'VANET V2X Mesh',    icon: '📡' },
  { id: 'analytics',  label: 'Analytics & XAI',   icon: '📊' },
  { id: 'emissions',  label: 'Eco-Routing',       icon: '🌿' },
  { id: 'rankings',   label: 'Route Rankings',     icon: '🏆' },
];

const MODES = [
  { id: 'CAR',          label: 'Passenger Car', icon: '🚗' },
  { id: 'TWO_WHEELER',  label: 'Two-Wheeler',   icon: '🛵' },
  { id: 'EV',           label: 'Electric Vehicle', icon: '⚡' },
  { id: 'TRUCK',        label: 'Freight Truck', icon: '🚛' },
];

const createDestinationPinIcon = () => L.divIcon({
  className: 'gmaps-pin-container',
  html: `<div class="gmaps-dest-pin"><svg width="36" height="46" viewBox="0 0 24 32" fill="none"><path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 20 12 20s12-11 12-20c0-6.63-5.37-12-12-12zm0 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4z" fill="#ea4335"/><circle cx="12" cy="12" r="4.5" fill="#ffffff"/></svg></div>`,
  iconSize: [36, 46],
  iconAnchor: [18, 46]
});

const createOriginPinIcon = (label) => L.divIcon({
  className: 'gmaps-origin-container',
  html: `<div class="gmaps-origin-pin" title="${label}"><div class="gmaps-origin-core"></div><div class="gmaps-origin-pulse"></div></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

const createRouteBadgeIcon = (id, isBest, isSelected, score, status, speed, incident, vehicleIcon) => {
  const speedVal = speed || 10;
  const minutes = Math.max(12, Math.round(26 - (speedVal * 1.1) + (score || 10) * 0.12));
  const tollRupees = Math.round(25 + ((score || 10) % 4) * 10);
  
  const badgeClass = isBest ? 'bubble-best' : (isSelected ? 'bubble-selected' : 'bubble-alt');
  const incidentIcon = incident ? (incident.type === 'ACCIDENT' ? '💥' : incident.type === 'RAIN' ? '🌧' : '🚧') : null;

  return L.divIcon({
    className: 'gmaps-route-badge-wrapper',
    html: `
      <div class="gmaps-speech-bubble ${badgeClass}">
        <div class="bubble-body">
          <span class="bubble-icon">${incidentIcon || vehicleIcon || (isBest ? '🛵' : '🚗')}</span>
          <div class="bubble-details">
            <div class="bubble-time">${minutes} min ${incidentIcon ? '(Delayed)' : ''}</div>
            <div class="bubble-sub">₹${tollRupees} · ${isBest ? 'Fastest' : status}</div>
          </div>
        </div>
        <div class="bubble-arrow"></div>
      </div>
    `,
    iconSize: [130, 54],
    iconAnchor: [65, 54]
  });
};

function ScoreRing({ score, maxScore, color }) {
  const pct = Math.min((score || 0) / (maxScore || 1), 1);
  const r = 28;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);
  return (
    <svg width="64" height="64" viewBox="0 0 70 70" style={{ flexShrink: 0 }}>
      <circle cx="35" cy="35" r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
      <circle cx="35" cy="35" r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={`${circ}`} strokeDashoffset={`${offset}`} strokeLinecap="round"
        style={{ transform: 'rotate(-90deg)', transformOrigin: '35px 35px', transition: 'stroke-dashoffset 1s ease' }}
      />
      <text x="35" y="40" textAnchor="middle" fill="#0f172a" fontSize="12" fontWeight="800" fontFamily="Inter, sans-serif">
        {Math.round(pct * 100)}%
      </text>
    </svg>
  );
}

function KPICard({ title, value, subtitle, color, pulse, icon }) {
  return (
    <div className="kpi-card" style={{ '--kpi-accent': color }}>
      <div className="kpi-icon-wrap" style={{ background: color + '15', color }}>{icon}</div>
      <div className="kpi-details">
        <div className="kpi-label">{title}</div>
        <div className="kpi-value">{value}</div>
        <div className="kpi-sub">{subtitle}</div>
      </div>
      {pulse && <div className="kpi-pulse-dot" style={{ background: color }} />}
    </div>
  );
}

function RouteModal({ routeId, congestion, history, onClose }) {
  const data = congestion[routeId];
  const hist = history[routeId] || {};
  const geom = ROUTE_GEOMETRIES[routeId] || {};
  const color = STATUS_COLOR[data?.status] || '#1a73e8';
  const [xaiText, setXaiText] = useState('Analyzing congestion factors...');

  useEffect(() => {
    axios.get(`${API}/api/xai/${routeId}`)
      .then(res => setXaiText(res.data.xai_explanation))
      .catch(() => setXaiText('Explanation unavailable.'));
  }, [routeId]);

  if (!data) return null;

  const totalRoutes = Object.keys(congestion).length;
  const maxScore = Math.max(...Object.values(congestion).map(d => d.congestion_score), 1);

  const stats = [
    { label: 'Average Speed',    value: hist.speed            ? `${hist.speed.toFixed(2)} m/s`           : 'N/A', icon: '⚡' },
    { label: 'CO₂ Emissions',    value: hist.co2_emission     ? `${hist.co2_emission.toFixed(1)} mg`      : 'N/A', icon: '💨' },
    { label: 'CO Emissions',     value: hist.co_emission      ? `${hist.co_emission.toFixed(2)} mg`       : 'N/A', icon: '🌫' },
    { label: 'NOx Emissions',    value: hist.nox_emission     ? `${hist.nox_emission.toFixed(3)} mg`      : 'N/A', icon: '⚗' },
    { label: 'Fuel Consumed',    value: hist.fuel_consumption ? `${hist.fuel_consumption.toFixed(3)} ml/s` : 'N/A', icon: '⛽' },
    { label: 'FAHP Index',       value: data.congestion_score?.toFixed(2),                                         icon: '📊' },
    { label: 'Hybrid AI Score',  value: data.hybrid_score?.toFixed(2) || 'N/A',                                    icon: '🧠' },
    { label: 'Corridor Rank',    value: `#${data.rank} of ${totalRoutes}`,                                         icon: '🏆' },
    { label: 'Traffic Density',  value: `${data.status} DENSITY`,                                                  icon: '🚦' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-route-id" style={{ color }}>{routeId.replace('route', 'ROUTE ').toUpperCase()}</div>
            <div className="modal-route-name">{geom.name}</div>
          </div>
          <span className="modal-badge" style={{ background: color + '15', color, border: `1px solid ${color}40` }}>
            {data.status} TRAFFIC
          </span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="xai-insight-box">
            <div className="xai-title">🧠 Explainable AI (XAI) Insight</div>
            <div className="xai-content">{xaiText}</div>
          </div>

          {data.alternate_route && (
            <div className="gmaps-reroute-box">
              <div className="reroute-header">✨ Intelligent Rerouting Recommendation</div>
              <div className="reroute-body">
                Avoid delay by taking <strong>{data.alternate_route.replace('route', 'Route ').toUpperCase()}</strong>.
                <div className="reroute-sub">Reason: {data.alternate_reason}</div>
              </div>
            </div>
          )}
          
          <div className="modal-score-section">
            <ScoreRing score={data.congestion_score} maxScore={maxScore} color={color} />
            <div>
              <div className="modal-score-label">FAHP Congestion Score</div>
              <div className="modal-score-num" style={{ color }}>{data.congestion_score?.toFixed(2)}</div>
              <div className="modal-rank">Ranked #{data.rank} among monitored corridors</div>
            </div>
          </div>

          <div className="modal-stats-grid">
            {stats.map(s => (
              <div key={s.label} className="modal-stat">
                <span className="modal-stat-icon">{s.icon}</span>
                <div>
                  <div className="modal-stat-label">{s.label}</div>
                  <div className="modal-stat-value">{s.value}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab]         = useState('dashboard');
  const [transportMode, setTransportMode] = useState('CAR');
  const [voiceActive, setVoiceActive]     = useState(false);
  const [congestion, setCongestion]       = useState({});
  const [history, setHistory]             = useState({});
  const [forecasts, setForecasts]         = useState({});
  const [signals, setSignals]             = useState({});
  const [ecoSummary, setEcoSummary]       = useState(null);
  const [vanetMesh, setVanetMesh]         = useState(null);
  const [emergencyMode, setEmergencyMode] = useState({ active: false });
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [focusedRoute, setFocusedRoute]   = useState('route1');
  const [clock, setClock]                 = useState(new Date());

  const speakAlert = useCallback((text) => {
    if (!voiceActive || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  }, [voiceActive]);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [congRes, histRes, foreRes, sigRes, ecoRes, vanetRes] = await Promise.all([
        axios.get(`${API}/api/congestion?mode=${transportMode}`),
        axios.get(`${API}/api/history`),
        axios.get(`${API}/api/forecast`),
        axios.get(`${API}/api/signals`),
        axios.get(`${API}/api/eco_summary`),
        axios.get(`${API}/api/vanet_mesh`),
      ]);
      const congData = congRes.data.data || {};
      setCongestion(congData);
      setHistory(histRes.data.data || {});
      setForecasts(foreRes.data.data || {});
      setSignals(sigRes.data.data || {});
      setEcoSummary(ecoRes.data.data || null);
      setVanetMesh(vanetRes.data.data || null);
      if (congRes.data.emergency_mode) setEmergencyMode(congRes.data.emergency_mode);

      const bestId = Object.keys(congData).sort((a, b) => congData[a].congestion_score - congData[b].congestion_score)[0];
      if (bestId && !focusedRoute) setFocusedRoute(bestId);

    } catch {
      setError('Backend offline or unreachable. Make sure the Flask server is running on port 5000.');
    } finally {
      setLoading(false);
    }
  }, [transportMode, focusedRoute]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const handleSimulateIncident = async (routeId, type) => {
    try {
      await axios.post(`${API}/api/simulate_incident`, { route_id: routeId, type });
      await fetchData();
      if (type !== 'CLEAR') {
        speakAlert(`Alert: ${type} simulated on corridor ${routeId}. Dynamic rerouting activated.`);
      }
    } catch {
      alert('Failed to inject incident.');
    }
  };

  const handleToggleEmergency = async () => {
    try {
      const nextState = !emergencyMode.active;
      await axios.post(`${API}/api/emergency`, { active: nextState, corridor: focusedRoute || 'route1' });
      setEmergencyMode({ active: nextState, corridor: focusedRoute });
      await fetchData();
      if (nextState) {
        speakAlert(`Emergency Ambulance Corridor activated on corridor ${focusedRoute}. Signal phase overridden.`);
      }
    } catch {
      alert('Failed to toggle emergency mode.');
    }
  };

  const handleExportReport = () => {
    window.print();
  };

  if (loading) return (
    <div className="state-screen">
      <div className="loader-ring" />
      <p className="state-msg">Initializing Smart Multi-Modal Traffic AI Platform...</p>
    </div>
  );

  if (error) return (
    <div className="state-screen">
      <div className="error-icon">⚠</div>
      <h2 className="error-title">Connection Failed</h2>
      <p className="state-msg" style={{ marginBottom: 24, maxWidth: 420 }}>{error}</p>
      <button className="btn-primary" onClick={() => { setLoading(true); fetchData(); }}>Retry Connection</button>
    </div>
  );

  const routeEntries = Object.entries(congestion).sort((a, b) => a[1].congestion_score - b[1].congestion_score);
  const bestRouteId = routeEntries[0]?.[0] || 'route1';
  const bestRouteData = congestion[bestRouteId];
  const activeModeObj = MODES.find(m => m.id === transportMode);

  const currentTab = NAV_ITEMS.find(n => n.id === activeTab);

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" fill="#1a73e8"/></svg>
          </div>
          <div className="brand-text-wrap">
            <span className="brand-title">Google Maps AI</span>
            <span className="brand-sub">VANET Mobility Platform</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-clock">{clock.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>
          <div className="sidebar-date">{clock.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}</div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="topbar">
          <div>
            <h1 className="topbar-title">{currentTab?.label}</h1>
            <p className="topbar-sub">Smart Intelligent Traffic Systems · Kalinga Hospital Junction</p>
          </div>
          <div className="topbar-actions">
            {/* Voice Guidance Assistant Toggle */}
            <button
              className={`voice-btn ${voiceActive ? 'active' : ''}`}
              onClick={() => {
                const next = !voiceActive;
                setVoiceActive(next);
                if (next) speakAlert("Voice Guidance Assistant Activated. Live traffic updates enabled.");
              }}
            >
              {voiceActive ? '🔊 Voice Guidance ON' : '🔇 Enable Voice AI'}
            </button>

            {/* Emergency Ambulance Switch */}
            <button
              className={`emergency-btn ${emergencyMode.active ? 'active' : ''}`}
              onClick={handleToggleEmergency}
            >
              🚑 {emergencyMode.active ? 'EMERGENCY CORRIDOR ACTIVE' : 'Ambulance Green Wave'}
            </button>

            {/* Export Scientific Report */}
            <button className="refresh-btn" onClick={handleExportReport}>
              📄 Export Scientific Report
            </button>
          </div>
        </header>

        <div className="dashboard-wrap">
          {/* Multi-Modal Mode Bar */}
          <div className="mode-selector-bar">
            <span className="mode-bar-title">Select Mode of Transport:</span>
            <div className="mode-buttons-group">
              {MODES.map(mode => (
                <button
                  key={mode.id}
                  className={`mode-pill ${transportMode === mode.id ? 'active' : ''}`}
                  onClick={() => setTransportMode(mode.id)}
                >
                  <span>{mode.icon}</span> {mode.label}
                </button>
              ))}
            </div>
          </div>

          {emergencyMode.active && (
            <div className="emergency-banner">
              <strong>🚑 EMERGENCY GREEN CORRIDOR ACTIVE</strong> — Signal override in progress for corridor {focusedRoute.toUpperCase()}.
            </div>
          )}

          {/* KPI Row */}
          <div className="kpi-row">
            <KPICard title="Optimal Path" value={bestRouteId.replace('route', 'Route ').toUpperCase()} subtitle={`Mode: ${activeModeObj?.label}`} color="#137333" icon={activeModeObj?.icon || '🛵'} />
            <KPICard title="VANET PDR Ratio" value={`${vanetMesh?.pdr_percent || 98.6}%`} subtitle={`${vanetMesh?.active_v2x_vehicles || 418} Active Vehicles`} color="#1a73e8" icon="📡" />
            <KPICard title="Carbon Offset Saved" value={`${ecoSummary?.co2_saved_grams_per_hr || 0} g/hr`} subtitle={`≈ ${ecoSummary?.trees_planted_equivalent || 0} Trees Planted`} color="#34a853" icon="🌿" />
            <KPICard title="Fuel Cost Savings" value={`₹${ecoSummary?.inr_fuel_saved_per_hr || 0}`} subtitle="Saved per travel hour" color="#f9ab00" icon="⛽" />
          </div>

          {/* ── TAB 1: GOOGLE NAVIGATION ── */}
          {activeTab === 'dashboard' && (
            <div className="tab-content">
              <div className="gmaps-layout-container">
                {/* Route Selection Panel */}
                <div className="gmaps-side-panel">
                  <div className="gmaps-search-box">
                    <div className="search-dots-col">
                      <div className="blue-dot" /><div className="dot-line" /><div className="red-pin-icon">📍</div>
                    </div>
                    <div className="search-inputs-col">
                      <div className="location-input-field"><span className="field-label">Origin:</span><span className="field-val">Bhubaneswar Entry Corridors</span></div>
                      <div className="location-divider" />
                      <div className="location-input-field"><span className="field-label">Destination:</span><span className="field-val">Kalinga Hospital Junction</span></div>
                    </div>
                  </div>

                  <div className="route-options-header">
                    <span className="options-title">Suggested Routes ({activeModeObj?.label})</span>
                    <span className="options-count">{routeEntries.length} options</span>
                  </div>

                  <div className="route-cards-stack">
                    {routeEntries.map(([id, data]) => {
                      const isBest = id === bestRouteId;
                      const isFocused = id === focusedRoute;
                      const geom = ROUTE_GEOMETRIES[id] || {};
                      const hist = history[id] || {};
                      const sig = signals[id] || {};
                      const minutes = Math.max(12, Math.round(26 - ((hist.speed || 10) * 1.1) + (data.congestion_score || 10) * 0.12));

                      return (
                        <div
                          key={id}
                          className={`gmaps-route-card ${isBest ? 'recommended' : ''} ${isFocused ? 'focused' : ''}`}
                          onClick={() => { setFocusedRoute(id); setSelectedRoute(id); }}
                        >
                          {isBest && <div className="best-route-badge">★ RECOMMENDED BEST ROUTE</div>}
                          
                          <div className="card-header-row">
                            <div className="route-title-group">
                              <span className="route-icon">{data.active_incident ? '⚠️' : activeModeObj?.icon}</span>
                              <div>
                                <div className="route-main-name">{id.replace('route', 'Route ').toUpperCase()}</div>
                                <div className="route-sub-name">{geom.name}</div>
                              </div>
                            </div>
                            <div className="route-eta-group">
                              <div className="route-eta-time">{minutes} min</div>
                              <div className="route-dist">{geom.distanceKm}</div>
                            </div>
                          </div>

                          <div className="signal-bar-badge">
                            🚦 Signal: Green {sig.total_green_sec}s (+{sig.ai_extension_sec}s ASCS Extension)
                          </div>

                          <div className="simulator-actions" onClick={e => e.stopPropagation()}>
                            <span className="sim-label">Inject Incident:</span>
                            <button className="sim-btn" title="Simulate Accident" onClick={() => handleSimulateIncident(id, 'ACCIDENT')}>💥</button>
                            <button className="sim-btn" title="Simulate Rain" onClick={() => handleSimulateIncident(id, 'RAIN')}>🌧</button>
                            <button className="sim-btn" title="Simulate Construction" onClick={() => handleSimulateIncident(id, 'CONSTRUCTION')}>🚧</button>
                            <button className="sim-btn clear" title="Clear Incident" onClick={() => handleSimulateIncident(id, 'CLEAR')}>🧹</button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Map Panel */}
                <div className="gmaps-map-panel">
                  <div className="map-panel-header">
                    <span>🗺 Live Route Navigation View ({activeModeObj?.label})</span>
                    <div className="map-layer-tag">Traffic Layer Active</div>
                  </div>

                  <div className="gmaps-leaflet-wrap">
                    <MapContainer center={CENTER} zoom={14} style={{ height: '100%', width: '100%' }}>
                      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                      <Marker position={CENTER} icon={createDestinationPinIcon()} />

                      {routeEntries.map(([id, data]) => {
                        const geom = ROUTE_GEOMETRIES[id];
                        if (!geom) return null;
                        const isBest = id === bestRouteId;
                        const isFocused = id === focusedRoute;
                        const hist = history[id] || {};
                        const color = isBest ? '#1a73e8' : (isFocused ? '#2563eb' : '#70757a');

                        return (
                          <React.Fragment key={id}>
                            <Polyline
                              positions={geom.positions}
                              color={color}
                              weight={isBest ? 8 : 6}
                              opacity={0.9}
                              eventHandlers={{ click: () => { setFocusedRoute(id); setSelectedRoute(id); } }}
                            />
                            <Marker position={geom.positions[0]} icon={createOriginPinIcon(geom.name)} />
                            <Marker
                              position={geom.positions[Math.floor(geom.positions.length / 2)]}
                              icon={createRouteBadgeIcon(id, isBest, isFocused, data.congestion_score, data.status, hist.speed, data.active_incident, activeModeObj?.icon)}
                              eventHandlers={{ click: () => { setFocusedRoute(id); setSelectedRoute(id); } }}
                            />
                          </React.Fragment>
                        );
                      })}
                    </MapContainer>

                    <div className="gmaps-floating-legend">
                      <div className="legend-title">Route Layers</div>
                      <div className="legend-item"><div className="line-sample best" /> Recommended Route</div>
                      <div className="legend-item"><div className="line-sample alt" /> Alternative Corridor</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 2: AI FORECASTING ── */}
          {activeTab === 'forecast' && (
            <div className="tab-content">
              <div className="glass-panel">
                <div className="panel-title">🔮 Time-Series Traffic Congestion Forecast (T+60 Min)</div>
                <div style={{ height: 380, padding: '16px 8px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={[
                      { time: 'Now', route1: 35, route2: 82, route3: 45, route4: 28 },
                      { time: '+15m', route1: 38, route2: 88, route3: 48, route4: 30 },
                      { time: '+30m', route1: 42, route2: 91, route3: 40, route4: 25 },
                      { time: '+60m', route1: 30, route2: 72, route3: 35, route4: 22 },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="time" stroke="#64748b" />
                      <YAxis stroke="#64748b" domain={[0, 100]} />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="route1" name="Jaydev Vihar" stroke="#1a73e8" fill="#1a73e8" fillOpacity={0.15} />
                      <Area type="monotone" dataKey="route2" name="Damana Sq" stroke="#ea4335" fill="#ea4335" fillOpacity={0.15} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 3: VANET V2X MESH ── */}
          {activeTab === 'vanet' && (
            <div className="tab-content">
              <div className="glass-panel">
                <div className="panel-title">📡 VANET V2X Mesh Network & Roadside Unit (RSU) Monitor</div>
                <div className="vanet-stats-grid">
                  <div className="vanet-stat-box"><span className="v-num">{vanetMesh?.pdr_percent}%</span><span className="v-lbl">Packet Delivery Ratio (PDR)</span></div>
                  <div className="vanet-stat-box"><span className="v-num">{vanetMesh?.latency_ms} ms</span><span className="v-lbl">Network Communication Latency</span></div>
                  <div className="vanet-stat-box"><span className="v-num">{vanetMesh?.active_v2x_vehicles}</span><span className="v-lbl">Active Vehicle OBU Nodes</span></div>
                  <div className="vanet-stat-box"><span className="v-num">{vanetMesh?.rsus_online} / {vanetMesh?.rsus_total}</span><span className="v-lbl">RSU Infrastructure Status</span></div>
                </div>

                <div className="rsu-table-container">
                  <div className="rsu-table-header"><span>RSU Identifier</span><span>Location Node</span><span>Communication Status</span><span>PDR Efficiency</span></div>
                  {vanetMesh?.rsus?.map(rsu => (
                    <div key={rsu.id} className="rsu-table-row">
                      <span className="rsu-id">{rsu.id}</span>
                      <span>{rsu.location}</span>
                      <span><span className="rsu-badge">{rsu.status}</span></span>
                      <span className="rsu-pdr">{rsu.pdr}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 4: ANALYTICS & XAI ── */}
          {activeTab === 'analytics' && (
            <div className="tab-content">
              <div className="analytics-grid">
                <div className="glass-panel">
                  <div className="panel-title">🕸 Multi-Parameter Radar Analysis</div>
                  <div style={{ height: 380, padding: '10px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={[
                        { param: 'Speed', route1: 80, route2: 45, route3: 65, route4: 90 },
                        { param: 'CO2', route1: 30, route2: 75, route3: 50, route4: 20 },
                        { param: 'NOx', route1: 25, route2: 80, route3: 40, route4: 15 },
                        { param: 'Fuel', route1: 35, route2: 70, route3: 45, route4: 25 },
                      ]}>
                        <PolarGrid stroke="#e2e8f0" />
                        <PolarAngleAxis dataKey="param" />
                        <Radar name="Route 1" dataKey="route1" stroke="#1a73e8" fill="#1a73e8" fillOpacity={0.15} />
                        <Radar name="Route 2" dataKey="route2" stroke="#ea4335" fill="#ea4335" fillOpacity={0.15} />
                        <Legend />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="glass-panel">
                  <div className="panel-title">🧠 Explainable AI (XAI) Inspection</div>
                  <div className="xai-stack">
                    {Object.keys(congestion).map(id => (
                      <div key={id} className="xai-item" onClick={() => setSelectedRoute(id)}>
                        <div className="xai-item-title">{id.replace('route', 'Route ').toUpperCase()} — Click for XAI Rationale</div>
                        <div className="xai-item-body">
                          Score: <strong>{congestion[id]?.congestion_score.toFixed(1)}</strong> | Status: <strong style={{ color: STATUS_COLOR[congestion[id]?.status] }}>{congestion[id]?.status}</strong>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 5: ECO-ROUTING ── */}
          {activeTab === 'emissions' && (
            <div className="tab-content">
              <div className="glass-panel">
                <div className="panel-title">🌿 Environmental Impact & Fuel Cost Savings (INR)</div>
                <div className="eco-stats-banner">
                  <div className="eco-box"><span className="eco-num">₹{ecoSummary?.inr_fuel_saved_per_hr || 0}</span><span className="eco-lbl">Fuel Savings / Hour</span></div>
                  <div className="eco-box"><span className="eco-num">{ecoSummary?.co2_saved_grams_per_hr || 0} g</span><span className="eco-lbl">CO₂ Emissions Reduced</span></div>
                  <div className="eco-box"><span className="eco-num">🌳 {ecoSummary?.trees_planted_equivalent || 0}</span><span className="eco-lbl">Tree Offset Equivalent</span></div>
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 6: RANKINGS ── */}
          {activeTab === 'rankings' && (
            <div className="tab-content">
              <div className="glass-panel">
                <div className="panel-title">🏆 FAHP Route Rankings & Scientific Summary</div>
                <div className="rank-table">
                  <div className="rank-header"><span>Rank</span><span>Route</span><span>FAHP Score</span><span>Status</span><span>Action</span></div>
                  {routeEntries.map(([id, data]) => (
                    <div key={id} className="rank-row">
                      <span className="rank-medal">#{data.rank}</span>
                      <span className="rank-id">{id.replace('route', 'Route ').toUpperCase()}</span>
                      <span className="rank-score" style={{ color: STATUS_COLOR[data.status] }}>{data.congestion_score.toFixed(2)}</span>
                      <span><span className="rank-badge" style={{ background: STATUS_COLOR[data.status] + '18', color: STATUS_COLOR[data.status] }}>{data.status}</span></span>
                      <button className="btn-view" onClick={() => { setFocusedRoute(id); setSelectedRoute(id); setActiveTab('dashboard'); }}>Navigate →</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {selectedRoute && (
        <RouteModal
          routeId={selectedRoute}
          congestion={congestion}
          history={history}
          onClose={() => setSelectedRoute(null)}
        />
      )}
    </div>
  );
}
