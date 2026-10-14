"""Create timetable.db from schema.sql. Safe to run repeatedly.

    python init_db.py            # create missing tables / timeslots, keep existing data
    python init_db.py --reset    # drop everything and recreate an empty database
"""
import argparse
from pathlib import Path

try:  # imported as a package by teammates
    from . import config, db as dal
except ImportError:  # run directly: python init_db.py
    import config
    import db as dal

# children before parents, so drops never violate a foreign key
DROP_ORDER = [
    "timetable", "timetable_runs", "teacher_availability", "sessions",
    "teaching_assignments", "timeslots", "rooms", "divisions", "subjects", "teachers",
]


def timeslot_rows():
    """(slot_id, day, period, start, end) for every slot in config."""
    return [
        (config.slot_id(d, p), day, p, start, end)
        for d, day in enumerate(config.DAYS)
        for p, start, end in config.PERIODS
    ]


def init_db(db_path=config.DEFAULT_DB, reset=False):
    """Create the schema and the timeslots rows. Returns the database path."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = dal.connect(db_path)
    try:
        if reset:
            for table in DROP_ORDER:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.executescript(config.SCHEMA_FILE.read_text())
        conn.executemany(
            "INSERT OR IGNORE INTO timeslots (slot_id, day, period, start_time, end_time) "
            "VALUES (?, ?, ?, ?, ?)",
            timeslot_rows(),
        )
        conn.commit()
    finally:
        conn.close()
    return Path(db_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DEFAULT_DB), help="database file (default: timetable.db)")
    ap.add_argument("--reset", action="store_true", help="drop and recreate all tables")
    args = ap.parse_args(argv)
    path = init_db(args.db, reset=args.reset)
    print(f"{'Reset' if args.reset else 'Initialised'} {path} ({config.NUM_SLOTS} timeslots)")


if __name__ == "__main__":
    main()
