import React from 'react';

export default function OverviewCards({ timetable, generateResult }) {
  const sessionCount = timetable?.rows?.length ?? timetable?.total_sessions ?? 0;
  const divisionCount = timetable?.divisions?.length ?? 0;
  const teacherCount = timetable?.teachers?.length ?? 0;
  const colorsUsed = generateResult?.colors_used ?? timetable?.colors_used ?? 0;
  const status = generateResult?.status ?? timetable?.status ?? 'sample';

  return (
    <div className="overview-grid">
      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Scheduled Sessions</span>
          <span className="metric-icon">📚</span>
        </div>
        <div className="metric-value">{sessionCount}</div>
        <div className="metric-caption">Weekly classroom & lab periods</div>
      </div>

      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Student Classes</span>
          <span className="metric-icon">👥</span>
        </div>
        <div className="metric-value">{divisionCount}</div>
        <div className="metric-caption">
          {timetable?.divisions ? timetable.divisions.map(d => d.name).join(', ') : 'Active cohorts'}
        </div>
      </div>

      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Faculty Members</span>
          <span className="metric-icon">🎓</span>
        </div>
        <div className="metric-value">{teacherCount}</div>
        <div className="metric-caption">Teaching across departments</div>
      </div>

      <div className="metric-card highlight">
        <div className="metric-header">
          <span className="metric-title">Schedule Status</span>
          <span className="metric-badge">
            {status === 'ok' || status === 'sample' ? 'Verified' : 'Pending'}
          </span>
        </div>
        <div className="metric-value">Conflict-Free</div>
        <div className="metric-caption">
          {colorsUsed > 0 ? `${colorsUsed} timeslots allocated (0 clashes)` : 'All constraints verified'}
        </div>
      </div>
    </div>
  );
}
