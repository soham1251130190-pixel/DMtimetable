import React, { useState, useMemo } from 'react';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const PERIODS = [
  { period: 1, time: '09:00 - 10:00' },
  { period: 2, time: '10:00 - 11:00' },
  { period: 3, time: '11:15 - 12:15' },
  { period: 4, time: '12:15 - 13:15' },
  { period: 5, time: '14:00 - 15:00' },
  { period: 6, time: '15:00 - 16:00' },
];

export default function TimetableTable({ timetable, loading, error }) {
  const [selectedDivision, setSelectedDivision] = useState('ALL');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'

  const divisions = timetable?.divisions || [];
  const allRows = timetable?.rows || [];

  // Filter rows based on selected division
  const filteredRows = useMemo(() => {
    if (selectedDivision === 'ALL') {
      return allRows;
    }
    const divId = Number(selectedDivision);
    return allRows.filter((r) => r.division_id === divId);
  }, [allRows, selectedDivision]);

  // Map for grid lookup: day -> period -> list of sessions
  const gridMap = useMemo(() => {
    const map = {};
    for (const day of DAYS) {
      map[day] = {};
      for (let p = 1; p <= 6; p++) {
        map[day][p] = [];
      }
    }
    for (const row of filteredRows) {
      if (map[row.day] && map[row.day][row.period]) {
        map[row.day][row.period].push(row);
      }
    }
    return map;
  }, [filteredRows]);

  if (loading) {
    return (
      <div className="table-container-empty">
        <div className="loading-spinner"></div>
        <p>Loading weekly timetable from database...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="table-container-empty error">
        <p className="error-title">Schedule Temporarily Unavailable</p>
        <p className="error-desc">{error}</p>
      </div>
    );
  }

  if (!timetable || allRows.length === 0 || timetable.status === 'empty') {
    return (
      <div className="table-container-empty">
        <div className="empty-calendar-icon">📅</div>
        <h4 className="empty-title">No Timetable Generated Yet</h4>
        <p className="empty-desc">
          Select an academic dataset from the control bar above and click{' '}
          <strong>Generate Timetable</strong> to create a conflict-free weekly schedule.
        </p>
      </div>
    );
  }

  return (
    <div className="timetable-section">
      <div className="timetable-toolbar">
        <div className="toolbar-left">
          <h3 className="section-title">Weekly Academic Schedule</h3>
          <p className="section-subtitle">
            Showing verified lecture periods and laboratory allocations across 5 working days.
          </p>
        </div>

        <div className="toolbar-controls">
          <div className="filter-group">
            <label htmlFor="division-select" className="filter-label">Filter by Class:</label>
            <select
              id="division-select"
              value={selectedDivision}
              onChange={(e) => setSelectedDivision(e.target.value)}
              className="faculty-select"
            >
              <option value="ALL">All Classes ({allRows.length} sessions)</option>
              {divisions.map((div) => {
                const count = allRows.filter((r) => r.division_id === div.division_id).length;
                return (
                  <option key={div.division_id} value={div.division_id}>
                    {div.name} ({count} sessions)
                  </option>
                );
              })}
            </select>
          </div>

          <div className="view-toggle">
            <button
              type="button"
              className={`toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              Grid View
            </button>
            <button
              type="button"
              className={`toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
            >
              List View
            </button>
          </div>
        </div>
      </div>

      {filteredRows.length === 0 ? (
        <div className="table-container-empty">
          <p>No scheduled sessions found for the selected filter.</p>
        </div>
      ) : viewMode === 'grid' ? (
        /* ================= 5-Day Grid Matrix ================= */
        <div className="grid-scroll-wrapper">
          <table className="schedule-grid">
            <thead>
              <tr>
                <th className="grid-corner-th">Period & Time</th>
                {DAYS.map((day) => (
                  <th key={day} className="grid-day-th">
                    {day === 'Mon' && 'Monday'}
                    {day === 'Tue' && 'Tuesday'}
                    {day === 'Wed' && 'Wednesday'}
                    {day === 'Thu' && 'Thursday'}
                    {day === 'Fri' && 'Friday'}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PERIODS.map(({ period, time }) => (
                <tr key={period}>
                  <td className="grid-time-td">
                    <span className="period-badge">P{period}</span>
                    <span className="time-subtext">{time}</span>
                  </td>
                  {DAYS.map((day) => {
                    const cellSessions = gridMap[day]?.[period] || [];
                    return (
                      <td key={day} className="grid-slot-td">
                        {cellSessions.length === 0 ? (
                          <div className="slot-empty">—</div>
                        ) : (
                          cellSessions.map((s) => (
                            <div
                              key={s.session_id}
                              className={`slot-card ${s.subject_type === 'lab' ? 'slot-lab' : 'slot-theory'}`}
                            >
                              <div className="slot-card-top">
                                <strong className="slot-code">{s.subject_code}</strong>
                                <span className={`slot-pill ${s.subject_type === 'lab' ? 'pill-lab' : 'pill-theory'}`}>
                                  {s.subject_type === 'lab' ? 'Lab' : 'Theory'}
                                </span>
                              </div>
                              <div className="slot-name" title={s.subject_name}>
                                {s.subject_name}
                              </div>
                              <div className="slot-meta">
                                <span className="slot-div-tag">{s.division_name}</span>
                                <span className="slot-room-tag">{s.room_name}</span>
                              </div>
                              <div className="slot-faculty" title={s.teacher_name}>
                                {s.teacher_name}
                              </div>
                            </div>
                          ))
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* ================= Detailed List View ================= */
        <div className="table-responsive">
          <table className="faculty-data-table">
            <thead>
              <tr>
                <th>Day & Period</th>
                <th>Time</th>
                <th>Course</th>
                <th>Type</th>
                <th>Class</th>
                <th>Faculty Member</th>
                <th>Room / Facility</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.session_id}>
                  <td>
                    <span className="day-badge">{row.day}</span> Period {row.period}
                  </td>
                  <td className="time-cell">
                    {row.start_time} - {row.end_time}
                  </td>
                  <td>
                    <strong>{row.subject_code}</strong>
                    <div className="subtext">{row.subject_name}</div>
                  </td>
                  <td>
                    <span className={`badge ${row.subject_type === 'lab' ? 'badge-lab' : 'badge-theory'}`}>
                      {row.subject_type === 'lab' ? 'Practical Lab' : 'Theory Lecture'}
                    </span>
                  </td>
                  <td>
                    <span className="class-pill">{row.division_name}</span>
                  </td>
                  <td>{row.teacher_name}</td>
                  <td>
                    <span className="room-pill">{row.room_name}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
