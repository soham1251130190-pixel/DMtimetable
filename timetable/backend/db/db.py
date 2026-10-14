"""Data-access layer: nobody outside this module writes SQL.

Every function returns plain Python types (dict, list, set, int, None).
No sqlite3.Row object ever leaves this module.
"""
import sqlite3

try:  # imported as a package by teammates
    from . import config
except ImportError:  # run directly from this folder
    import config


def connect(db_path=config.DEFAULT_DB):
    """Open a connection with foreign keys ON (it is OFF by default in SQLite)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _all(conn, sql, params=()):
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


# --------------------------------------------------------------------------- loaders (contract)

def load_sessions(conn):
    """One dict per session: session_id, subject_id, subject_code, subject_type,
    division_id, teacher_id, elective_group_id."""
    return _all(conn, """
        SELECT s.session_id, s.subject_id, sub.code AS subject_code, sub.type AS subject_type,
               s.division_id, s.teacher_id, s.elective_group_id
        FROM sessions s JOIN subjects sub ON sub.subject_id = s.subject_id
        ORDER BY s.session_id""")


def load_availability(conn):
    """{teacher_id: set of available slot_ids}. Every teacher is a key, even with an empty set."""
    result = {row["teacher_id"]: set() for row in _all(conn, "SELECT teacher_id FROM teachers")}
    for row in _all(conn, "SELECT teacher_id, slot_id FROM teacher_availability WHERE is_available = 1"):
        result[row["teacher_id"]].add(row["slot_id"])
    return result


def load_timeslots(conn):
    """list of dicts: slot_id, day, period, start_time, end_time (ordered Mon P1 .. Fri P6)."""
    return _all(conn, "SELECT slot_id, day, period, start_time, end_time FROM timeslots ORDER BY slot_id")


def load_rooms(conn):
    """list of dicts: room_id, name, capacity, room_type."""
    return _all(conn, "SELECT room_id, name, capacity, room_type FROM rooms ORDER BY room_id")


# ------------------------------------------------------------------ lookup lists (for the UI / checks)

def load_divisions(conn):
    return _all(conn, "SELECT division_id, name, year, strength FROM divisions ORDER BY division_id")


def load_teachers(conn):
    return _all(conn, "SELECT teacher_id, name, department, max_lectures_per_day "
                      "FROM teachers ORDER BY teacher_id")


def load_subjects(conn):
    return _all(conn, "SELECT subject_id, code, name, type, lectures_per_week, elective_group_id "
                      "FROM subjects ORDER BY subject_id")


def list_runs(conn):
    return _all(conn, "SELECT run_id, created_at, status, colors_used, penalty_score "
                      "FROM timetable_runs ORDER BY run_id")


# ------------------------------------------------------------------------------ runs and timetables

def new_run_id(conn, status="running"):
    """Insert a new timetable_runs row and return its run_id."""
    with conn:
        cur = conn.execute("INSERT INTO timetable_runs (status) VALUES (?)", (status,))
    return cur.lastrowid


def update_run(conn, run_id, status=None, colors_used=None, penalty_score=None):
    """Fill in a run's result fields once the pipeline finishes (None = leave unchanged)."""
    with conn:
        conn.execute(
            "UPDATE timetable_runs SET status = COALESCE(?, status), "
            "colors_used = COALESCE(?, colors_used), penalty_score = COALESCE(?, penalty_score) "
            "WHERE run_id = ?",
            (status, colors_used, penalty_score, run_id),
        )


def save_timetable(conn, run_id, rows):
    """Store rows (dicts with session_id, slot_id, room_id) for a run, replacing any earlier rows
    of that run. All-or-nothing: if one row breaks a constraint nothing is saved."""
    with conn:
        conn.execute("DELETE FROM timetable WHERE run_id = ?", (run_id,))
        conn.executemany(
            "INSERT INTO timetable (run_id, session_id, slot_id, room_id) VALUES (?, ?, ?, ?)",
            [(run_id, r["session_id"], r["slot_id"], r.get("room_id")) for r in rows],
        )


def get_timetable(conn, run_id, division_id=None, teacher_id=None):
    """Rows of a run joined with names, day, period and room, ordered by slot.

    Each dict: run_id, session_id, session_no, subject_id, subject_code, subject_name,
    subject_type, division_id, division_name, teacher_id, teacher_name, slot_id, day, period,
    start_time, end_time, room_id, room_name.  Optional filters: division_id, teacher_id.
    """
    sql = """
        SELECT t.run_id, t.session_id, s.session_no,
               s.subject_id, sub.code AS subject_code, sub.name AS subject_name, sub.type AS subject_type,
               s.division_id, d.name AS division_name,
               s.teacher_id, te.name AS teacher_name,
               t.slot_id, ts.day, ts.period, ts.start_time, ts.end_time,
               t.room_id, r.name AS room_name
        FROM timetable t
        JOIN sessions  s   ON s.session_id  = t.session_id
        JOIN subjects  sub ON sub.subject_id = s.subject_id
        JOIN divisions d   ON d.division_id = s.division_id
        JOIN teachers  te  ON te.teacher_id = s.teacher_id
        JOIN timeslots ts  ON ts.slot_id    = t.slot_id
        LEFT JOIN rooms r  ON r.room_id     = t.room_id
        WHERE t.run_id = ?"""
    params = [run_id]
    if division_id is not None:
        sql += " AND s.division_id = ?"
        params.append(division_id)
    if teacher_id is not None:
        sql += " AND s.teacher_id = ?"
        params.append(teacher_id)
    sql += " ORDER BY t.slot_id, d.name, t.session_id"
    return _all(conn, sql, params)
