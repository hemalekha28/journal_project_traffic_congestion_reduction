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
  HIGH: 'var(--high-color)', 
  MEDIUM: 'var(--medium-color)', 
  LOW: 'var(--low-color)' 
};

export default function App() {
  const [congestion, setCongestion] = useState({});
  const [history, setHistory] = useState({});
  const [status, setStatus] = useState(null);
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

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
      <div className="state-container">
        <div className="spinner" aria-label="Loading indicator"></div>
        <p style={{color: 'var(--text-muted)'}}>Loading Traffic Analysis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-container">
        <h2 className="error-title">⚠️ Connection Error</h2>
        <p className="error-text">{error}</p>
        <button className="btn" onClick={() => { setLoading(true); fetchData(); }} aria-label="Retry connection to server">
          Retry Connection
        </button>
      </div>
    );
  }

  // Pick top 4 congested routes for the dashboard visualization
  const routeEntries = Object.entries(congestion)
    .sort((a, b) => b[1].congestion_score - a[1].congestion_score)
    .slice(0, 4);

  // Prepare Chart Data
  const chartData = routeEntries.map(([id, data], idx) => ({
    name: `Route ${id.replace('!', '')}`,
    score: Math.round(data.congestion_score),
    status: data.status
  }));

  return (
    <div className="dashboard-container" role="main" aria-label="Smart Traffic Dashboard">
      <header className="header">
        <div>
          <h1 className="header-title">Smart Traffic Dashboard</h1>
          <p className="header-subtitle">Live Congestion Analysis — Kalinga Hospital Junction</p>
        </div>
        
        <div className="controls">
          {status && (
            <span className="last-updated">
              Last updated: {status.data_last_updated}
            </span>
          )}
          <button 
            className="btn" 
            onClick={handleRefresh} 
            disabled={refreshing}
            aria-label="Re-run Congestion Detection Algorithm"
          >
            {refreshing ? '🔄 Running Pipeline...' : '▶ Re-run Algorithm'}
          </button>
        </div>
      </header>

      {/* Cards Grid */}
      <div className="cards-grid" aria-label="Route analysis cards">
        {routeEntries.map(([id, data], idx) => {
          const cColor = COLOR_MAP[data.status] || '#888';
          const routeName = GEOMETRIES[idx % GEOMETRIES.length].name;
          
          return (
            <div 
              key={id} 
              className="route-card" 
              style={{ borderColor: cColor }}
              aria-label={`Route ${id.replace('!', '')} analysis`}
            >
              <h3 className="route-name">Route {id.replace('!', '')}</h3>
              <p className="route-desc">{routeName}</p>
              
              <div>
                <span className="status-badge" style={{ backgroundColor: cColor + '20', color: cColor }}>
                  {data.status} CONGESTION
                </span>
              </div>
              
              <div className="score-text">
                FAHP Score
                <span className="score-value" style={{ color: cColor }}>
                  {data.congestion_score.toFixed(1)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="viz-section">
        {/* Map Panel */}
        <div className="panel" aria-label="Live Traffic Map Panel">
          <div className="panel-header">Live Traffic Map</div>
          <div className="map-container-wrapper">
            <MapContainer center={CENTER} zoom={15} style={{ height: '100%', width: '100%' }} zoomControl={false} aria-label="Interactive Traffic Map">
              <TileLayer 
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" 
                attribution='&copy; OpenStreetMap contributors &copy; CARTO' 
              />
              
              {routeEntries.map(([id, data], idx) => {
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
                      <strong style={{fontSize: '14px', color: cColor}}>Route {id.replace('!', '')}</strong>
                      <br/>
                      <span style={{color: 'var(--text-muted)'}}>{geom.name}</span>
                      
                      <div className="popup-grid">
                        <div className="popup-stat">
                          <strong>Speed</strong>
                          {hist.speed ? hist.speed.toFixed(2) + ' m/s' : 'N/A'}
                        </div>
                        <div className="popup-stat">
                          <strong>CO2 Emission</strong>
                          {hist.co2_emission ? hist.co2_emission.toFixed(1) + ' mg' : 'N/A'}
                        </div>
                        <div className="popup-stat">
                          <strong>CO Emission</strong>
                          {hist.co_emission ? hist.co_emission.toFixed(2) + ' mg' : 'N/A'}
                        </div>
                        <div className="popup-stat">
                          <strong>NOx Emission</strong>
                          {hist.nox_emission ? hist.nox_emission.toFixed(2) + ' mg' : 'N/A'}
                        </div>
                        <div className="popup-stat" style={{ gridColumn: 'span 2' }}>
                          <strong>Fuel Consumption</strong>
                          {hist.fuel_consumption ? hist.fuel_consumption.toFixed(2) + ' ml/s' : 'N/A'}
                        </div>
                      </div>
                    </Popup>
                  </Polyline>
                );
              })}
            </MapContainer>
            
            <div className="map-legend" aria-label="Map Legend">
              <div className="legend-item">
                <div className="legend-color" style={{background: 'var(--high-color)'}}></div>
                High Congestion
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{background: 'var(--medium-color)'}}></div>
                Medium Congestion
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{background: 'var(--low-color)'}}></div>
                Low Congestion
              </div>
            </div>
          </div>
        </div>

        {/* Chart Panel */}
        <div className="panel" aria-label="Score Comparison Chart Panel">
          <div className="panel-header">Score Comparison</div>
          <div style={{ padding: '24px 20px 20px', height: '445px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }} aria-label="Route Congestion Score Bar Chart">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  cursor={{fill: '#1e293b'}} 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
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
      </div>
    </div>
  );
}
