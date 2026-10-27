import React from 'react';

export default function GenerationSummary({ timetable, generateResult, loading, error }) {
  if (loading) {
    return (
      <div className="summary-empty">
        <div className="loading-spinner"></div>
        <p>Verifying academic rules and schedule compliance...</p>
      </div>
    );
  }

  const result = generateResult || timetable;

  if (error || !result || result.status === 'empty') {
    return (
      <div className="summary-empty">
        <div className="empty-calendar-icon">📋</div>
        <h4 className="empty-title">No Validation Report Available</h4>
        <p className="empty-desc">
          Generate a timetable to review automated institutional rule compliance, faculty workload distribution, and facility allocations.
        </p>
      </div>
    );
  }

  const {
    run_id,
    created_at,
    status = 'completed',
    colors_used = 0,
    total_sessions = timetable?.rows?.length || 0,
    violations = [],
    score,
  } = result;

  const isSuccess = status === 'ok' || status === 'completed' || status === 'sample';
  const hasViolations = violations.length > 0;

  return (
    <div className="summary-wrapper">
      <div className="summary-header">
        <div>
          <div className="summary-badge-row">
            {run_id && <span className="sample-run-label">Schedule Version #{run_id}</span>}
            {created_at && <span className="run-timestamp">{created_at}</span>}
            <span
              className={`status-pill ${
                isSuccess && !hasViolations ? 'status-pill-ok' : 'status-pill-failed'
              }`}
            >
              {isSuccess && !hasViolations
                ? 'Verified & Approved'
                : 'Attention Required'}
            </span>
          </div>
          <h3 className="section-title">Institutional Rule Verification & Quality Report</h3>
          <p className="section-subtitle">
            Formal verification of academic scheduling rules, faculty non-overlapping constraints, and room capacities.
          </p>
        </div>
      </div>

      <div className="summary-grid">
        {/* Institutional Rule Verification Checklist */}
        <div className="summary-card">
          <div className="card-header">
            <h4>Mandatory Academic Policies</h4>
            <span className="card-sub">All four core constraints evaluated by the schedule verifier</span>
          </div>

          <div className="constraint-checklist">
            <div className={`check-item ${!hasViolations ? 'passed' : 'warning'}`}>
              <span className="check-icon">{!hasViolations ? '✓' : '!'}</span>
              <div>
                <strong>Faculty Non-Overlapping Policy</strong>
                <p>No faculty member is assigned to teach multiple divisions at the same time period.</p>
              </div>
            </div>

            <div className={`check-item ${!hasViolations ? 'passed' : 'warning'}`}>
              <span className="check-icon">{!hasViolations ? '✓' : '!'}</span>
              <div>
                <strong>Student Class Cohort Integrity</strong>
                <p>No class division is scheduled for more than one lecture or lab simultaneously.</p>
              </div>
            </div>

            <div className={`check-item ${!hasViolations ? 'passed' : 'warning'}`}>
              <span className="check-icon">{!hasViolations ? '✓' : '!'}</span>
              <div>
                <strong>Room Type & Seating Capacity</strong>
                <p>Classrooms meet cohort enrollment numbers; laboratories are reserved strictly for practicals.</p>
              </div>
            </div>

            <div className={`check-item ${!hasViolations ? 'passed' : 'warning'}`}>
              <span className="check-icon">{!hasViolations ? '✓' : '!'}</span>
              <div>
                <strong>Faculty Declared Working Hours</strong>
                <p>All sessions fall strictly within faculty-registered available teaching timeslots.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Schedule Quality & Resource Metrics */}
        <div className="summary-card">
          <div className="card-header">
            <h4>Schedule Statistics & Quality</h4>
            <span className="card-sub">Resource allocations and schedule efficiency breakdown</span>
          </div>

          <div className="timeslot-utilization-box">
            <div className="utilization-label">
              <span>Weekly Timeslot Allocation:</span>
              <strong>{colors_used} of 30 standard periods used</strong>
            </div>
            <div className="utilization-bar">
              <div
                className="utilization-fill"
                style={{ width: `${Math.min(100, (colors_used / 30) * 100)}%` }}
              ></div>
            </div>
          </div>

          <div className="breakdown-list" style={{ marginTop: '16px' }}>
            <div className="breakdown-row">
              <div className="breakdown-info">
                <strong>Scheduled Lectures & Labs</strong>
                <p>Total academic sessions placed in this schedule</p>
              </div>
              <span className="breakdown-badge">{total_sessions} Sessions</span>
            </div>

            <div className="breakdown-row">
              <div className="breakdown-info">
                <strong>Schedule Conflicts Detected</strong>
                <p>Simultaneous faculty, room, or class collisions</p>
              </div>
              <span className={`breakdown-badge ${violations.length === 0 ? 'zero' : 'violation'}`}>
                {violations.length === 0 ? '0 Clashes' : `${violations.length} Clashes`}
              </span>
            </div>

            {score && typeof score.total === 'number' && (
              <div className="breakdown-row">
                <div className="breakdown-info">
                  <strong>Schedule Quality Optimization Score</strong>
                  <p>
                    {score.breakdown
                      ? `Gap periods: ${score.breakdown.gap || 0} · Consecutive lectures: ${
                          score.breakdown.consecutive || 0
                        }`
                      : 'Optimization penalty measure (lower is better)'}
                  </p>
                </div>
                <span className="breakdown-badge zero">
                  Score: {score.total}
                </span>
              </div>
            )}
          </div>

          {violations.length > 0 && (
            <div className="violations-box">
              <h5>Detected Conflicts ({violations.length})</h5>
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
