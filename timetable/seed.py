"""Seed the database with four synthetic datasets.

    small       2 divisions,  5 teachers,  5 subjects,  3 classrooms + 1 lab   (hand-checkable)
    medium      4 divisions, 10 teachers, 11 subjects,  6 classrooms + 2 labs  (demo, 1 elective group)
    stress     12 divisions, 30 teachers, 31 subjects, 11 classrooms + 4 labs  (speed / scoring)
    impossible  small data with one teacher who has more lectures than available slots

    python seed.py                          # rebuild data/*.db and timetable.db (= medium)
    python seed.py --dataset small --db timetable.db

Everything is deterministic (fixed ids, fixed random seed), so re-seeding never changes ids.
To add data later, APPEND to the lists below instead of inserting in the middle.
"""
import argparse
import random
from collections import defaultdict
from pathlib import Path

try:  # imported as a package by teammates
    from . import config, db as dal, init_db as initdb
except ImportError:  # run directly: python seed.py
    import config
    import db as dal
    import init_db as initdb

S = config.slot_id


def _u(text):
    """'Mon1 Fri5' -> [slot ids]. Compact way to write a teacher's unavailable slots."""
    return sorted({S(tok[:3], int(tok[3])) for tok in text.split()})


# Row layouts used by every dataset (plain tuples, in this column order):
#   teachers    (teacher_id, name, department, max_lectures_per_day)
#   subjects    (subject_id, code, name, type, lectures_per_week, elective_group_id)
#   divisions   (division_id, name, year, strength)
#   rooms       (room_id, name, capacity, room_type)
#   assignments (division_id, subject_id, teacher_id)
#   unavailable {teacher_id: [slot_id, ...]}


# ------------------------------------------------------------------------------------- small

def build_small():
    teachers = [
        (1, "Dr. Anita Deshmukh", "Mathematics", 4),
        (2, "Prof. Rahul Kulkarni", "Computer Science", 4),
        (3, "Prof. Meera Iyer", "Electronics", 4),
        (4, "Prof. Imran Shaikh", "Humanities", 4),
        (5, "Prof. Sneha Bhosale", "Computer Science", 4),
    ]
    subjects = [
        (1, "MA201", "Discrete Mathematics", "theory", 2, None),
        (2, "CS201", "Data Structures", "theory", 2, None),
        (3, "EC201", "Digital Logic Design", "theory", 1, None),
        (4, "HS201", "Technical Communication", "theory", 1, None),
        (5, "CS202", "Data Structures Lab", "lab", 2, None),
    ]
    divisions = [(1, "SE-A", 2, 48), (2, "SE-B", 2, 45)]
    rooms = [
        (1, "R101", 60, "classroom"),
        (2, "R102", 60, "classroom"),
        (3, "R103", 50, "classroom"),
        (4, "LAB-1", 50, "lab"),
    ]
    # teacher i teaches subject i to both divisions -> 8 sessions per division, 16 in total
    assignments = [(d, s, s) for d in (1, 2) for s in (1, 2, 3, 4, 5)]
    unavailable = {1: _u("Mon1"), 2: [], 3: _u("Wed5 Wed6"), 4: _u("Fri5 Fri6"), 5: _u("Tue1 Tue2")}
    return dict(name="small", description="2 divisions, 16 sessions; small enough to draw the graph by hand",
                teachers=teachers, subjects=subjects, divisions=divisions, rooms=rooms,
                assignments=assignments, unavailable=unavailable)


# ------------------------------------------------------------------------------------ medium

def build_medium():
    teachers = [
        (1, "Dr. Anita Deshmukh", "Mathematics", 4),
        (2, "Prof. Rahul Kulkarni", "Computer Science", 4),
        (3, "Prof. Meera Iyer", "Electronics", 4),
        (4, "Dr. Sanjay Patil", "Computer Science", 4),
        (5, "Prof. Vikram Rao", "Computer Science", 4),
        (6, "Prof. Kavita Nair", "Computer Science", 4),
        (7, "Dr. Arjun Menon", "Computer Science", 3),
        (8, "Prof. Pooja Sharma", "Computer Science", 3),
        (9, "Prof. Imran Shaikh", "Humanities", 4),
        (10, "Prof. Sneha Bhosale", "Computer Science", 4),
    ]
    subjects = [
        (1, "MA201", "Discrete Mathematics", "theory", 4, None),
        (2, "CS201", "Data Structures", "theory", 4, None),
        (3, "EC201", "Digital Logic Design", "theory", 3, None),
        (4, "HS201", "Technical Communication", "theory", 2, None),      # shared by all 4 divisions
        (5, "CS202", "Data Structures Lab", "lab", 2, None),
        (6, "CS301", "Database Management Systems", "theory", 4, None),
        (7, "CS302", "Operating Systems", "theory", 4, None),
        (8, "CS303", "Computer Networks", "theory", 3, None),
        (9, "CS304", "DBMS Lab", "lab", 2, None),
        (10, "CS351", "Machine Learning", "elective", 3, 1),             # elective group 1
        (11, "CS352", "Cloud Computing", "elective", 3, 1),              # elective group 1
    ]
    divisions = [(1, "SE-A", 2, 58), (2, "SE-B", 2, 55), (3, "TE-A", 3, 52), (4, "TE-B", 3, 50)]
    rooms = [
        (1, "R101", 60, "classroom"), (2, "R102", 60, "classroom"), (3, "R103", 60, "classroom"),
        (4, "R201", 70, "classroom"), (5, "R202", 70, "classroom"), (6, "R203", 50, "classroom"),
        (7, "LAB-1", 60, "lab"), (8, "LAB-2", 60, "lab"),
    ]
    teacher_of = {1: 1, 2: 2, 3: 3, 4: 9, 5: 10, 6: 4, 7: 5, 8: 6, 9: 10, 10: 7, 11: 8}
    year_subjects = {1: [1, 2, 3, 4, 5], 2: [1, 2, 3, 4, 5], 3: [6, 7, 8, 9, 4, 10, 11], 4: [6, 7, 8, 9, 4, 10, 11]}
    assignments = [(d, s, teacher_of[s]) for d in (1, 2, 3, 4) for s in year_subjects[d]]
    unavailable = {
        1: _u("Mon1 Fri5 Fri6"),
        2: _u("Wed5 Wed6 Thu1"),
        3: _u("Tue5 Tue6 Fri1 Fri2"),
        4: _u("Mon5 Mon6 Thu5"),
        5: _u("Tue1 Wed1 Fri6"),
        6: _u("Thu5 Thu6 Mon1"),
        7: _u("Mon5 Mon6 Wed5 Wed6"),     # visiting faculty: no afternoons Mon/Wed
        8: _u("Fri3 Fri4 Fri5 Fri6"),     # half day on Friday
        9: _u("Tue1 Tue2 Thu1"),
        10: _u("Wed1 Wed2 Fri5 Fri6"),
    }
    return dict(name="medium", description="4 divisions, 72 sessions, 1 elective group, 3-4 blocked slots per teacher",
                teachers=teachers, subjects=subjects, divisions=divisions, rooms=rooms,
                assignments=assignments, unavailable=unavailable)


# ------------------------------------------------------------------------------------ stress

# year -> [(code, name, type, lectures_per_week, department, elective_group_id)]
CURRICULUM = {
    1: [("MA101", "Engineering Mathematics I", "theory", 4, "Mathematics", None),
        ("PH101", "Engineering Physics", "theory", 3, "Physics", None),
        ("ME101", "Engineering Mechanics", "theory", 3, "Physics", None),
        ("CS101", "Programming Fundamentals", "theory", 4, "Computer Science", None),
        ("EE101", "Basic Electrical Engineering", "theory", 3, "Electronics", None),
        ("HS101", "Communication Skills", "theory", 2, "Humanities", None),
        ("CS102", "Programming Lab", "lab", 2, "Computer Science", None)],
    2: [("MA201", "Discrete Mathematics", "theory", 4, "Mathematics", None),
        ("CS201", "Data Structures", "theory", 4, "Computer Science", None),
        ("EC201", "Digital Logic Design", "theory", 3, "Electronics", None),
        ("EC202", "Signals and Systems", "theory", 3, "Electronics", None),
        ("CS202", "Computer Organization", "theory", 3, "Computer Science", None),
        ("HS201", "Technical Communication", "theory", 2, "Humanities", None),
        ("CS203", "Data Structures Lab", "lab", 2, "Computer Science", None)],
    3: [("CS301", "Database Management Systems", "theory", 4, "Computer Science", None),
        ("CS302", "Operating Systems", "theory", 4, "Computer Science", None),
        ("CS303", "Computer Networks", "theory", 3, "Computer Science", None),
        ("CS304", "Software Engineering", "theory", 3, "Computer Science", None),
        ("MA301", "Probability and Statistics", "theory", 3, "Mathematics", None),
        ("CS305", "DBMS Lab", "lab", 2, "Computer Science", None),
        ("CS351", "Machine Learning", "elective", 2, "Computer Science", 1),
        ("CS352", "Cloud Computing", "elective", 2, "Computer Science", 1)],
    4: [("CS401", "Compiler Design", "theory", 3, "Computer Science", None),
        ("CS402", "Information Security", "theory", 3, "Computer Science", None),
        ("CS403", "Distributed Systems", "theory", 3, "Computer Science", None),
        ("MA401", "Operations Research", "theory", 3, "Mathematics", None),
        ("HS401", "Engineering Economics", "theory", 2, "Humanities", None),
        ("CS404", "Security Lab", "lab", 2, "Computer Science", None),
        ("CS451", "Deep Learning", "elective", 2, "Computer Science", 2),
        ("CS452", "Internet of Things", "elective", 2, "Computer Science", 2),
        ("CS453", "Blockchain Technology", "elective", 2, "Computer Science", 2)],
}

DEPT_TEACHERS = {  # order fixes the teacher ids (Mathematics 1-5, Physics 6-7, ...)
    "Mathematics": ["Dr. Anita Deshmukh", "Dr. Prakash Joshi", "Prof. Lata Mehta", "Prof. Suresh Naik", "Dr. Farah Khan"],
    "Physics": ["Dr. Ravi Shankar", "Prof. Deepa Menon"],
    "Electronics": ["Prof. Meera Iyer", "Dr. Harish Pawar", "Prof. Nilesh Gaikwad", "Prof. Swati Kelkar"],
    "Humanities": ["Prof. Imran Shaikh", "Dr. Shalini Verma", "Prof. Rohan Dsouza", "Prof. Tanvi Apte"],
    "Computer Science": ["Prof. Rahul Kulkarni", "Dr. Sanjay Patil", "Prof. Vikram Rao", "Prof. Kavita Nair",
                         "Dr. Arjun Menon", "Prof. Pooja Sharma", "Prof. Sneha Bhosale", "Dr. Manoj Kale",
                         "Prof. Aditi Phadke", "Prof. Karan Malhotra", "Dr. Priya Ramesh", "Prof. Omkar Jadhav",
                         "Prof. Nandini Rane", "Prof. Sameer Chavan", "Dr. Isha Thakur"],
}
DEPT_MAX_PER_DAY = {"Mathematics": 4, "Physics": 3, "Electronics": 4, "Humanities": 3, "Computer Science": 4}
STRESS_STRENGTHS = [62, 58, 55, 60, 56, 52, 57, 54, 50, 52, 48, 46]
TEACHER_LOAD_CAP = 14  # soft cap used while generating assignments


def _random_unavailable(rng):
    """1-3 blocks: an afternoon, a morning or a single period on some day."""
    slots = set()
    for _ in range(rng.randint(1, 3)):
        kind, day = rng.choice(["afternoon", "morning", "single"]), rng.choice(config.DAYS)
        if kind == "afternoon":
            slots |= {S(day, 5), S(day, 6)}
        elif kind == "morning":
            slots |= {S(day, 1), S(day, 2)}
        else:
            slots.add(S(day, rng.randint(1, config.PERIODS_PER_DAY)))
    return sorted(slots)


def build_stress():
    rng = random.Random(7)
    teachers, dept_of_teacher = [], {}
    for dept, names in DEPT_TEACHERS.items():
        for i, name in enumerate(names):
            tid = len(teachers) + 1
            cap = DEPT_MAX_PER_DAY[dept] + (1 if dept == "Computer Science" and i % 2 else 0)
            teachers.append((tid, name, dept, cap))
            dept_of_teacher[tid] = dept

    divisions, subjects, rooms = [], [], []
    for year, prefix in zip(sorted(CURRICULUM), ["FE", "SE", "TE", "BE"]):
        for letter in "ABC":
            did = len(divisions) + 1
            divisions.append((did, f"{prefix}-{letter}", year, STRESS_STRENGTHS[did - 1]))

    classroom_caps = [60] * 4 + [70] * 4 + [80] * 3
    rooms += [(i + 1, f"C-{(i // 4 + 1)}{i % 4 + 1:02d}", cap, "classroom") for i, cap in enumerate(classroom_caps)]
    rooms += [(12 + i, f"LAB-{i + 1}", cap, "lab") for i, cap in enumerate([70, 70, 60, 60])]

    assignments, load = [], defaultdict(int)
    for year in sorted(CURRICULUM):
        year_divs = [d[0] for d in divisions if d[2] == year]
        for code, name, typ, lps, dept, grp in CURRICULUM[year]:
            sid = len(subjects) + 1
            subjects.append((sid, code, name, typ, lps, grp))
            pool = [t[0] for t in teachers if t[2] == dept]
            used = set()
            for did in year_divs:
                # keep the same teacher for a subject across divisions while their load allows it
                tid = min(pool, key=lambda t: (0 if t in used and load[t] + lps <= TEACHER_LOAD_CAP else 1, load[t], t))
                used.add(tid)
                load[tid] += lps
                assignments.append((did, sid, tid))

    unavailable = {t[0]: _random_unavailable(rng) for t in teachers}
    return dict(name="stress", description="12 divisions, 261 sessions, 2 elective groups, random blocked slots",
                teachers=teachers, subjects=subjects, divisions=divisions, rooms=rooms,
                assignments=assignments, unavailable=unavailable)


# --------------------------------------------------------------------------------- impossible

def build_impossible():
    """Small data, but Dr. Deshmukh teaches 8 Discrete Maths lectures/week to each of two divisions
    (16 sessions) while being free only on Mon and Tue (12 slots)."""
    data = build_small()
    data["name"] = "impossible"
    data["description"] = ("Dr. Anita Deshmukh has 16 sessions but only 12 available slots "
                           "(free Mon-Tue only): cannot be scheduled")
    data["subjects"] = [(1, "MA201", "Discrete Mathematics", "theory", 8, None)] + data["subjects"][1:]
    data["teachers"] = [(1, "Dr. Anita Deshmukh", "Mathematics", 6)] + data["teachers"][1:]
    data["unavailable"] = dict(data["unavailable"])
    data["unavailable"][1] = sorted(S(day, p) for day in ("Wed", "Thu", "Fri")
                                    for p in range(1, config.PERIODS_PER_DAY + 1))
    return data


DATASETS = {"small": build_small, "medium": build_medium, "stress": build_stress, "impossible": build_impossible}


# ------------------------------------------------------------------------------------ loading

def load_dataset(conn, data):
    """Insert a dataset: base tables -> teaching_assignments -> sessions (one row per lecture)."""
    slot_ids = [r[0] for r in conn.execute("SELECT slot_id FROM timeslots ORDER BY slot_id")]
    availability = [
        (t[0], s, 0 if s in set(data["unavailable"].get(t[0], [])) else 1)
        for t in data["teachers"] for s in slot_ids
    ]
    lectures = {s[0]: s[4] for s in data["subjects"]}
    group = {s[0]: s[5] for s in data["subjects"]}
    sessions, next_id = [], 1
    for division_id, subject_id, teacher_id in sorted(data["assignments"]):
        for n in range(1, lectures[subject_id] + 1):
            sessions.append((next_id, subject_id, division_id, teacher_id, n, group[subject_id]))
            next_id += 1
    with conn:
        conn.executemany("INSERT INTO teachers (teacher_id, name, department, max_lectures_per_day) VALUES (?,?,?,?)", data["teachers"])
        conn.executemany("INSERT INTO subjects (subject_id, code, name, type, lectures_per_week, elective_group_id) VALUES (?,?,?,?,?,?)", data["subjects"])
        conn.executemany("INSERT INTO divisions (division_id, name, year, strength) VALUES (?,?,?,?)", data["divisions"])
        conn.executemany("INSERT INTO rooms (room_id, name, capacity, room_type) VALUES (?,?,?,?)", data["rooms"])
        conn.executemany("INSERT INTO teaching_assignments (division_id, subject_id, teacher_id) VALUES (?,?,?)", data["assignments"])
        conn.executemany("INSERT INTO teacher_availability (teacher_id, slot_id, is_available) VALUES (?,?,?)", availability)
        conn.executemany("INSERT INTO sessions (session_id, subject_id, division_id, teacher_id, session_no, elective_group_id) VALUES (?,?,?,?,?,?)", sessions)


# ------------------------------------------------------------------------------- sample run

def _try_schedule(sessions, avail, rooms, strength, max_day, day_of, rng):
    """One greedy attempt: most-constrained session first, spread over the week. None on dead end.
    Hard rules: teacher availability / no clash / daily limit, division no clash, room type and
    capacity, one room per session, sessions of one elective group never share a slot."""
    by_id = {s["session_id"]: s for s in sessions}
    fit = {}
    for s in sessions:
        kind = "lab" if s["subject_type"] == "lab" else "classroom"
        fit[s["session_id"]] = sorted(
            (r for r in rooms if r["room_type"] == kind and r["capacity"] >= strength[s["division_id"]]),
            key=lambda r: (r["capacity"], r["room_id"]))
    feas = {sid: set(avail[by_id[sid]["teacher_id"]]) if fit[sid] else set() for sid in by_id}
    busy_room, teacher_day = defaultdict(set), defaultdict(int)
    div_day, div_day_subject = defaultdict(int), defaultdict(int)
    todo, rows = set(by_id), []
    while todo:
        sid = min(todo, key=lambda i: (len(feas[i]), rng.random()))
        if not feas[sid]:
            return None
        s = by_id[sid]
        dv, sub, tc, grp = s["division_id"], s["subject_id"], s["teacher_id"], s["elective_group_id"]
        slot = min(feas[sid], key=lambda x: (div_day_subject[(dv, day_of[x], sub)], div_day[(dv, day_of[x])], rng.random()))
        room = next(r for r in fit[sid] if r["room_id"] not in busy_room[slot])
        rows.append({"session_id": sid, "slot_id": slot, "room_id": room["room_id"]})
        todo.discard(sid)
        busy_room[slot].add(room["room_id"])
        day = day_of[slot]
        teacher_day[(tc, day)] += 1
        div_day[(dv, day)] += 1
        div_day_subject[(dv, day, sub)] += 1
        for u in todo:
            us, f = by_id[u], feas[u]
            if slot in f:
                clash = us["teacher_id"] == tc or us["division_id"] == dv or (grp is not None and us["elective_group_id"] == grp)
                if clash or all(r["room_id"] in busy_room[slot] for r in fit[u]):
                    f.discard(slot)
            if us["teacher_id"] == tc and teacher_day[(tc, day)] >= max_day[tc]:
                f.difference_update([x for x in f if day_of[x] == day])
    return rows


def make_sample_run(conn, seed=0, attempts=300):
    """A valid timetable (list of dicts: session_id, slot_id, room_id) so Member 4 can build the
    UI on real rows. A throwaway greedy builder, not the project's real algorithm."""
    sessions, avail = dal.load_sessions(conn), dal.load_availability(conn)
    rooms = dal.load_rooms(conn)
    strength = {d["division_id"]: d["strength"] for d in dal.load_divisions(conn)}
    max_day = {t["teacher_id"]: t["max_lectures_per_day"] for t in dal.load_teachers(conn)}
    day_of = {s["slot_id"]: s["day"] for s in dal.load_timeslots(conn)}
    for attempt in range(attempts):
        rows = _try_schedule(sessions, avail, rooms, strength, max_day, day_of, random.Random(seed + attempt))
        if rows:
            return rows
    raise RuntimeError("could not build a sample timetable for this dataset")


# ----------------------------------------------------------------------------------------- CLI

def seed_database(db_path, dataset, sample_run=True):
    """Reset db_path and load one dataset. Returns a small summary dict."""
    data = DATASETS[dataset]()
    initdb.init_db(db_path, reset=True)
    conn = dal.connect(db_path)
    try:
        load_dataset(conn, data)
        run_id = None
        if sample_run and dataset not in config.EXPECTED_TO_FAIL:
            rows = make_sample_run(conn)
            run_id = dal.new_run_id(conn, status="sample")
            dal.save_timetable(conn, run_id, rows)
            dal.update_run(conn, run_id, colors_used=len({r["slot_id"] for r in rows}))
        count = lambda table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return {"dataset": dataset, "path": str(db_path), "description": data["description"],
                "divisions": count("divisions"), "teachers": count("teachers"), "subjects": count("subjects"),
                "rooms": count("rooms"), "sessions": count("sessions"), "sample_run_id": run_id}
    finally:
        conn.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dataset", choices=config.DATASET_NAMES + ["all"], default="all")
    ap.add_argument("--db", help="target file for a single dataset (default: timetable.db)")
    ap.add_argument("--no-sample-run", action="store_true", help="skip the saved sample timetable")
    args = ap.parse_args(argv)
    jobs = []
    if args.dataset == "all":
        jobs = [(n, config.DATA_DIR / f"{n}.db") for n in config.DATASET_NAMES] + [("medium", config.DEFAULT_DB)]
    else:
        jobs = [(args.dataset, Path(args.db) if args.db else config.DEFAULT_DB)]
    for name, path in jobs:
        info = seed_database(path, name, sample_run=not args.no_sample_run)
        print(f"{name:<10} -> {Path(path).name:<14} {info['divisions']:>2} divisions, {info['teachers']:>2} teachers, "
              f"{info['subjects']:>2} subjects, {info['rooms']:>2} rooms, {info['sessions']:>3} sessions"
              f"{'  (sample run #%d)' % info['sample_run_id'] if info['sample_run_id'] else ''}")


if __name__ == "__main__":
    main()
