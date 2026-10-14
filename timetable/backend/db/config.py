"""Single place for the numbers every module shares (Task 2: "keep the numbers in one config")."""
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
DATA_DIR = DB_DIR / "data"            # small.db, medium.db, stress.db, impossible.db
DEFAULT_DB = DB_DIR / "timetable.db"  # the shared sample database (medium dataset)
SCHEMA_FILE = DB_DIR / "schema.sql"

# Week layout: 5 days x 6 periods = 30 timeslots.
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
PERIODS = [  # (period number, start, end)
    (1, "09:00", "10:00"),
    (2, "10:00", "11:00"),
    (3, "11:15", "12:15"),
    (4, "12:15", "13:15"),
    (5, "14:00", "15:00"),
    (6, "15:00", "16:00"),
]
PERIODS_PER_DAY = len(PERIODS)
NUM_SLOTS = len(DAYS) * PERIODS_PER_DAY

DATASET_NAMES = ["small", "medium", "stress", "impossible"]
EXPECTED_TO_FAIL = {"impossible"}  # validate_data.py --all treats these as "should FAIL"


def slot_id(day, period):
    """slot_id for a day (name like 'Mon' or 0-based index) and a 1-based period.

    Slots are numbered day-major: Mon P1 = 1, Mon P6 = 6, Tue P1 = 7, ... Fri P6 = 30.
    """
    day_index = DAYS.index(day) if isinstance(day, str) else day
    if not 0 <= day_index < len(DAYS) or not 1 <= period <= PERIODS_PER_DAY:
        raise ValueError(f"bad slot: day={day!r} period={period!r}")
    return day_index * PERIODS_PER_DAY + period
