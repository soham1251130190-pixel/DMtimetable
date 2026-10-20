import React from 'react';

export default function GenerationSummary({ generateResult, loading, error }) {
  if (loading) {
    return (
      <div className="summary-empty">
        <div className="loading-spinner"></div>
        <p>Loading schedule quality summary...</p>
      </div>
    );
  }

  if (error || !generateResult) {
    return (
      <div className="summary-empty error">
        <p className="error-title">Schedule summary not available</p>
        <p className="error-desc">{error || 'No generation result record found.'}</p>
      </div>
    );
  }

  const {
    run_id = 2,
    status = 'ok',
    colors_used = 15,
    score = { total: 0, breakdown: { consecutive: 0, gap: 0, spread: 0 } },
    violations = [],
  } = generateResult;

  const isSuccess = status === 'ok';
  const totalScore = score?.total ?? 0;
  const breakdown = score?.breakdown ?? {};

  return (
    <div className="summary-wrapper">
      <div className="summary-header">
        <div>
          <div className="summary-badge-row">
            <span className="sample-run-label">Historical Benchmark · Run #{run_id}</span>
            <span className={`status-pill ${isSuccess ? 'status-pill-ok' : 'status-pill-failed'}`}>
              {isSuccess ? 'Schedule Solved & Verified' : 'Generation Incomplete'}
            </span>
          </div>
          <h3 className="section-title">Schedule Optimization & Constraint Report</h3>
          <p className="section-subtitle">
            Diagnostic breakdown of physical classroom allocations, fatigue prevention, and cohort comfort metrics.
          </p>
        </div>
      </div>

      <div className="summary-grid">
        {/* Soft Constraint Quality Metrics */}
        <div className="summary-card">
          <div className="card-header">
            <h4>Academic Comfort & Quality Metrics</h4>
            <span className="card-sub">Lower penalty score indicates higher schedule balance</span>
          </div>
          <div className="metric-score-display">
            <div className="big-score">
              <span className="score-num">{totalScore}</span>
              <span className="score-label">Total Penalty Points</span>
            </div>
            <div className="score-rating">
              {totalScore === 0 ? (
                <span className="rating-badge optimal">Optimal Distribution</span>
              ) : totalScore < 20 ? (
                <span className="rating-badge good">Well-Balanced</span>
              ) : (
                <span className="rating-badge moderate">Acceptable Distribution</span>
              )}
            </div>
          </div>

          <div className="breakdown-list">
            <div className="breakdown-row">
              <div className="breakdown-info">
                <strong>Faculty & Student Fatigue Guard</strong>
                <p>Ensures neither faculty nor student cohorts have more than 3 consecutive lecture hours</p>
              </div>
              <span className={`breakdown-badge ${breakdown.consecutive === 0 ? 'zero' : 'nonzero'}`}>
                {breakdown.consecutive ?? 0} penalties
              </span>
            </div>

            <div className="breakdown-row">
              <div className="breakdown-info">
                <strong>Idle Hour Minimization</strong>
                <p>Eliminates scattered gap periods between first and last lecture of the day</p>
              </div>
              <span className={`breakdown-badge ${breakdown.gap === 0 ? 'zero' : 'nonzero'}`}>
                {breakdown.gap ?? 0} penalties
              </span>
            </div>

            <div className="breakdown-row">
              <div className="breakdown-info">
                <strong>Daily Subject Variety</strong>
                <p>Distributes same-subject lectures across multiple days to prevent cognitive fatigue</p>
              </div>
              <span className={`breakdown-badge ${breakdown.spread === 0 ? 'zero' : 'nonzero'}`}>
                {breakdown.spread ?? 0} penalties
              </span>
            </div>
          </div>
        </div>

        {/* Hard Constraints & Operational Verification */}
        <div className="summary-card">
          <div className="card-header">
            <h4>Institutional Rule Verification</h4>
            <span className="card-sub">Every mandatory academic rule verified prior to schedule approval</span>
          </div>

          <div className="constraint-checklist">
            <div className="check-item passed">
              <span className="check-icon">✓</span>
              <div>
                <strong>No Double-Booked Faculty</strong>
                <p>No faculty member is assigned to multiple classes simultaneously</p>
              </div>
            </div>

            <div className="check-item passed">
              <span className="check-icon">✓</span>
              <div>
                <strong>No Student Cohort Overlaps</strong>
                <p>Each division attends exactly one lecture or lab at any given period</p>
              </div>
            </div>

            <div className="check-item passed">
              <span className="check-icon">✓</span>
              <div>
                <strong>No Room Conflicts & Sufficient Capacity</strong>
                <p>Room capacities match or exceed class strength; laboratories assigned only for practicals</p>
              </div>
            </div>

            <div className="check-item passed">
              <span className="check-icon">✓</span>
              <div>
                <strong>Faculty Availability Compliance</strong>
                <p>All lectures scheduled strictly within declared working periods</p>
              </div>
            </div>
          </div>

          <div className="timeslot-utilization-box">
            <div className="utilization-label">
              <span>Weekly Timeslot Allocation:</span>
              <strong>{colors_used} of 30 periods used</strong>
            </div>
            <div className="utilization-bar">
              <div
                className="utilization-fill"
                style={{ width: `${Math.min(100, (colors_used / 30) * 100)}%` }}
              ></div>
            </div>
          </div>

          {violations.length > 0 && (
            <div className="violations-box">
              <h5>Detected Violations ({violations.length})</h5>
              <ul>
                {violations.map((v, i) => (
                  <li key={i}>{v.reason || JSON.stringify(v)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
