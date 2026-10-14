"""Tests for Member 1's data layer (the Testing Checklist from the task document)."""
import sqlite3
from collections import defaultdict

import pytest

from db import config, db as dal, init_db as initdb, seed, validate_data

ALL = config.DATASET_NAMES
FEASIBLE = [n for n in ALL if n not in config.EXPECTED_TO_FAIL]


@pytest.fixture(scope="module")
def dbs(tmp_path_factory):
    """Every dataset seeded once into a temp folder: {name: path}."""
    folder = tmp_path_factory.mktemp("datasets")
    paths = {}
    for name in ALL:
        paths[name] = folder / f"{name}.db"
        seed.seed_database(paths[name], name)
    return paths


@pytest.fixture
def conn(tmp_path):
    seed.seed_database(tmp_path / "small.db", "small")
    c = dal.connect(tmp_path / "small.db")
    yield c
    c.close()


def dump_without_runs(path):
    c = dal.connect(path)
    try:
        return {t: c.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall()
                for t in ("teachers", "subjects", "divisions", "rooms", "timeslots",
                          "teaching_assignments", "sessions", "teacher_availability")}
    finally:
        c.close()


# ------------------------------------------------------------------ init_db

def test_reset_twice_gives_identical_empty_database(tmp_path):
    path = tmp_path / "t.db"
    dumps = []
    for _ in range(2):
        initdb.init_db(path, reset=True)
        c = sqlite3.connect(path)
        dumps.append(list(c.iterdump()))
        c.close()
    assert dumps[0] == dumps[1]
    c = dal.connect(path)
    assert c.execute("SELECT COUNT(*) FROM timeslots").fetchone()[0] == 30
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    assert len(tables) == 10
    assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_init_without_reset_keeps_data(tmp_path):
    seed.seed_database(tmp_path / "a.db", "small")
    initdb.init_db(tmp_path / "a.db")  # no reset: must be harmless
    c = dal.connect(tmp_path / "a.db")
    assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 16


def test_foreign_keys_are_on(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# --------------------------------------------------------- constraints reject bad rows

@pytest.mark.parametrize("sql", [
    "INSERT INTO rooms (room_id, name, capacity, room_type) VALUES (99, 'X', 40, 'gym')",           # bad room_type
    "INSERT INTO rooms (room_id, name, capacity, room_type) VALUES (99, 'X', 0, 'classroom')",      # capacity 0
    "INSERT INTO subjects (subject_id, code, name, type, lectures_per_week) VALUES (99, 'Z', 'Z', 'seminar', 1)",
    "INSERT INTO subjects (subject_id, code, name, type, lectures_per_week) VALUES (99, 'Z', 'Z', 'elective', 1)",  # elective w/o group
    "INSERT INTO subjects (subject_id, code, name, type, lectures_per_week, elective_group_id) VALUES (99, 'Z', 'Z', 'theory', 1, 5)",
    "INSERT INTO subjects (subject_id, code, name, type, lectures_per_week) VALUES (99, 'MA201', 'dup code', 'theory', 1)",
    "INSERT INTO timeslots (slot_id, day, period, start_time, end_time) VALUES (99, 'Mon', 1, '09:00', '10:00')",   # duplicate slot
    "INSERT INTO teacher_availability (teacher_id, slot_id, is_available) VALUES (1, 1, 1)",       # duplicate availability
    "INSERT INTO teacher_availability (teacher_id, slot_id, is_available) VALUES (1, 2, 5)",       # bad flag (and duplicate)
    "INSERT INTO teaching_assignments (division_id, subject_id, teacher_id) VALUES (1, 1, 999)",   # unknown teacher
    "INSERT INTO sessions (session_id, subject_id, division_id, teacher_id, session_no) VALUES (999, 1, 1, 999, 9)",  # unknown teacher
    "INSERT INTO sessions (session_id, subject_id, division_id, teacher_id, session_no) VALUES (999, 1, 1, 2, 9)",    # teacher != assignment
    "INSERT INTO sessions (session_id, subject_id, division_id, teacher_id, session_no) VALUES (999, 1, 1, 1, 1)",    # duplicate session_no
    "INSERT INTO divisions (division_id, name, year, strength) VALUES (99, 'Q', 1, -5)",
    "INSERT INTO timetable_runs (status) VALUES ('done')",
])
def test_database_rejects_bad_row(conn, sql):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql)


def test_timetable_rejects_double_booked_room_and_unknown_ids(conn):
    run = dal.new_run_id(conn)
    with pytest.raises(sqlite3.IntegrityError):  # two sessions in the same room and slot
        dal.save_timetable(conn, run, [{"session_id": 1, "slot_id": 1, "room_id": 1},
                                       {"session_id": 2, "slot_id": 1, "room_id": 1}])
    with pytest.raises(sqlite3.IntegrityError):  # unknown slot
        dal.save_timetable(conn, run, [{"session_id": 1, "slot_id": 999, "room_id": 1}])
    assert dal.get_timetable(conn, run) == []    # nothing half-saved


# ------------------------------------------------------------------- datasets

@pytest.mark.parametrize("name", ALL)
def test_session_count_equals_sum_of_lectures_per_week(dbs, name):
    c = dal.connect(dbs[name])
    expected = c.execute("""SELECT SUM(sub.lectures_per_week) FROM teaching_assignments ta
                            JOIN subjects sub ON sub.subject_id = ta.subject_id""").fetchone()[0]
    assert len(dal.load_sessions(c)) == expected
    assert c.execute("SELECT COUNT(*) FROM timeslots").fetchone()[0] == 30


@pytest.mark.parametrize("name,shape", [
    ("small", dict(divisions=2, teachers=5, subjects=5, classrooms=3, labs=1)),
    ("medium", dict(divisions=4, teachers=10, subjects=11, classrooms=6, labs=2)),
    ("stress", dict(divisions=12, teachers=30, subjects=31, classrooms=11, labs=4)),
])
def test_dataset_shapes_match_the_spec(dbs, name, shape):
    c = dal.connect(dbs[name])
    rooms = dal.load_rooms(c)
    assert len(dal.load_divisions(c)) == shape["divisions"]
    assert len(dal.load_teachers(c)) == shape["teachers"]
    assert len(dal.load_subjects(c)) == shape["subjects"]
    assert sum(r["room_type"] == "classroom" for r in rooms) == shape["classrooms"]
    assert sum(r["room_type"] == "lab" for r in rooms) == shape["labs"]


def test_medium_has_one_elective_group_and_blocked_slots(dbs):
    c = dal.connect(dbs["medium"])
    groups = {s["elective_group_id"] for s in dal.load_subjects(c) if s["elective_group_id"]}
    assert groups == {1}
    for tid, free in dal.load_availability(c).items():
        assert 26 <= len(free) < 30, f"teacher {tid} should have a few blocked slots"


def test_seeding_is_deterministic(tmp_path):
    for name in ("medium", "stress"):
        seed.seed_database(tmp_path / "a.db", name)
        first = dump_without_runs(tmp_path / "a.db")
        seed.seed_database(tmp_path / "b.db", name)
        assert first == dump_without_runs(tmp_path / "b.db")


# --------------------------------------------------------------- db.py contract

def test_loaders_return_plain_python_types(conn):
    sessions = dal.load_sessions(conn)
    assert type(sessions) is list and type(sessions[0]) is dict
    assert set(sessions[0]) == {"session_id", "subject_id", "subject_code", "subject_type",
                                "division_id", "teacher_id", "elective_group_id"}
    avail = dal.load_availability(conn)
    assert type(avail) is dict and all(type(v) is set for v in avail.values())
    assert set(avail) == {1, 2, 3, 4, 5}
    assert 1 not in avail[1] and 2 in avail[1]       # Dr. Deshmukh is blocked Mon P1 only
    for rows in (dal.load_timeslots(conn), dal.load_rooms(conn), dal.load_divisions(conn),
                 dal.load_teachers(conn), dal.load_subjects(conn)):
        assert type(rows) is list and all(type(r) is dict for r in rows)
    assert [s["slot_id"] for s in dal.load_timeslots(conn)] == list(range(1, 31))


def test_save_then_get_roundtrip(conn):
    rows = [{"session_id": 1, "slot_id": 1, "room_id": 1},
            {"session_id": 2, "slot_id": 2, "room_id": 1},
            {"session_id": 9, "slot_id": 2, "room_id": 2},
            {"session_id": 3, "slot_id": 30, "room_id": None}]  # stage-1 style row without a room
    run = dal.new_run_id(conn)
    dal.save_timetable(conn, run, rows)
    got = dal.get_timetable(conn, run)
    assert sorted((g["session_id"], g["slot_id"], g["room_id"]) for g in got) == \
           sorted((r["session_id"], r["slot_id"], r["room_id"]) for r in rows)
    first = got[0]
    assert {"division_name", "teacher_name", "subject_code", "day", "period", "room_name"} <= set(first)
    assert (first["day"], first["period"], first["room_name"]) == ("Mon", 1, "R101")
    assert all(type(g) is dict for g in got)
    # saving again replaces the run's rows rather than duplicating them
    dal.save_timetable(conn, run, rows[:2])
    assert len(dal.get_timetable(conn, run)) == 2


def test_get_timetable_filters(dbs):
    c = dal.connect(dbs["medium"])
    run = dal.list_runs(c)[0]["run_id"]
    everything = dal.get_timetable(c, run)
    assert len(everything) == 72
    by_div = dal.get_timetable(c, run, division_id=3)
    assert by_div and {r["division_id"] for r in by_div} == {3}
    by_teacher = dal.get_timetable(c, run, teacher_id=9)
    assert len(by_teacher) == 8 and {r["teacher_id"] for r in by_teacher} == {9}
    both = dal.get_timetable(c, run, division_id=3, teacher_id=9)
    assert len(both) == 2


def test_update_run(conn):
    run = dal.new_run_id(conn)
    dal.update_run(conn, run, status="completed", colors_used=12, penalty_score=3.5)
    assert dal.list_runs(conn)[-1] == {"run_id": run, "created_at": dal.list_runs(conn)[-1]["created_at"],
                                       "status": "completed", "colors_used": 12, "penalty_score": 3.5}


# ----------------------------------------------------------------- sample runs

def hard_violations(c, run_id):
    """Independent re-check of every hard constraint on a saved run."""
    rows = dal.get_timetable(c, run_id)
    sessions = {s["session_id"]: s for s in dal.load_sessions(c)}
    avail, rooms = dal.load_availability(c), {r["room_id"]: r for r in dal.load_rooms(c)}
    strength = {d["division_id"]: d["strength"] for d in dal.load_divisions(c)}
    max_day = {t["teacher_id"]: t["max_lectures_per_day"] for t in dal.load_teachers(c)}
    bad, seen = [], defaultdict(list)
    if {r["session_id"] for r in rows} != set(sessions):
        bad.append("not every session is placed exactly once")
    per_day = defaultdict(int)
    for r in rows:
        s, room = sessions[r["session_id"]], rooms[r["room_id"]]
        seen[("teacher", s["teacher_id"], r["slot_id"])].append(r)
        seen[("division", s["division_id"], r["slot_id"])].append(r)
        seen[("room", r["room_id"], r["slot_id"])].append(r)
        if s["elective_group_id"] is not None:
            seen[("group", s["elective_group_id"], r["slot_id"])].append(r)
        if r["slot_id"] not in avail[s["teacher_id"]]:
            bad.append(f"session {s['session_id']} placed when teacher unavailable")
        if room["capacity"] < strength[s["division_id"]]:
            bad.append(f"session {s['session_id']} room too small")
        if (s["subject_type"] == "lab") != (room["room_type"] == "lab"):
            bad.append(f"session {s['session_id']} wrong room type")
        per_day[(s["teacher_id"], r["day"])] += 1
    bad += [f"clash {k}" for k, v in seen.items() if len(v) > 1]
    bad += [f"teacher {t} has too many lectures on {d}" for (t, d), n in per_day.items() if n > max_day[t]]
    return bad


@pytest.mark.parametrize("name", FEASIBLE)
def test_sample_run_is_valid_and_complete(dbs, name):
    c = dal.connect(dbs[name])
    runs = dal.list_runs(c)
    assert len(runs) == 1 and runs[0]["status"] == "sample"
    assert hard_violations(c, runs[0]["run_id"]) == []   # proves these datasets really are schedulable


def test_impossible_has_no_sample_run(dbs):
    assert dal.list_runs(dal.connect(dbs["impossible"])) == []


# ------------------------------------------------------------------- validator

@pytest.mark.parametrize("name", FEASIBLE)
def test_validator_passes_feasible_datasets(dbs, name):
    results = validate_data.validate_file(dbs[name])
    assert [r["name"] for r in results if not r["passed"]] == []


def test_validator_fails_impossible_for_the_right_reason(dbs):
    results = validate_data.validate_file(dbs["impossible"])
    failed = [r for r in results if not r["passed"]]
    assert [r["name"] for r in failed] == ["teacher_load"]
    assert failed[0]["problems"] == ["Dr. Anita Deshmukh: 16 sessions but only 12 available slots"]


def failed_checks(c):
    return {r["name"] for r in validate_data.run_checks(c) if not r["passed"]}


def test_validator_catches_each_kind_of_problem(tmp_path):
    def fresh(name="small"):
        p = tmp_path / f"{name}-{len(list(tmp_path.iterdir()))}.db"
        seed.seed_database(p, name, sample_run=False)
        return dal.connect(p)

    c = fresh("medium")                                             # per-day limit too low (8 sessions, 1/day)
    c.execute("UPDATE teachers SET max_lectures_per_day = 1 WHERE teacher_id = 9")
    assert failed_checks(c) == {"teacher_load"}

    c = fresh()                                                     # no lab room at all
    c.execute("DELETE FROM rooms WHERE room_type = 'lab'")
    assert failed_checks(c) == {"lab_rooms", "room_capacity"}

    c = fresh()                                                     # division too big for any classroom
    c.execute("UPDATE divisions SET strength = 200 WHERE division_id = 1")
    assert "room_capacity" in failed_checks(c)

    c = fresh()                                                     # more sessions than the week can hold
    c.executemany("INSERT INTO sessions (session_id, subject_id, division_id, teacher_id, session_no) VALUES (?,?,?,?,?)",
                  [(100 + i, 1, 1, 1, 10 + i) for i in range(90)])
    assert {"division_load", "room_slots"} <= failed_checks(c)

    c = fresh("medium")                                             # elective group with a single subject
    c.execute("UPDATE subjects SET elective_group_id = 2 WHERE code = 'CS352'")
    assert "elective_groups" in failed_checks(c)

    c = fresh()                                                     # orphan session (FKs off to sneak it in)
    c.execute("PRAGMA foreign_keys = OFF")
    c.execute("INSERT INTO sessions (session_id, subject_id, division_id, teacher_id, session_no) VALUES (500, 1, 1, 77, 5)")
    assert "session_integrity" in failed_checks(c)

    c = fresh()                                                     # a missing session
    c.execute("DELETE FROM sessions WHERE session_id = 1")
    assert failed_checks(c) == {"session_integrity"}
