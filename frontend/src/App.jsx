import React, { useState, useEffect, useCallback } from 'react';
import OverviewCards from './components/OverviewCards.jsx';
import TimetableTable from './components/TimetableTable.jsx';
import ConflictGraph from './components/ConflictGraph.jsx';
import GenerationSummary from './components/GenerationSummary.jsx';
import './App.css';

/**
 * Normalizes API endpoint URLs to avoid accidental double slashes or duplicated '/api' segments.
 * Handles inputs like 'https://service.onrender.com', 'https://service.onrender.com/', or 'https://service.onrender.com/api'.
 */
export const buildApiUrl = (baseUrl, endpoint = '/api/health') => {
  const base = (baseUrl || 'http://127.0.0.1:8000').trim().replace(/\/+$/, '');
  const path = endpoint.trim().startsWith('/') ? endpoint.trim() : `/${endpoint.trim()}`;

  // If base already ends with /api and endpoint starts with /api/, avoid duplicate /api/api
  if (base.endsWith('/api') && path.startsWith('/api/')) {
    return `${base}${path.slice(4)}`;
  }
  // If base already ends with the target endpoint, avoid duplicate
  if (base.endsWith(path)) {
    return base;
  }
  return `${base}${path}`;
};

// Vite environment variable with local development fallback
const rawApiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const API_BASE_URL = rawApiBase.replace(/\/+$/, '');
export const HEALTH_CHECK_URL = buildApiUrl(API_BASE_URL, '/api/health');

export default function App() {
  const [activeTab, setActiveTab] = useState('timetable'); // 'timetable' | 'graph' | 'summary'

  // Backend Health State (independent of static sample data)
  const [backendOnline, setBackendOnline] = useState(null); // null (checking) | true | false

  // Mock Data States
  const [timetableData, setTimetableData] = useState(null);
  const [timetableLoading, setTimetableLoading] = useState(true);
  const [timetableError, setTimetableError] = useState(null);

  const [graphData, setGraphData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState(null);

  const [generateResult, setGenerateResult] = useState(null);
  const [generateLoading, setGenerateLoading] = useState(true);
  const [generateError, setGenerateError] = useState(null);

  // Check Backend Health using normalized HEALTH_CHECK_URL
  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(HEALTH_CHECK_URL, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        setBackendOnline(data.status === 'ok');
      } else {
        setBackendOnline(false);
      }
    } catch {
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Load Static Mock Data (Always separate and resilient)
  useEffect(() => {
    // 1. Timetable Mock
    fetch('/mock-data/timetable.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setTimetableData(data);
        setTimetableLoading(false);
      })
      .catch((err) => {
        setTimetableError(err.message);
        setTimetableLoading(false);
      });

    // 2. Conflict Graph Mock
    fetch('/mock-data/graph.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setGraphData(data);
        setGraphLoading(false);
      })
      .catch((err) => {
        setGraphError(err.message);
        setGraphLoading(false);
      });

    // 3. Generation Result Mock
    fetch('/mock-data/generate_result.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setGenerateResult(data);
        setGenerateLoading(false);
      })
      .catch((err) => {
        setGenerateError(err.message);
        setGenerateLoading(false);
      });
  }, []);

  return (
    <div className="app-container">
      {/* Brand Header with Connectivity Indicator */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">🏛️</div>
          <div>
            <h1 className="app-title">Timetable Manager</h1>
            <p className="app-subtitle">Academic Schedule & Faculty Workload Portal</p>
          </div>
        </div>

        <div className="header-connectivity">
          <span
            className={`connectivity-pill ${
              backendOnline === true
                ? 'online'
                : backendOnline === false
                ? 'offline'
                : 'checking'
            }`}
            title={`Backend endpoint: ${HEALTH_CHECK_URL}`}
          >
            <span className="connectivity-dot"></span>
            {backendOnline === true && 'API Online'}
            {backendOnline === false && 'API Offline (Sample View)'}
            {backendOnline === null && 'Connecting...'}
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main>
        {/* Overview Cards (always visible) */}
        <OverviewCards
          timetable={timetableData}
          generateResult={generateResult}
        />

        {/* Section Tabs */}
        <nav className="tab-navigation" aria-label="Schedule views">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'timetable' ? 'active' : ''}`}
            onClick={() => setActiveTab('timetable')}
          >
            📅 Weekly Schedule
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'graph' ? 'active' : ''}`}
            onClick={() => setActiveTab('graph')}
          >
            🕸️ Course Conflict Network
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
          >
            📊 Institutional Rules & Verification
          </button>
        </nav>

        {/* Tab Views */}
        {activeTab === 'timetable' && (
          <TimetableTable
            timetable={timetableData}
            loading={timetableLoading}
            error={timetableError}
          />
        )}

        {activeTab === 'graph' && (
          <ConflictGraph
            graphData={graphData}
            loading={graphLoading}
            error={graphError}
          />
        )}

        {activeTab === 'summary' && (
          <GenerationSummary
            generateResult={generateResult}
            loading={generateLoading}
            error={generateError}
          />
        )}
      </main>
    </div>
  );
}
