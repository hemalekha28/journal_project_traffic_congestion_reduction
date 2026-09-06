import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polyline, Popup } from 'react-leaflet';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Kalinga Hospital Junction
const CENTER = [20.3147, 85.8203];

// Pre-defined path geometries for the demo
const GEOMETRIES = [
  { name: 'Via Jaydev Vihar', positions: [[20.3147, 85.8203], [20.3200, 85.8150]] },
  { name: 'Via Damana', positions: [[20.3147, 85.8203], [20.3100, 85.8250]] },
  { name: 'Via Acharya Vihar', positions: [[20.3147, 85.8203], [20.3050, 85.8150]] },
  { name: 'Main Road', positions: [[20.3147, 85.8203], [20.3200, 85.8250]] }
];

const COLOR_MAP = { 
  HIGH: 'var(--color-high)', 
  MEDIUM: 'var(--color-medium)', 
  LOW: 'var(--color-low)' 
};

export default function App() {
  const [congestion, setCongestion] = useState({});
  const [history, setHistory] = useState({});
  const [status, setStatus] = useState(null);
  const [rerouteState, setRerouteState] = useState({}); // { [route_id]: { loading: bool, data: obj, open: bool } }
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // NOTE: Data fetching logic kept exactly as requested
  const fetchData = async () => {
    try {
      setError(null);
      
      const [congRes, histRes, statRes] = await Promise.all([
        axios.get('http://localhost:5000/api/congestion'),
        axios.get('http://localhost:5000/api/history'),
        axios.get('http://localhost:5000/api/status')
      ]);

      setCongestion(congRes.data.data);
      setHistory(histRes.data.data);
      setStatus(statRes.data);
    } catch (err) {
      console.error(err);
      setError('Backend offline or unreachable.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleToggleReroute = async (routeId) => {
    const cleanId = routeId.startsWith('!') ? routeId : `!${routeId}`;
    const current = rerouteState[cleanId] || {};

    if (current.open) {
      setRerouteState(prev => ({ ...prev, [cleanId]: { ...current, open: false } }));
      return;
    }

    if (current.data) {
      setRerouteState(prev => ({ ...prev, [cleanId]: { ...current, open: true } }));
      return;
    }

    setRerouteState(prev => ({ ...prev, [cleanId]: { loading: true, open: true } }));
    try {
      const res = await axios.get(`http://localhost:5000/routes/${cleanId}/reroute-suggestion`);
      setRerouteState(prev => ({
        ...prev,
        [cleanId]: { loading: false, open: true, data: res.data }
      }));
    } catch (err) {
      setRerouteState(prev => ({
        ...prev,
        [cleanId]: {
          loading: false,
          open: true,
          data: { available: false, message: 'Failed to connect to rerouting service.' }
        }
      }));
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post('http://localhost:5000/api/refresh');
      await fetchData();
    } catch (err) {
      console.error(err);
      setError('Pipeline refresh failed.');
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--text-secondary)' }}>
        Loading Traffic Analysis...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--color-high)', marginBottom: '1rem' }}>⚠️ Connection Error</h2>
        <p>{error}</p>
        <button className="btn" onClick={() => { setLoading(true); fetchData(); }} style={{ marginTop: '1rem' }}>
          Retry Connection
        </button>
      </div>
    );
  }

  // Derive top 10 for alerts
  const allRoutes = Object.entries(congestion);
  const top10 = [...allRoutes]
    .sort((a, b) => b[1].congestion_score - a[1].congestion_score)
    .slice(0, 10);

  // Derive stats
  const totalRoutes = allRoutes.length;
  const highCount = allRoutes.filter(([_, d]) => d.status === 'HIGH').length;
  const medCount = allRoutes.filter(([_, d]) => d.status === 'MEDIUM').length;
  const lowCount = allRoutes.filter(([_, d]) => d.status === 'LOW').length;

  // Prepare Chart Data for Top 10 Congestion Scores
  const chartData = top10.map(([id, data]) => ({
    name: `Route !${id.replace('!', '')}`,
    score: Math.round(data.congestion_score),
    status: data.status
  }));

  // Prepare authentic Rank Comparison Chart Data (direct from CSV API)
  const rankComparisonData = top10.map(([id, data]) => ({
    name: `!${id.replace('!', '')}`,
    fahp_rank: data.rank || 0,
    entropy_rank: data.entropy_rank || data.rank || 0
  }));

  return (
    <div className="app-layout">
      {/* 1. Header Bar */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo-placeholder">T</div>
          <div className="project-title">Traffic Analysis Platform</div>
        </div>
        <div className="header-right">
          {status && (
            <span className="timestamp">
              Last updated: {status.last_updated}
            </span>
          )}
          <button 
            className="btn btn-secondary" 
            onClick={handleRefresh} 
            disabled={refreshing}
          >
            {refreshing ? '🔄 Refreshing...' : '▶ Re-run Simulation'}
          </button>
        </div>
      </header>

      <main className="main-content">
        
        {/* 2. Summary Stats Bar */}
        <div className="stats-bar">
          <div className="stat-card">
            <span className="stat-title">Total Routes Monitored</span>
            <span className="stat-value">{totalRoutes}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">High Congestion</span>
            <span className="stat-value high">{highCount}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Medium Congestion</span>
            <span className="stat-value medium">{medCount}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Low Congestion</span>
            <span className="stat-value low">{lowCount}</span>
          </div>
        </div>

        {/* 3. Middle Row: Map & Alerts */}
        <div className="middle-row">
          
          <div className="panel">
            <div className="panel-header">Live Traffic Map</div>
            <div className="map-wrapper">
              <MapContainer center={CENTER} zoom={15} style={{ height: '100%', width: '100%' }} zoomControl={false}>
                <TileLayer 
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' 
                />
                
                {top10.map(([id, data], idx) => {
                  const geom = GEOMETRIES[idx % GEOMETRIES.length];
                  const hist = history[id] || {};
                  const cColor = COLOR_MAP[data.status] || '#888';
                  
                  return (
                    <Polyline 
                      key={id} 
                      positions={geom.positions} 
                      color={cColor} 
                      weight={8} 
                      opacity={0.9}
                    >
                      <Popup>
                        <div style={{ fontFamily: 'var(--font-sans)', color: 'var(--text-primary)' }}>
                          <strong style={{fontSize: '14px', color: cColor}}>Route {id.replace('!', '')}</strong>
                          <br/>
                          <span style={{color: 'var(--text-secondary)'}}>{geom.name}</span>
                          
                          <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '12px' }}>
                            <div><strong>Speed:</strong> {hist.speed ? hist.speed.toFixed(2) + ' m/s' : 'N/A'}</div>
                            <div><strong>CO2:</strong> {hist.co2_emission ? hist.co2_emission.toFixed(1) : 'N/A'}</div>
                            <div><strong>CO:</strong> {hist.co_emission ? hist.co_emission.toFixed(2) : 'N/A'}</div>
                            <div><strong>NOx:</strong> {hist.nox_emission ? hist.nox_emission.toFixed(2) : 'N/A'}</div>
                          </div>
                        </div>
                      </Popup>
                    </Polyline>
                  );
                })}
              </MapContainer>
              
              <div className="map-legend">
                <div className="legend-item">
                  <div className="legend-color" style={{background: 'var(--color-high)'}}></div>
                  High Congestion
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: 'var(--color-medium)'}}></div>
                  Medium Congestion
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: 'var(--color-low)'}}></div>
                  Low Congestion
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">Top 10 Congestion Alerts</div>
            <div className="panel-content">
              <div className="alerts-list">
                {top10.map(([id, data]) => {
                  const cColor = COLOR_MAP[data.status] || '#888';
                  const cleanId = id.startsWith('!') ? id : `!${id}`;
                  const rState = rerouteState[cleanId] || {};
                  
                  return (
                    <div key={id} className="alert-item">
                      <div className="alert-header">
                        <span className="route-id" style={{ color: cColor }}>Route {id.replace('!', '')}</span>
                        <span className={`tier-badge ${data.status.toLowerCase()}`}>{data.status}</span>
                      </div>
                      <div className="alert-stats">
                        <span><strong>Score:</strong> {data.congestion_score.toFixed(1)}</span>
                        <span><strong>Rank:</strong> #{data.rank}</span>
                      </div>
                      
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => handleToggleReroute(id)}
                        style={{ marginTop: '0.5rem', width: '100%' }}
                      >
                        {rState.open ? 'Hide Reroute Suggestion' : 'View Reroute Suggestion'}
                      </button>
                      
                      {rState.open && (
                        <div className="reroute-card" style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                          {rState.loading ? (
                            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Loading reroute analysis...</p>
                          ) : rState.data?.available ? (
                            <div>
                              <p style={{ fontSize: '13px', marginBottom: '0.5rem' }}>
                                <strong>Suggested Action ({rState.data.recommended_variant}):</strong> Reroute 50% of heavy-overlap fleet via secondary arterial.
                              </p>
                              <div className="reroute-metrics" style={{ display: 'flex', gap: '0.5rem' }}>
                                <div className="metric-pill" style={{ background: 'rgba(34,197,94,0.1)', color: '#16a34a', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 600 }}>
                                  Travel Time: -{rState.data.travel_time_improvement_pct}%
                                </div>
                                <div className="metric-pill" style={{ background: 'rgba(34,197,94,0.1)', color: '#16a34a', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 600 }}>
                                  CO₂ / Fuel: -{rState.data.co2_fuel_improvement_pct}%
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                              {rState.data?.message || "Rerouting simulation data currently available only for bottleneck Route !257."}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

        </div>

        {/* 4. Bottom Row: Charts */}
        <div className="bottom-row">
          <div className="panel">
            <div className="panel-header">Top 10 Congestion Scores</div>
            <div className="panel-content no-pad" style={{ height: '300px', padding: '1rem' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis 
                    dataKey="name" 
                    stroke="var(--text-secondary)" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={false} 
                    angle={-25}
                    textAnchor="end"
                  />
                  <YAxis stroke="var(--text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={{fill: 'rgba(0,0,0,0.05)'}} 
                    contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLOR_MAP[entry.status]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="panel">
            <div className="panel-header">FAHP vs Entropy Rank Comparison (Top 10)</div>
            <div className="panel-content no-pad" style={{ height: '300px', padding: '1rem' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rankComparisonData} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis 
                    dataKey="name" 
                    stroke="var(--text-secondary)" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={false} 
                    angle={-25}
                    textAnchor="end"
                  />
                  <YAxis 
                    stroke="var(--text-secondary)" 
                    fontSize={12} 
                    tickLine={false} 
                    axisLine={false} 
                    reversed 
                    domain={[1, 359]} 
                  />
                  <Tooltip 
                    cursor={{fill: 'rgba(0,0,0,0.05)'}} 
                    contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="fahp_rank" name="FAHP Rank" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="entropy_rank" name="Entropy Rank" fill="var(--color-medium)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
