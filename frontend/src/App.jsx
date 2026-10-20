import React, { useState, useEffect } from 'react';
import OverviewCards from './components/OverviewCards.jsx';
import TimetableTable from './components/TimetableTable.jsx';
import ConflictGraph from './components/ConflictGraph.jsx';
import GenerationSummary from './components/GenerationSummary.jsx';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('timetable'); // 'timetable' | 'graph' | 'summary'

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

  // Load Static Mock Data
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
      {/* Simplified Brand Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">🏛️</div>
          <div>
            <h1 className="app-title">Timetable Manager</h1>
            <p className="app-subtitle">Academic Schedule & Faculty Workload Portal</p>
          </div>
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
