-- Smart College Timetable Generator: database schema (SQLite)
-- Foreign keys are switched on per connection by db.connect(): PRAGMA foreign_keys = ON.

CREATE TABLE IF NOT EXISTS teachers (
    teacher_id           INTEGER PRIMARY KEY,
    name                 TEXT    NOT NULL,
    department           TEXT    NOT NULL,
    max_lectures_per_day INTEGER NOT NULL DEFAULT 4 CHECK (max_lectures_per_day >= 1)
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id        INTEGER PRIMARY KEY,
    code              TEXT    NOT NULL UNIQUE,
    name              TEXT    NOT NULL,
    type              TEXT    NOT NULL CHECK (type IN ('theory', 'lab', 'elective')),
    lectures_per_week INTEGER NOT NULL CHECK (lectures_per_week >= 1),
    elective_group_id INTEGER,           -- NULL unless type = 'elective'
    CHECK ((type = 'elective') = (elective_group_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS divisions (
    division_id INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    year        INTEGER NOT NULL CHECK (year >= 1),
    strength    INTEGER NOT NULL CHECK (strength > 0)
);

CREATE TABLE IF NOT EXISTS rooms (
    room_id   INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    capacity  INTEGER NOT NULL CHECK (capacity > 0),
    room_type TEXT    NOT NULL CHECK (room_type IN ('classroom', 'lab'))
);

CREATE TABLE IF NOT EXISTS timeslots (
    slot_id    INTEGER PRIMARY KEY,
    day        TEXT    NOT NULL,
    period     INTEGER NOT NULL CHECK (period >= 1),
    start_time TEXT    NOT NULL,
    end_time   TEXT    NOT NULL,
    UNIQUE (day, period)
);

-- Who teaches what to which division. Source for the sessions table.
CREATE TABLE IF NOT EXISTS teaching_assignments (
    division_id INTEGER NOT NULL REFERENCES divisions (division_id),
    subject_id  INTEGER NOT NULL REFERENCES subjects (subject_id),
    teacher_id  INTEGER NOT NULL REFERENCES teachers (teacher_id),
    PRIMARY KEY (division_id, subject_id),          -- one teacher per (division, subject)
    UNIQUE (division_id, subject_id, teacher_id)    -- lets sessions reference all three
);

-- One row per weekly lecture = one node of the conflict graph.
CREATE TABLE IF NOT EXISTS sessions (
    session_id        INTEGER PRIMARY KEY,
    subject_id        INTEGER NOT NULL REFERENCES subjects (subject_id),
    division_id       INTEGER NOT NULL REFERENCES divisions (division_id),
    teacher_id        INTEGER NOT NULL REFERENCES teachers (teacher_id),
    session_no        INTEGER NOT NULL CHECK (session_no >= 1),
    elective_group_id INTEGER,                      -- copied from subjects for convenience
    UNIQUE (division_id, subject_id, session_no),
    FOREIGN KEY (division_id, subject_id, teacher_id)
        REFERENCES teaching_assignments (division_id, subject_id, teacher_id)
);

-- One row per (teacher, slot). A missing row is treated as "not available".
CREATE TABLE IF NOT EXISTS teacher_availability (
    teacher_id   INTEGER NOT NULL REFERENCES teachers (teacher_id),
    slot_id      INTEGER NOT NULL REFERENCES timeslots (slot_id),
    is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1)),
    UNIQUE (teacher_id, slot_id)
);

CREATE TABLE IF NOT EXISTS timetable_runs (
    run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status        TEXT    NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'completed', 'failed', 'sample')),
    colors_used   INTEGER,
    penalty_score REAL
);

-- Generated output. room_id may be NULL so Stage 1 (slots only) can be saved before Stage 2.
CREATE TABLE IF NOT EXISTS timetable (
    run_id     INTEGER NOT NULL REFERENCES timetable_runs (run_id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions (session_id),
    slot_id    INTEGER NOT NULL REFERENCES timeslots (slot_id),
    room_id    INTEGER REFERENCES rooms (room_id),
    PRIMARY KEY (run_id, session_id),               -- a session is placed once per run
    UNIQUE (run_id, slot_id, room_id)               -- a room hosts one session per slot
);

CREATE INDEX IF NOT EXISTS idx_sessions_teacher  ON sessions (teacher_id);
CREATE INDEX IF NOT EXISTS idx_sessions_division ON sessions (division_id);
CREATE INDEX IF NOT EXISTS idx_timetable_run     ON timetable (run_id);
