import React, { useEffect, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Polyline, Popup, Marker, CircleMarker } from 'react-leaflet';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  CartesianGrid, Legend, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Fix Leaflet's default icon path issues
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// ─── Constants ────────────────────────────────────────────────
const API = 'http://localhost:5000';
const CENTER = [20.3147, 85.8203];

// Realistic paths for routes converging at Kalinga Hospital Junction
const ROUTE_GEOMETRIES = {
  route1: { 
    name: 'Via Jaydev Vihar',   
    positions: [[20.2984, 85.8162], [20.3022, 85.8187], [20.3060, 85.8182], [20.3111, 85.8193], [20.3147, 85.8203]] 
  },
  route2: { 
    name: 'Via Damana',         
    positions: [[20.3402, 85.8176], [20.3338, 85.8193], [20.3245, 85.8196], [20.3188, 85.8200], [20.3147, 85.8203]] 
  },
  route3: { 
    name: 'Via Acharya Vihar',  
    positions: [[20.2949, 85.8275], [20.3005, 85.8252], [20.3051, 85.8234], [20.3102, 85.8217], [20.3147, 85.8203]] 
  },
  route4: { 
    name: 'Main Road / NH16',          
    positions: [[20.3150, 85.8330], [20.3148, 85.8270], [20.3147, 85.8203]] 
  },
};

const STATUS_COLOR = { HIGH: '#ff4757', MEDIUM: '#ffa502', LOW: '#2ed573' };
const RADAR_COLORS = ['#ff4757', '#ffa502', '#2ed573', '#60a5fa'];

const NAV_ITEMS = [
  { id: 'dashboard',  label: 'Dashboard',  icon: '⬛' },
  { id: 'analytics',  label: 'Analytics',  icon: '◈'  },
  { id: 'emissions',  label: 'Emissions',  icon: '🌿' },
  { id: 'rankings',   label: 'Rankings',   icon: '🏆' },
];

// ─── Score Ring ───────────────────────────────────────────────
function ScoreRing({ score, maxScore, color }) {
  const pct = Math.min(score / (maxScore || 1), 1);
  const r = 28;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);
  return (
    <svg width="70" height="70" viewBox="0 0 70 70" style={{ flexShrink: 0 }}>
      <circle cx="35" cy="35" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
      <circle
        cx="35" cy="35" r={r} fill="none"
        stroke={color} strokeWidth="5"
        strokeDasharray={`${circ}`} strokeDashoffset={`${offset}`}
        strokeLinecap="round"
        style={{ transform: 'rotate(-90deg)', transformOrigin: '35px 35px', transition: 'stroke-dashoffset 1.2s ease' }}
      />
      <text x="35" y="39" textAnchor="middle" fill={color} fontSize="11" fontWeight="700" fontFamily="Inter, sans-serif">
        {Math.round(pct * 100)}%
      </text>
    </svg>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────
function KPICard({ title, value, subtitle, color, pulse }) {
  return (
    <div className="kpi-card" style={{ '--kpi-color': color }}>
      <div className="kpi-label">{title}</div>
      <div className="kpi-value" style={{ color }}>{value}</div>
      <div className="kpi-sub">{subtitle}</div>
      {pulse && <div className="kpi-pulse" style={{ background: color }} />}
    </div>
  );
}

// ─── Alert Banner ─────────────────────────────────────────────
function AlertBanner({ routes, onDismiss }) {
  const highRoutes = Object.entries(routes).filter(([, v]) => v.status === 'HIGH');
  if (!highRoutes.length) return null;
  return (
    <div className="alert-banner" role="alert">
      <span className="alert-dot" />
      <span>
        <strong>⚠ HIGH CONGESTION ALERT</strong> — {highRoutes.map(([id]) => id.toUpperCase()).join(', ')} detected
        with critical congestion levels. Immediate rerouting recommended.
      </span>
      <button className="alert-close" onClick={onDismiss} aria-label="Dismiss alert">✕</button>
    </div>
  );
}

// ─── Route Detail Modal ───────────────────────────────────────
function RouteModal({ routeId, congestion, history, onClose }) {
  const data = congestion[routeId];
  const hist = history[routeId] || {};
  const geom = ROUTE_GEOMETRIES[routeId] || {};
  const color = STATUS_COLOR[data?.status] || '#888';
  if (!data) return null;

  const totalRoutes = Object.keys(congestion).length;
  const maxScore = Math.max(...Object.values(congestion).map(d => d.congestion_score), 1);

  const stats = [
    { label: 'Speed',          value: hist.speed            ? `${hist.speed.toFixed(2)} m/s`           : 'N/A', icon: '⚡' },
    { label: 'CO₂ Emission',   value: hist.co2_emission     ? `${hist.co2_emission.toFixed(1)} mg`      : 'N/A', icon: '💨' },
    { label: 'CO Emission',    value: hist.co_emission      ? `${hist.co_emission.toFixed(2)} mg`       : 'N/A', icon: '🌫' },
    { label: 'NOx Emission',   value: hist.nox_emission     ? `${hist.nox_emission.toFixed(3)} mg`      : 'N/A', icon: '⚗' },
    { label: 'Fuel Consumption', value: hist.fuel_consumption ? `${hist.fuel_consumption.toFixed(3)} ml/s` : 'N/A', icon: '⛽' },
    { label: 'FAHP Score',     value: data.congestion_score?.toFixed(2),                                         icon: '📊' },
    { label: 'Hybrid Score',   value: data.hybrid_score?.toFixed(2) || 'N/A',                                    icon: '🧠' },
    { label: 'Algorithm Rank', value: `#${data.rank} of ${totalRoutes}`,                                         icon: '🏆' },
    { label: 'Status',         value: `${data.status} CONGESTION`,                                               icon: '🚦' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-panel" onClick={e => e.stopPropagation()} style={{ '--modal-color': color }}>
        <div className="modal-header" style={{ borderColor: color + '40' }}>
          <div>
            <div className="modal-route-id" style={{ color }}>
              {routeId.replace('route', 'ROUTE ').toUpperCase()}
            </div>
            <div className="modal-route-name">{geom.name || 'Unknown Corridor'}</div>
          </div>
          <span className="modal-badge" style={{ background: color + '18', color, border: `1px solid ${color}35` }}>
            {data.status} CONGESTION
          </span>
          <button className="modal-close" onClick={onClose} aria-label="Close modal">✕</button>
        </div>

        <div className="modal-body">
          {data.alternate_route && (
            <div style={{ background: 'rgba(46, 213, 115, 0.1)', border: '1px solid rgba(46, 213, 115, 0.3)', borderRadius: 12, padding: '12px 16px', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#2ed573', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', marginBottom: 4 }}>
                <span>✨ Intelligent Rerouting</span>
              </div>
              <div style={{ fontSize: 13, color: '#f1f5f9' }}>
                Suggested Alternate: <strong>{data.alternate_route.replace('route', 'Route ').toUpperCase()}</strong>
                <div style={{ color: '#94a3b8', fontSize: 11, marginTop: 4 }}>
                  Reason: {data.alternate_reason}
                </div>
              </div>
            </div>
          )}
          <div className="modal-score-section">
            <ScoreRing score={data.congestion_score} maxScore={maxScore} color={color} />
            <div>
              <div className="modal-score-label">FAHP Congestion Score</div>
              <div className="modal-score-num" style={{ color }}>{data.congestion_score?.toFixed(2)}</div>
              <div className="modal-rank">Rank #{data.rank} of {totalRoutes} monitored routes</div>
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

// ─── Custom Recharts Tooltip ───────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', borderRadius: 10, padding: '10px 14px', fontSize: 13 }}>
      <p style={{ color: '#475569', marginBottom: 6, fontWeight: 600 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || p.fill, margin: '3px 0' }}>
          {p.name}: <strong>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ─── Main App ─────────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab]         = useState('dashboard');
  const [congestion, setCongestion]       = useState({});
  const [history, setHistory]             = useState({});
  const [status, setStatus]               = useState(null);
  const [summary, setSummary]             = useState(null);
  const [loading, setLoading]             = useState(true);
  const [refreshing, setRefreshing]       = useState(false);
  const [error, setError]                 = useState(null);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [autoRefresh, setAutoRefresh]     = useState(false);
  const [countdown, setCountdown]         = useState(30);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const [clock, setClock]                 = useState(new Date());
  const [sortKey, setSortKey]             = useState('rank');
  const [sortDir, setSortDir]             = useState('asc');
  const countdownRef = useRef(null);

  // ── Fetch all data ─────────────────────────────────────────
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [congRes, histRes, statRes, sumRes] = await Promise.all([
        axios.get(`${API}/api/congestion`),
        axios.get(`${API}/api/history`),
        axios.get(`${API}/api/status`),
        axios.get(`${API}/api/summary`),
      ]);
      setCongestion(congRes.data.data || {});
      setHistory(histRes.data.data || {});
      setStatus(statRes.data);
      setSummary(sumRes.data.data || null);
    } catch {
      setError('Backend offline or unreachable. Make sure the Flask server is running on port 5000.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Live clock ─────────────────────────────────────────────
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // ── Auto-refresh countdown ─────────────────────────────────
  useEffect(() => {
    if (!autoRefresh) {
      clearInterval(countdownRef.current);
      setCountdown(30);
      return;
    }
    setCountdown(30);
    countdownRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) { fetchData(); return 30; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(countdownRef.current);
  }, [autoRefresh, fetchData]);

  // ── Pipeline refresh ───────────────────────────────────────
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/api/refresh`);
      await fetchData();
    } catch {
      setError('Pipeline refresh failed. Check backend logs.');
      setRefreshing(false);
    }
  };

  // ── Sort handler ───────────────────────────────────────────
  const handleSort = (key) => {
    setSortDir(prev => sortKey === key ? (prev === 'asc' ? 'desc' : 'asc') : 'asc');
    setSortKey(key);
  };

  // ── Loading / Error screens ────────────────────────────────
  if (loading) return (
    <div className="state-screen">
      <div className="loader-ring" />
      <p className="state-msg">Initializing Traffic Intelligence System...</p>
    </div>
  );

  if (error) return (
    <div className="state-screen">
      <div className="error-icon">⚠</div>
      <h2 className="error-title">Connection Failed</h2>
      <p className="state-msg" style={{ marginBottom: 20, maxWidth: 400 }}>{error}</p>
      <button className="btn-primary" onClick={() => { setLoading(true); fetchData(); }}>
        Retry Connection
      </button>
    </div>
  );

  // ── Derived data ───────────────────────────────────────────
  const routeEntries = Object.entries(congestion)
    .sort((a, b) => b[1].congestion_score - a[1].congestion_score);
  const maxScore = Math.max(...routeEntries.map(([, d]) => d.congestion_score), 1);

  // Bar chart
  const barData = routeEntries.map(([id, d]) => ({
    name: id.replace('route', 'Route '),
    score: Math.round(d.congestion_score),
    status: d.status,
  }));

  // Radar chart data — normalize each param to 0–100
  const radarParams = ['speed', 'co_emission', 'co2_emission', 'nox_emission', 'fuel_consumption'];
  const paramMaxes = {};
  radarParams.forEach(p => {
    paramMaxes[p] = Math.max(...Object.values(history).map(h => h[p] || 0), 1);
  });
  const radarData = radarParams.map(param => {
    const entry = {
      param: param === 'speed' ? 'Speed'
           : param === 'co_emission'  ? 'CO'
           : param === 'co2_emission' ? 'CO₂'
           : param === 'nox_emission' ? 'NOx'
           : 'Fuel',
    };
    Object.keys(history).forEach(rid => {
      entry[rid] = parseFloat(((history[rid]?.[param] || 0) / paramMaxes[param] * 100).toFixed(1));
    });
    return entry;
  });

  // Emissions grouped bar
  const emissionsData = Object.entries(history).map(([id, d]) => ({
    name: id.replace('route', 'Route '),
    CO:   parseFloat((d.co_emission   || 0).toFixed(2)),
    NOx:  parseFloat((d.nox_emission  || 0).toFixed(3)),
  }));

  // Sorted routes for rankings tab
  const sortedRoutes = [...routeEntries].sort((a, b) => {
    let va = a[1][sortKey] ?? (sortKey === 'id' ? a[0] : 0);
    let vb = b[1][sortKey] ?? (sortKey === 'id' ? b[0] : 0);
    if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    return sortDir === 'asc' ? va - vb : vb - va;
  });

  const currentTab = NAV_ITEMS.find(n => n.id === activeTab);

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar" aria-label="Navigation sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">🚦</div>
          <span className="brand-text">TrafficIQ</span>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
              aria-current={activeTab === item.id ? 'page' : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
              {activeTab === item.id && <div className="nav-indicator" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-clock">
            {clock.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
          <div className="sidebar-date">
            {clock.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
          </div>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="main-content" role="main">
        {/* Topbar */}
        <header className="topbar">
          <div>
            <h1 className="topbar-title">{currentTab?.label ?? 'Dashboard'}</h1>
            <p className="topbar-sub">Kalinga Hospital Junction · Bhubaneswar, Odisha</p>
          </div>
          <div className="topbar-actions">
            {status && (
              <span className="status-badge">
                <span className="status-dot" />
                Updated: {status.data_last_updated}
              </span>
            )}
            <button
              className="refresh-btn"
              onClick={() => setAutoRefresh(p => !p)}
              title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh (every 30s)'}
              aria-pressed={autoRefresh}
            >
              ⟳ {autoRefresh ? `Auto ${countdown}s` : 'Auto'}
            </button>
            <button
              className={`refresh-btn ${refreshing ? 'spinning' : ''}`}
              onClick={handleRefresh}
              disabled={refreshing}
              aria-label="Re-run algorithm pipeline"
            >
              <span className="btn-icon">⟳</span> {refreshing ? 'Running...' : 'Re-run Algorithm'}
            </button>
          </div>
        </header>

        <div className="dashboard-wrap">
          {/* Alert Banner */}
          {!alertDismissed && (
            <AlertBanner routes={congestion} onDismiss={() => setAlertDismissed(true)} />
          )}

          {/* KPI Row — always visible */}
          <div className="kpi-row" aria-label="Key performance indicators">
            <KPICard
              title="Total Routes"
              value={summary?.total_routes ?? routeEntries.length}
              subtitle="Monitored corridors"
              color="#60a5fa"
            />
            <KPICard
              title="Highest Risk"
              value={summary?.worst_route?.id
                ? summary.worst_route.id.replace('route', 'Route ').toUpperCase()
                : '—'}
              subtitle={`Score: ${summary?.worst_route?.score?.toFixed(0) ?? '—'}`}
              color="#ff4757"
              pulse
            />
            <KPICard
              title="Avg Speed"
              value={summary?.avg_speed ? `${summary.avg_speed} m/s` : '—'}
              subtitle="Across all routes"
              color="#ffa502"
            />
            <KPICard
              title="Avg CO₂"
              value={summary?.avg_co2 ? `${summary.avg_co2} mg` : '—'}
              subtitle="Mean emission level"
              color="#2ed573"
            />
          </div>

          {/* ── DASHBOARD TAB ── */}
          {activeTab === 'dashboard' && (
            <div className="tab-content">
              {/* Route Cards */}
              <div className="route-list-grid" aria-label="Route congestion cards">
                {routeEntries.map(([id, data]) => {
                  const color = STATUS_COLOR[data.status] || '#888';
                  const geom = ROUTE_GEOMETRIES[id] || {};
                  return (
                    <div
                      key={id}
                      className="route-card"
                      style={{ '--card-color': color }}
                      onClick={() => setSelectedRoute(id)}
                      role="button"
                      tabIndex={0}
                      aria-label={`${id} — ${data.status} congestion. Click for details.`}
                      onKeyDown={e => e.key === 'Enter' && setSelectedRoute(id)}
                    >
                      <div className="card-top">
                        <div>
                          <div className="card-id">
                            {id.replace('route', 'Route ').toUpperCase()}
                          </div>
                          <div className="card-name">{geom.name || 'Unknown Corridor'}</div>
                        </div>
                        <ScoreRing score={data.congestion_score} maxScore={maxScore} color={color} />
                      </div>
                      <div className="card-badge" style={{ background: color + '1a', color, border: `1px solid ${color}30` }}>
                        {data.status} CONGESTION
                      </div>
                      <div className="card-score-row">
                        <span className="card-score-label">FAHP Score</span>
                        <span className="card-score-val" style={{ color }}>{data.congestion_score.toFixed(1)}</span>
                      </div>
                      <div className="card-rank">Algorithm Rank #{data.rank}</div>
                      <div className="card-hint">Click for full details →</div>
                    </div>
                  );
                })}
              </div>

              {/* Map + Bar Chart */}
              <div className="viz-row">
                {/* Map */}
                <div className="glass-panel map-panel" aria-label="Live traffic map">
                  <div className="panel-title">🗺 Live Traffic Map — Kalinga Hospital Junction</div>
                  <div className="map-wrap">
                    <MapContainer
                      center={CENTER} zoom={15}
                      style={{ height: '100%', width: '100%' }}
                      zoomControl={false}
                      aria-label="Interactive map of traffic routes"
                    >
                      <TileLayer
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        attribution="&copy; OpenStreetMap contributors"
                      />
                      {routeEntries.map(([id, data]) => {
                        const geom = ROUTE_GEOMETRIES[id];
                        if (!geom) return null;
                        const color = STATUS_COLOR[data.status];
                        const hist = history[id] || {};
                        const isAlternate = routeEntries.some(([_, rData]) => rData.status === 'HIGH' && rData.alternate_route === id);
                        
                        return (
                          <React.Fragment key={id}>
                            <Polyline 
                              positions={geom.positions} 
                              color={isAlternate ? '#2ed573' : color} 
                              weight={isAlternate ? 10 : 9} 
                              opacity={isAlternate ? 1 : 0.9}
                              dashArray={isAlternate ? "10, 15" : ""}
                              className={isAlternate ? "path-alternate" : ""}
                            >
                              <Popup>
                                <div className="popup-inner">
                                  <strong style={{ color, fontSize: 15 }}>
                                    {id.replace('route', 'Route ').toUpperCase()}
                                  </strong>
                                  <p style={{ color: '#64748b', fontSize: 12, margin: '2px 0 10px' }}>{geom.name}</p>
                                  <div className="popup-stat-row">
                                    <span>⚡ Speed:</span>
                                    <strong>{hist.speed?.toFixed(2)} m/s</strong>
                                  </div>
                                  <div className="popup-stat-row">
                                    <span>💨 CO₂:</span>
                                    <strong>{hist.co2_emission?.toFixed(1)} mg</strong>
                                  </div>
                                  <div className="popup-stat-row">
                                    <span>📊 FAHP Score:</span>
                                    <strong style={{ color }}>{data.congestion_score?.toFixed(2)}</strong>
                                  </div>
                                  {data.hybrid_score && (
                                    <div className="popup-stat-row">
                                      <span>🧠 Hybrid Score:</span>
                                      <strong style={{ color: '#a78bfa' }}>{data.hybrid_score?.toFixed(2)}</strong>
                                    </div>
                                  )}
                                  <div className="popup-stat-row">
                                    <span>🚦 Status:</span>
                                    <strong style={{ color }}>{data.status}</strong>
                                  </div>
                                </div>
                              </Popup>
                            </Polyline>
                            {/* Route Start Node */}
                            <CircleMarker 
                              center={geom.positions[0]} 
                              radius={6} 
                              pathOptions={{ color: '#fff', fillColor: color, fillOpacity: 1, weight: 2 }} 
                            />
                          </React.Fragment>
                        );
                      })}
                      <Marker position={CENTER}>
                        <Popup>
                          <strong style={{ color: '#0f172a' }}>Kalinga Hospital Junction</strong>
                        </Popup>
                      </Marker>
                    </MapContainer>
                    <div className="map-legend" aria-label="Map legend">
                      {Object.entries(STATUS_COLOR).map(([s, c]) => (
                        <div key={s} className="legend-row">
                          <div className="legend-dot" style={{ background: c, boxShadow: `0 0 6px ${c}` }} />
                          <span>{s}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bar Chart */}
                <div className="glass-panel" aria-label="Congestion score bar chart">
                  <div className="panel-title">📊 FAHP Congestion Scores</div>
                  <div style={{ padding: '20px 16px', height: 380 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                        <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="score" radius={[6, 6, 0, 0]} maxBarSize={60}>
                          {barData.map((entry, i) => (
                            <Cell key={i} fill={STATUS_COLOR[entry.status]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── ANALYTICS TAB ── */}
          {activeTab === 'analytics' && (
            <div className="tab-content">
              <div className="analytics-grid">
                {/* Radar Chart */}
                <div className="glass-panel" aria-label="Multi-parameter radar chart">
                  <div className="panel-title">🕸 Multi-Parameter Radar Analysis</div>
                  <div style={{ height: 420, padding: '16px 8px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                        <PolarGrid stroke="#e2e8f0" />
                        <PolarAngleAxis
                          dataKey="param"
                          tick={{ fill: '#475569', fontSize: 12, fontFamily: 'Inter' }}
                        />
                        <PolarRadiusAxis
                          angle={90} domain={[0, 100]}
                          tick={{ fill: '#475569', fontSize: 9 }}
                          tickCount={4}
                        />
                        {Object.keys(history).map((rid, i) => (
                          <Radar
                            key={rid}
                            name={rid.replace('route', 'Route ')}
                            dataKey={rid}
                            stroke={RADAR_COLORS[i % RADAR_COLORS.length]}
                            fill={RADAR_COLORS[i % RADAR_COLORS.length]}
                            fillOpacity={0.12}
                            strokeWidth={2}
                          />
                        ))}
                        <Legend
                          wrapperStyle={{ color: '#475569', fontSize: 12, paddingTop: 12 }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Emissions Grouped Bar */}
                <div className="glass-panel" aria-label="Emissions comparison chart">
                  <div className="panel-title">📉 CO vs NOx Emissions by Route</div>
                  <div style={{ height: 420, padding: '20px 8px 16px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={emissionsData} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                        <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend wrapperStyle={{ color: '#475569', fontSize: 12 }} />
                        <Bar dataKey="CO"  name="CO (mg)"  fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
                        <Bar dataKey="NOx" name="NOx (mg)" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={40} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── EMISSIONS TAB ── */}
          {activeTab === 'emissions' && (
            <div className="tab-content">
              {/* Summary Table */}
              <div className="glass-panel" style={{ marginBottom: 24 }} aria-label="Emissions data table">
                <div className="panel-title">🌿 Emissions Summary Table — All Routes</div>
                <div className="emissions-table">
                  <div className="em-header">
                    <span>Route</span>
                    <span>Speed (m/s)</span>
                    <span>CO (mg)</span>
                    <span>CO₂ (mg)</span>
                    <span>NOx (mg)</span>
                    <span>Fuel (ml/s)</span>
                  </div>
                  {Object.entries(history).map(([id, d]) => {
                    const cdata = congestion[id];
                    const color = STATUS_COLOR[cdata?.status] || '#888';
                    return (
                      <div key={id} className="em-row">
                        <span className="em-route" style={{ color }}>
                          {id.replace('route', 'Route ').toUpperCase()}
                        </span>
                        <span>{d.speed?.toFixed(2) ?? '—'}</span>
                        <span>{d.co_emission?.toFixed(2) ?? '—'}</span>
                        <span>{d.co2_emission?.toFixed(1) ?? '—'}</span>
                        <span>{d.nox_emission?.toFixed(3) ?? '—'}</span>
                        <span>{d.fuel_consumption?.toFixed(3) ?? '—'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Per-route Emission Progress Bars */}
              <div className="cards-grid-2" aria-label="Per-route emissions breakdown">
                {Object.entries(history).map(([id, d]) => {
                  const cdata = congestion[id];
                  const color = STATUS_COLOR[cdata?.status] || '#888';
                  const histVals = Object.values(history);
                  const maxCO2  = Math.max(...histVals.map(h => h.co2_emission  || 0), 1);
                  const maxCO   = Math.max(...histVals.map(h => h.co_emission   || 0), 1);
                  const maxNOx  = Math.max(...histVals.map(h => h.nox_emission  || 0), 1);
                  const maxFuel = Math.max(...histVals.map(h => h.fuel_consumption || 0), 1);

                  const bars = [
                    { label: 'CO₂', value: d.co2_emission,    max: maxCO2,  color: '#ff6b81', unit: 'mg' },
                    { label: 'CO',  value: d.co_emission,     max: maxCO,   color: '#ffa502', unit: 'mg' },
                    { label: 'NOx', value: d.nox_emission,    max: maxNOx,  color: '#a78bfa', unit: 'mg' },
                    { label: 'Fuel',value: d.fuel_consumption,max: maxFuel, color: '#2ed573', unit: 'ml/s' },
                  ];

                  return (
                    <div key={id} className="glass-panel emission-card">
                      <div className="em-card-header" style={{ color }}>
                        {id.replace('route', 'Route ').toUpperCase()}
                        <span className="em-badge" style={{ background: color + '18', color }}>
                          {cdata?.status ?? '—'}
                        </span>
                      </div>
                      {bars.map(bar => (
                        <div key={bar.label} className="bar-item">
                          <div className="bar-label-row">
                            <span>{bar.label}</span>
                            <span style={{ color: bar.color, fontWeight: 600 }}>
                              {bar.value?.toFixed(2)} {bar.unit}
                            </span>
                          </div>
                          <div className="bar-track">
                            <div
                              className="bar-fill"
                              style={{
                                width: `${Math.min(((bar.value || 0) / bar.max) * 100, 100)}%`,
                                background: bar.color,
                                boxShadow: `0 0 8px ${bar.color}60`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── RANKINGS TAB ── */}
          {activeTab === 'rankings' && (
            <div className="tab-content">
              <div className="glass-panel" aria-label="Route rankings table">
                <div className="panel-title">🏆 FAHP Route Rankings — Congestion Severity</div>
                <div className="rank-table">
                  <div className="rank-header" role="row">
                    <span className="rank-th" onClick={() => handleSort('rank')} role="columnheader">
                      Rank {sortKey === 'rank' ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                    <span className="rank-th" onClick={() => handleSort('id')} role="columnheader">
                      Route {sortKey === 'id' ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                    <span className="rank-th" onClick={() => handleSort('congestion_score')} role="columnheader">
                      FAHP Score {sortKey === 'congestion_score' ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                    <span className="rank-th" onClick={() => handleSort('status')} role="columnheader">
                      Status {sortKey === 'status' ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                    <span className="rank-th" role="columnheader">Actions</span>
                  </div>

                  {sortedRoutes.map(([id, data], idx) => {
                    const color = STATUS_COLOR[data.status] || '#888';
                    return (
                      <div
                        key={id}
                        className="rank-row"
                        style={{ animationDelay: `${idx * 55}ms` }}
                        role="row"
                      >
                        <span className="rank-medal">
                          {data.rank === 1 ? '🥇' : data.rank === 2 ? '🥈' : data.rank === 3 ? '🥉' : `#${data.rank}`}
                        </span>
                        <span className="rank-id">
                          {id.replace('route', 'Route ').toUpperCase()}
                          <br />
                          <small style={{ color: '#475569', fontWeight: 400, fontSize: 11 }}>
                            {ROUTE_GEOMETRIES[id]?.name || ''}
                          </small>
                        </span>
                        <span className="rank-score" style={{ color }}>
                          {data.congestion_score.toFixed(2)}
                        </span>
                        <span>
                          <span
                            className="rank-badge"
                            style={{ background: color + '18', color, border: `1px solid ${color}30` }}
                          >
                            {data.status}
                          </span>
                        </span>
                        <button
                          className="btn-view"
                          onClick={() => { setSelectedRoute(id); setActiveTab('dashboard'); }}
                          aria-label={`View details for ${id}`}
                        >
                          View →
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ── Route Detail Modal ── */}
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
