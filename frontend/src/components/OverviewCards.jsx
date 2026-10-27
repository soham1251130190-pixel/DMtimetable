import React from 'react';

export default function OverviewCards({ timetable, generateResult }) {
  const allRows = timetable?.rows || [];
  const sessionCount = timetable?.total_sessions ?? allRows.length ?? 0;
  const divisions = timetable?.divisions || [];
  const teachers = timetable?.teachers || [];
  const rooms = timetable?.rooms || [];
  const violations = timetable?.violations || generateResult?.violations || [];
  const colorsUsed = timetable?.colors_used || generateResult?.colors_used || 0;
  const status = timetable?.status || generateResult?.status;

  // Real room utilization calculation
  const totalRooms = rooms.length;
  const activeRooms = new Set(allRows.map((r) => r.room_id).filter(Boolean)).size;
  const roomUtilPercent = totalRooms > 0 ? Math.round((activeRooms / totalRooms) * 100) : 0;

  const isGenerated = sessionCount > 0 && status !== 'empty';
  const hasViolations = violations.length > 0;

  let statusBadgeText = 'Draft / Not Generated';
  let statusBadgeClass = 'pending';
  let statusDetail = 'Click "Generate Timetable" to start';

  if (isGenerated) {
    if (!hasViolations) {
      statusBadgeText = 'Verified & Approved';
      statusBadgeClass = 'verified';
      statusDetail = `${colorsUsed > 0 ? `${colorsUsed} periods scheduled` : 'Complete'} · 0 Clashes`;
    } else {
      statusBadgeText = 'Needs Attention';
      statusBadgeClass = 'warning';
      statusDetail = `${violations.length} constraint violation(s) detected`;
    }
  }

  return (
    <div className="overview-grid">
      {/* 1. Scheduled Sessions */}
      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Scheduled Sessions</span>
          <span className="metric-icon">📚</span>
        </div>
        <div className="metric-value">{sessionCount}</div>
        <div className="metric-caption">
          {sessionCount > 0
            ? 'Weekly theory lectures & laboratory periods'
            : 'No sessions scheduled yet'}
        </div>
      </div>

      {/* 2. Student Classes / Divisions */}
      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Student Classes</span>
          <span className="metric-icon">👥</span>
        </div>
        <div className="metric-value">{divisions.length}</div>
        <div className="metric-caption">
          {divisions.length > 0
            ? divisions.map((d) => d.name).join(', ')
            : 'Registered class cohorts'}
        </div>
      </div>

      {/* 3. Faculty Members */}
      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Teaching Faculty</span>
          <span className="metric-icon">🎓</span>
        </div>
        <div className="metric-value">{teachers.length}</div>
        <div className="metric-caption">Faculty members with assigned workloads</div>
      </div>

      {/* 4. Room Allocation & Utilization */}
      <div className="metric-card">
        <div className="metric-header">
          <span className="metric-title">Facility Utilization</span>
          <span className="metric-icon">🏛️</span>
        </div>
        <div className="metric-value">{totalRooms > 0 ? `${roomUtilPercent}%` : '0%'}</div>
        <div className="metric-caption">
          {totalRooms > 0
            ? `${activeRooms} of ${totalRooms} rooms actively assigned`
            : 'Classrooms & laboratories'}
        </div>
      </div>

      {/* 5. Timetable Generation Outcome */}
      <div className="metric-card highlight">
        <div className="metric-header">
          <span className="metric-title">Schedule Status</span>
          <span className={`metric-badge ${statusBadgeClass}`}>{statusBadgeText}</span>
        </div>
        <div className="metric-value">
          {!isGenerated
            ? 'Awaiting Run'
            : !hasViolations
            ? '0 Conflicts'
            : `${violations.length} Conflicts`}
        </div>
        <div className="metric-caption">{statusDetail}</div>
      </div>
    </div>
  );
}
