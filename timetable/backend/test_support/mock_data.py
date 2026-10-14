"""Test fixtures and mock datasets for Member 3 tests.

TEST ONLY - MOCK TEST FIXTURES
Contains:
- Datasets A through H (Room CSP unit test suites)
- Small Dataset (2 divisions integration test)
- Medium Dataset (4 divisions, 10 teachers, 8 rooms integration test)
- Impossible Dataset (overconstrained room capacity failure test)
"""

from typing import Any, Dict, List, Set, Tuple

# ==============================================================================
# DATASETS A-H: ROOM CSP UNIT TEST DATASETS
# ==============================================================================

# Dataset A: 3 sessions, 3 suitable rooms -> assignment succeeds
DATASET_A_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 3, "subject_id": 103, "division_id": 3, "teacher_id": 12, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
]
DATASET_A_ROOMS = [
    {"room_id": 101, "name": "Room 101", "capacity": 50, "room_type": "classroom"},
    {"room_id": 102, "name": "Room 102", "capacity": 50, "room_type": "classroom"},
    {"room_id": 103, "name": "Room 103", "capacity": 50, "room_type": "classroom"},
]
DATASET_A_SLOT_MAP = {1: 1, 2: 1, 3: 1}


# Dataset B: 3 sessions in same slot, 2 suitable rooms -> assignment fails
DATASET_B_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 3, "subject_id": 103, "division_id": 3, "teacher_id": 12, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
]
DATASET_B_ROOMS = [
    {"room_id": 101, "name": "Room 101", "capacity": 50, "room_type": "classroom"},
    {"room_id": 102, "name": "Room 102", "capacity": 50, "room_type": "classroom"},
]
DATASET_B_SLOT_MAP = {1: 1, 2: 1, 3: 1}


# Dataset C: theory + lab sessions, classroom + lab rooms -> verify correct room types
DATASET_C_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "lab", "elective_group_id": None, "division_strength": 30},
]
DATASET_C_ROOMS = [
    {"room_id": 201, "name": "Classroom 201", "capacity": 50, "room_type": "classroom"},
    {"room_id": 202, "name": "Computer Lab 1", "capacity": 35, "room_type": "lab"},
]
DATASET_C_SLOT_MAP = {1: 1, 2: 1}


# Dataset D: rooms with different capacities -> verify capacity filtering
DATASET_D_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 60},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 30},
]
DATASET_D_ROOMS = [
    {"room_id": 301, "name": "Small Room", "capacity": 35, "room_type": "classroom"},
    {"room_id": 302, "name": "Large Room", "capacity": 65, "room_type": "classroom"},
]
DATASET_D_SLOT_MAP = {1: 1, 2: 1}


# Dataset E: multiple sessions in same slot -> verify no room collision
DATASET_E_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 3, "subject_id": 103, "division_id": 3, "teacher_id": 12, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 4, "subject_id": 104, "division_id": 4, "teacher_id": 13, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
]
DATASET_E_ROOMS = [
    {"room_id": 401, "name": "Room 401", "capacity": 50, "room_type": "classroom"},
    {"room_id": 402, "name": "Room 402", "capacity": 50, "room_type": "classroom"},
    {"room_id": 403, "name": "Room 403", "capacity": 50, "room_type": "classroom"},
    {"room_id": 404, "name": "Room 404", "capacity": 50, "room_type": "classroom"},
]
DATASET_E_SLOT_MAP = {1: 1, 2: 1, 3: 1, 4: 1}


# Dataset F: sessions in different slots -> same room may be reused
DATASET_F_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 40},
]
DATASET_F_ROOMS = [
    {"room_id": 501, "name": "Single Room", "capacity": 50, "room_type": "classroom"},
]
DATASET_F_SLOT_MAP = {1: 1, 2: 2}  # Different slots


# Dataset G: one session with no suitable room -> clear failure
DATASET_G_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "lab", "elective_group_id": None, "division_strength": 40},
]
DATASET_G_ROOMS = [
    {"room_id": 601, "name": "Classroom Only", "capacity": 50, "room_type": "classroom"},
]
DATASET_G_SLOT_MAP = {1: 1}


# Dataset H: domains designed so MRV provides an advantage
# Session 1 requires large room (only room 701 fits, domain size 1)
# Session 2 and Session 3 can fit in room 701, 702, 703 (domain size 3)
DATASET_H_SESSIONS = [
    {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 10, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 90},
    {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 11, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 30},
    {"session_id": 3, "subject_id": 103, "division_id": 3, "teacher_id": 12, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 30},
]
DATASET_H_ROOMS = [
    {"room_id": 701, "name": "Large Auditorium", "capacity": 100, "room_type": "classroom"},
    {"room_id": 702, "name": "Small Room A", "capacity": 40, "room_type": "classroom"},
    {"room_id": 703, "name": "Small Room B", "capacity": 40, "room_type": "classroom"},
]
DATASET_H_SLOT_MAP = {1: 1, 2: 1, 3: 1}


# ==============================================================================
# SMALL DATASET: 2 Divisions, multiple subjects, classrooms, lab, timeslots
# ==============================================================================

def get_small_dataset() -> Dict[str, Any]:
    """Return a complete small dataset fixture (2 divisions)."""
    sessions = [
        # Division 1 sessions
        {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 1, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 2, "subject_id": 101, "division_id": 1, "teacher_id": 1, "session_no": 2, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 3, "subject_id": 102, "division_id": 1, "teacher_id": 2, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 4, "subject_id": 103, "division_id": 1, "teacher_id": 3, "session_no": 1, "subject_type": "lab", "elective_group_id": None, "division_strength": 50},
        # Division 2 sessions
        {"session_id": 5, "subject_id": 101, "division_id": 2, "teacher_id": 1, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 45},
        {"session_id": 6, "subject_id": 102, "division_id": 2, "teacher_id": 2, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 45},
        {"session_id": 7, "subject_id": 104, "division_id": 2, "teacher_id": 4, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 45},
        {"session_id": 8, "subject_id": 103, "division_id": 2, "teacher_id": 3, "session_no": 1, "subject_type": "lab", "elective_group_id": None, "division_strength": 45},
    ]

    rooms = [
        {"room_id": 1, "name": "C101", "capacity": 60, "room_type": "classroom"},
        {"room_id": 2, "name": "C102", "capacity": 60, "room_type": "classroom"},
        {"room_id": 3, "name": "Lab1", "capacity": 55, "room_type": "lab"},
    ]

    # 2 days, 4 periods each -> 8 slots
    timeslots = [
        {"slot_id": 1, "day": "Monday", "period": 1, "start_time": "09:00", "end_time": "10:00"},
        {"slot_id": 2, "day": "Monday", "period": 2, "start_time": "10:00", "end_time": "11:00"},
        {"slot_id": 3, "day": "Monday", "period": 3, "start_time": "11:00", "end_time": "12:00"},
        {"slot_id": 4, "day": "Monday", "period": 4, "start_time": "12:00", "end_time": "13:00"},
        {"slot_id": 5, "day": "Tuesday", "period": 1, "start_time": "09:00", "end_time": "10:00"},
        {"slot_id": 6, "day": "Tuesday", "period": 2, "start_time": "10:00", "end_time": "11:00"},
        {"slot_id": 7, "day": "Tuesday", "period": 3, "start_time": "11:00", "end_time": "12:00"},
        {"slot_id": 8, "day": "Tuesday", "period": 4, "start_time": "12:00", "end_time": "13:00"},
    ]

    # Teacher 1 unavailable on Tuesday period 4 (slot 8)
    teacher_availability: Set[Tuple[int, int]] = {
        (1, 8),  # (teacher_id, unavailable_slot_id)
    }

    return {
        "sessions": sessions,
        "rooms": rooms,
        "timeslots": timeslots,
        "availability": teacher_availability,
    }


# ==============================================================================
# MEDIUM DATASET: 4 divisions, 10 teachers, 10 subjects, 8 rooms, elective group
# ==============================================================================

def get_medium_dataset() -> Dict[str, Any]:
    """Return a realistic medium dataset fixture (4 divisions, 8 rooms, 10 teachers)."""
    # 4 divisions (strengths: 55, 50, 60, 45)
    # 10 subjects: 101-108 theory, 109-110 lab
    # Elective group 1 contains subject 107 and 108
    sessions = []
    sid = 1

    # Division 1 (strength 55)
    for sub, teacher, stype, eg in [
        (101, 1, "theory", None),
        (102, 2, "theory", None),
        (103, 3, "theory", None),
        (104, 4, "theory", None),
        (107, 7, "theory", 1),  # Elective
        (109, 9, "lab", None),
    ]:
        sessions.append({
            "session_id": sid,
            "subject_id": sub,
            "division_id": 1,
            "teacher_id": teacher,
            "session_no": 1,
            "subject_type": stype,
            "elective_group_id": eg,
            "division_strength": 55,
        })
        sid += 1

    # Division 2 (strength 50)
    for sub, teacher, stype, eg in [
        (101, 1, "theory", None),
        (102, 2, "theory", None),
        (105, 5, "theory", None),
        (106, 6, "theory", None),
        (108, 8, "theory", 1),  # Elective
        (110, 10, "lab", None),
    ]:
        sessions.append({
            "session_id": sid,
            "subject_id": sub,
            "division_id": 2,
            "teacher_id": teacher,
            "session_no": 1,
            "subject_type": stype,
            "elective_group_id": eg,
            "division_strength": 50,
        })
        sid += 1

    # Division 3 (strength 60)
    for sub, teacher, stype in [
        (103, 3, "theory"),
        (104, 4, "theory"),
        (105, 5, "theory"),
        (106, 6, "theory"),
        (109, 9, "lab"),
    ]:
        sessions.append({
            "session_id": sid,
            "subject_id": sub,
            "division_id": 3,
            "teacher_id": teacher,
            "session_no": 1,
            "subject_type": stype,
            "elective_group_id": None,
            "division_strength": 60,
        })
        sid += 1

    # Division 4 (strength 45)
    for sub, teacher, stype in [
        (101, 1, "theory"),
        (103, 3, "theory"),
        (105, 5, "theory"),
        (106, 6, "theory"),
        (110, 10, "lab"),
    ]:
        sessions.append({
            "session_id": sid,
            "subject_id": sub,
            "division_id": 4,
            "teacher_id": teacher,
            "session_no": 1,
            "subject_type": stype,
            "elective_group_id": None,
            "division_strength": 45,
        })
        sid += 1

    # 8 rooms: 6 classrooms, 2 labs
    rooms = [
        {"room_id": 1, "name": "Room 101", "capacity": 65, "room_type": "classroom"},
        {"room_id": 2, "name": "Room 102", "capacity": 65, "room_type": "classroom"},
        {"room_id": 3, "name": "Room 103", "capacity": 65, "room_type": "classroom"},
        {"room_id": 4, "name": "Room 104", "capacity": 65, "room_type": "classroom"},
        {"room_id": 5, "name": "Room 105", "capacity": 55, "room_type": "classroom"},
        {"room_id": 6, "name": "Room 106", "capacity": 50, "room_type": "classroom"},
        {"room_id": 7, "name": "Lab A", "capacity": 65, "room_type": "lab"},
        {"room_id": 8, "name": "Lab B", "capacity": 65, "room_type": "lab"},
    ]

    # 5 days x 4 periods = 20 slots
    timeslots = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    slot_num = 1
    for day in days:
        for p in range(1, 5):
            timeslots.append({
                "slot_id": slot_num,
                "day": day,
                "period": p,
                "start_time": f"{8+p}:00",
                "end_time": f"{9+p}:00",
            })
            slot_num += 1

    # Teacher unavailable slots:
    # Teacher 1 unavailable in slot 1 and slot 5
    # Teacher 2 unavailable in slot 4
    teacher_availability: Set[Tuple[int, int]] = {
        (1, 1),
        (1, 5),
        (2, 4),
    }

    return {
        "sessions": sessions,
        "rooms": rooms,
        "timeslots": timeslots,
        "availability": teacher_availability,
    }


# ==============================================================================
# IMPOSSIBLE DATASET: Overconstrained room capacity (forces CSP failure & retries)
# ==============================================================================

def get_impossible_dataset() -> Dict[str, Any]:
    """Return an impossible dataset fixture where suitable rooms are insufficient."""
    # 5 theory sessions scheduled in the same slot, but only 2 classrooms exist
    sessions = [
        {"session_id": 1, "subject_id": 101, "division_id": 1, "teacher_id": 1, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 2, "subject_id": 102, "division_id": 2, "teacher_id": 2, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 3, "subject_id": 103, "division_id": 3, "teacher_id": 3, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 4, "subject_id": 104, "division_id": 4, "teacher_id": 4, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
        {"session_id": 5, "subject_id": 105, "division_id": 5, "teacher_id": 5, "session_no": 1, "subject_type": "theory", "elective_group_id": None, "division_strength": 50},
    ]

    # Only 2 classrooms available
    rooms = [
        {"room_id": 1, "name": "Room 101", "capacity": 60, "room_type": "classroom"},
        {"room_id": 2, "name": "Room 102", "capacity": 60, "room_type": "classroom"},
    ]

    timeslots = [
        {"slot_id": 1, "day": "Monday", "period": 1, "start_time": "09:00", "end_time": "10:00"},
        {"slot_id": 2, "day": "Monday", "period": 2, "start_time": "10:00", "end_time": "11:00"},
    ]

    return {
        "sessions": sessions,
        "rooms": rooms,
        "timeslots": timeslots,
        "availability": set(),
    }
