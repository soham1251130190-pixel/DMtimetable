"""Pre-flight check: can this dataset possibly be scheduled, and if not, why?

    python validate_data.py                      # check timetable.db
    python validate_data.py --db data/small.db
    python validate_data.py --all                # check small, medium, stress, impossible

Exit code 0 = PASS (with --all: every dataset behaved as expected, impossible must FAIL).
"""
import argparse
from collections import defaultdict
from pathlib import Path

try:  # imported as a package by teammates
    from . import config, db as dal
except ImportError:  # run directly: python validate_data.py
    import config
    import db as dal


def _q(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _result(name, title, problems):
    return {"name": name, "title": title, "passed": not problems, "problems": problems}


# ---------------------------------------------------------------------------------- the checks

def check_teacher_load(conn):
    """Sessions must fit in the teacher's available slots and respect max_lectures_per_day."""
    loads = {r["teacher_id"]: r["n"] for r in _q(conn, "SELECT teacher_id, COUNT(*) AS n FROM sessions GROUP BY teacher_id")}
    free_per_day = defaultdict(dict)
    for r in _q(conn, """SELECT ta.teacher_id, ts.day, COUNT(*) AS n
                         FROM teacher_availability ta JOIN timeslots ts ON ts.slot_id = ta.slot_id
                         WHERE ta.is_available = 1 GROUP BY ta.teacher_id, ts.day"""):
        free_per_day[r["teacher_id"]][r["day"]] = r["n"]
    problems = []
    for t in _q(conn, "SELECT teacher_id, name, max_lectures_per_day FROM teachers ORDER BY teacher_id"):
        n = loads.get(t["teacher_id"], 0)
        days = free_per_day[t["teacher_id"]]
        available = sum(days.values())
        per_day_limit = sum(min(t["max_lectures_per_day"], c) for c in days.values())
        if n > available:
            problems.append(f"{t['name']}: {n} sessions but only {available} available slots")
        elif n > per_day_limit:
            problems.append(f"{t['name']}: {n} sessions but a limit of {t['max_lectures_per_day']} per day "
                            f"allows only {per_day_limit} per week")
    return _result("teacher_load", "each teacher has enough available slots", problems)


def check_division_load(conn):
    """A division cannot attend more lectures than there are timeslots in the week."""
    total = _q(conn, "SELECT COUNT(*) AS n FROM timeslots")[0]["n"]
    problems = [f"{r['name']}: {r['n']} sessions but only {total} timeslots"
                for r in _q(conn, """SELECT d.name, COUNT(s.session_id) AS n FROM divisions d
                                     LEFT JOIN sessions s ON s.division_id = d.division_id
                                     GROUP BY d.division_id ORDER BY d.division_id""")
                if r["n"] > total]
    return _result("division_load", "each division's sessions fit in the week", problems)


def check_lab_rooms(conn):
    """Every lab subject that has sessions needs at least one lab room to exist."""
    has_lab_room = _q(conn, "SELECT COUNT(*) AS n FROM rooms WHERE room_type = 'lab'")[0]["n"] > 0
    problems = []
    if not has_lab_room:
        problems = [f"{r['name']} ({r['code']}): lab subject with {r['n']} sessions but there is no lab room"
                    for r in _q(conn, """SELECT sub.name, sub.code, COUNT(*) AS n FROM sessions s
                                         JOIN subjects sub ON sub.subject_id = s.subject_id
                                         WHERE sub.type = 'lab' GROUP BY sub.subject_id""")]
    return _result("lab_rooms", "every lab session has a lab room", problems)


def check_room_capacity(conn):
    """For each division, a room of the needed type must be big enough for its strength."""
    problems = []
    for d in _q(conn, "SELECT division_id, name, strength FROM divisions ORDER BY division_id"):
        needed = {r["kind"] for r in _q(conn, """
            SELECT DISTINCT CASE WHEN sub.type = 'lab' THEN 'lab' ELSE 'classroom' END AS kind
            FROM sessions s JOIN subjects sub ON sub.subject_id = s.subject_id
            WHERE s.division_id = ?""", (d["division_id"],))}
        for kind in sorted(needed):
            best = _q(conn, "SELECT MAX(capacity) AS m FROM rooms WHERE room_type = ?", (kind,))[0]["m"]
            if best is None or best < d["strength"]:
                largest = f"largest is {best}" if best is not None else f"no {kind} exists"
                problems.append(f"{d['name']} (strength {d['strength']}): no {kind} with capacity >= "
                                f"{d['strength']} ({largest})")
    return _result("room_capacity", "a room of each needed type can hold every division", problems)


def check_room_slots(conn):
    """Enough room-slots in a week for the sessions of each room type."""
    total = _q(conn, "SELECT COUNT(*) AS n FROM timeslots")[0]["n"]
    problems = []
    for kind in ("classroom", "lab"):
        sessions = _q(conn, """SELECT COUNT(*) AS n FROM sessions s JOIN subjects sub ON sub.subject_id = s.subject_id
                               WHERE (sub.type = 'lab') = (? = 'lab')""", (kind,))[0]["n"]
        rooms = _q(conn, "SELECT COUNT(*) AS n FROM rooms WHERE room_type = ?", (kind,))[0]["n"]
        if sessions > rooms * total and (kind == "classroom" or rooms > 0):
            problems.append(f"{kind}: {sessions} sessions but only {rooms} rooms x {total} slots = {rooms * total}")
    return _result("room_slots", "enough room-slots in the week for each room type", problems)


def check_elective_groups(conn):
    """Each elective group needs at least two subjects (otherwise it is not a choice)."""
    problems = [f"Elective group {r['elective_group_id']} has only {r['n']} subject ({r['codes']})"
                for r in _q(conn, """SELECT elective_group_id, COUNT(*) AS n, GROUP_CONCAT(code, ', ') AS codes
                                     FROM subjects WHERE elective_group_id IS NOT NULL
                                     GROUP BY elective_group_id HAVING n < 2 ORDER BY elective_group_id""")]
    return _result("elective_groups", "each elective group has at least two subjects", problems)


def check_session_integrity(conn):
    """Sessions reference real teachers/divisions/subjects, match teaching_assignments, carry the
    subject's elective group, and number exactly lectures_per_week per (division, subject)."""
    problems = []
    for table, col in (("teachers", "teacher_id"), ("divisions", "division_id"), ("subjects", "subject_id")):
        for r in _q(conn, f"""SELECT s.session_id, s.{col} AS ref FROM sessions s
                              LEFT JOIN {table} x ON x.{col} = s.{col} WHERE x.{col} IS NULL"""):
            problems.append(f"session {r['session_id']} refers to unknown {col} {r['ref']}")
    for r in _q(conn, """SELECT s.session_id, s.division_id, s.subject_id, s.teacher_id FROM sessions s
                         LEFT JOIN teaching_assignments ta ON ta.division_id = s.division_id
                              AND ta.subject_id = s.subject_id AND ta.teacher_id = s.teacher_id
                         WHERE ta.division_id IS NULL"""):
        problems.append(f"session {r['session_id']} (division {r['division_id']}, subject {r['subject_id']}, "
                        f"teacher {r['teacher_id']}) has no matching teaching assignment")
    for r in _q(conn, """SELECT s.session_id, sub.code FROM sessions s JOIN subjects sub ON sub.subject_id = s.subject_id
                         WHERE s.elective_group_id IS NOT sub.elective_group_id"""):
        problems.append(f"session {r['session_id']} ({r['code']}) has a different elective_group_id than its subject")
    for r in _q(conn, """SELECT d.name AS division, sub.code, sub.lectures_per_week AS expected,
                                (SELECT COUNT(*) FROM sessions s WHERE s.division_id = ta.division_id
                                   AND s.subject_id = ta.subject_id) AS actual
                         FROM teaching_assignments ta
                         JOIN divisions d ON d.division_id = ta.division_id
                         JOIN subjects sub ON sub.subject_id = ta.subject_id
                         ORDER BY ta.division_id, ta.subject_id"""):
        if r["actual"] != r["expected"]:
            problems.append(f"{r['division']} / {r['code']}: {r['actual']} sessions but lectures_per_week is {r['expected']}")
    return _result("session_integrity", "every session has a valid teacher, division and assignment", problems)


CHECKS = [check_teacher_load, check_division_load, check_lab_rooms, check_room_capacity,
          check_room_slots, check_elective_groups, check_session_integrity]


# ------------------------------------------------------------------------------------ reporting

def run_checks(conn):
    """List of result dicts: name, title, passed, problems (list of readable strings)."""
    return [check(conn) for check in CHECKS]


def format_report(results, label):
    lines = [f"Validating {label}"]
    for r in results:
        lines.append(f"  [{'PASS' if r['passed'] else 'FAIL'}] {r['name']:<18} {r['title']}")
        lines.extend(f"         - {p}" for p in r["problems"])
    failed = [r["name"] for r in results if not r["passed"]]
    lines.append(f"  => {'PASS' if not failed else 'FAIL'} "
                 f"({len(results) - len(failed)}/{len(results)} checks passed)")
    return "\n".join(lines)


def validate_file(db_path):
    conn = dal.connect(db_path)
    try:
        return run_checks(conn)
    finally:
        conn.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DEFAULT_DB))
    ap.add_argument("--all", action="store_true", help="validate every dataset in data/")
    args = ap.parse_args(argv)
    if not args.all:
        results = validate_file(args.db)
        print(format_report(results, args.db))
        return 0 if all(r["passed"] for r in results) else 1
    as_expected = True
    for name in config.DATASET_NAMES:
        results = validate_file(config.DATA_DIR / f"{name}.db")
        print(format_report(results, f"{name}.db"))
        passed = all(r["passed"] for r in results)
        expected = name not in config.EXPECTED_TO_FAIL
        if passed != expected:
            as_expected = False
            print(f"  !! unexpected: {name} should {'PASS' if expected else 'FAIL'}")
        elif not expected:
            print("  (expected to fail)")
        print()
    print("All datasets behaved as expected." if as_expected else "Some datasets did NOT behave as expected.")
    return 0 if as_expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
