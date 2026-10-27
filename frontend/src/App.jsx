import React, { useState, useEffect, useCallback } from 'react';
import OverviewCards from './components/OverviewCards.jsx';
import TimetableTable from './components/TimetableTable.jsx';
import ConflictGraph from './components/ConflictGraph.jsx';
import GenerationSummary from './components/GenerationSummary.jsx';
import {
  getDatasets,
  getLatestTimetable,
  getConflictGraph,
  generateTimetable,
  API_BASE_URL,
} from './api/client.js';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('timetable'); // 'timetable' | 'graph' | 'summary'

  // Academic Scope & Dataset Selection
  const [datasets, setDatasets] = useState([
    { id: 'default', name: 'Standard College Schedule (Medium — 72 Sessions)' },
    { id: 'small', name: 'Department Sample (Small — 16 Sessions)' },
    { id: 'stress', name: 'Multi-Department Benchmark (Stress — 261 Sessions)' },
    { id: 'impossible', name: 'Over-Constrained Test Case (Demonstrates Conflicts)' },
  ]);
  const [selectedDataset, setSelectedDataset] = useState('default');

  // Live Database Timetable & Graph State
  const [timetableData, setTimetableData] = useState(null);
  const [timetableLoading, setTimetableLoading] = useState(true);
  const [timetableError, setTimetableError] = useState(null);

  const [graphData, setGraphData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState(null);

  // Generation Workflow State
  const [isGenerating, setIsGenerating] = useState(false);
  const [notification, setNotification] = useState(null);

  // Load available datasets from the backend on mount
  useEffect(() => {
    getDatasets()
      .then((data) => {
        if (data?.datasets?.length > 0) {
          setDatasets(data.datasets);
        }
      })
      .catch(() => {
        // Retain standard default choices if endpoint unreachable
      });
  }, []);

  // Fetch timetable and graph data from the backend whenever dataset changes
  const loadScheduleData = useCallback(async (datasetId) => {
    setTimetableLoading(true);
    setTimetableError(null);
    setGraphLoading(true);
    setGraphError(null);

    // 1. Fetch Latest Timetable
    try {
      const tt = await getLatestTimetable(datasetId);
      setTimetableData(tt);
    } catch (err) {
      setTimetableError(err.message || 'Unable to load timetable schedule.');
    } finally {
      setTimetableLoading(false);
    }

    // 2. Fetch Conflict Graph
    try {
      const g = await getConflictGraph(datasetId);
      setGraphData(g);
    } catch (err) {
      setGraphError(err.message || 'Unable to load conflict graph.');
    } finally {
      setGraphLoading(false);
    }
  }, []);

  useEffect(() => {
    loadScheduleData(selectedDataset);
  }, [selectedDataset, loadScheduleData]);

  // Handle Timetable Generation Request
  const handleGenerate = async () => {
    setIsGenerating(true);
    setNotification(null);

    try {
      const result = await generateTimetable({
        dataset: selectedDataset,
        seed: 42,
        maxAttempts: 10,
        optimizerIterations: 500,
      });

      setNotification({
        type: 'success',
        title: 'Timetable Generated Successfully',
        message: `Schedule created and verified. ${
          result.colors_used ? `${result.colors_used} periods allocated.` : ''
        } Results saved to database.`,
      });

      // Reload fresh schedule and conflict network
      await loadScheduleData(selectedDataset);
    } catch (err) {
      setNotification({
        type: 'error',
        title: 'Generation Incomplete',
        message:
          err.message ||
          'The scheduler was unable to find a conflict-free allocation satisfying all hard constraints.',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="app-container">
      {/* Academic Header with Generator Controls */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">🏛️</div>
          <div>
            <h1 className="app-title">College Timetable Manager</h1>
            <p className="app-subtitle">
              Automated Academic Scheduling & Faculty Allocation System
            </p>
          </div>
        </div>

        {/* Schedule Generation & Dataset Selection Toolbar */}
        <div className="header-actions">
          <div className="dataset-control">
            <label htmlFor="dataset-select" className="dataset-label">
              Academic Scope:
            </label>
            <select
              id="dataset-select"
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              disabled={isGenerating}
              className="dataset-select"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="generate-btn"
            onClick={handleGenerate}
            disabled={isGenerating}
            title="Trigger automated schedule generation algorithm"
          >
            {isGenerating ? (
              <>
                <span className="btn-spinner"></span>
                <span>Generating Schedule...</span>
              </>
            ) : (
              <>
                <span className="btn-icon">⚡</span>
                <span>Generate Timetable</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Generation Status Alert Banner */}
      {notification && (
        <div className={`notification-banner ${notification.type}`}>
          <div className="notification-content">
            <span className="notification-icon">
              {notification.type === 'success' ? '✓' : '⚠️'}
            </span>
            <div>
              <strong className="notification-title">{notification.title}</strong>
              <p className="notification-desc">{notification.message}</p>
            </div>
          </div>
          <button
            type="button"
            className="notification-close"
            onClick={() => setNotification(null)}
            aria-label="Dismiss notification"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main>
        {/* Overview Metric Cards */}
        <OverviewCards
          timetable={timetableData}
          generateResult={null}
        />

        {/* View Navigation Tabs */}
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
            🕸️ Class & Faculty Conflict Map
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
          >
            📋 Policy Compliance & Verification
          </button>
        </nav>

        {/* View Panes */}
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
            timetable={timetableData}
            generateResult={null}
            loading={timetableLoading}
            error={timetableError}
          />
        )}
      </main>
    </div>
  );
}
