"""Tests for Independent Hard Constraint Verifier (Member 3).

Verifies detection of:
- Valid timetable (returns [])
- Teacher conflict
- Division conflict
- Room conflict (double booking)
- Wrong room type
- Insufficient room capacity
- Unavailable teacher
- Missing slot
- Missing room
- Multiple simultaneous violations
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from timetable.backend.core.verifier import verify_timetable


@pytest.fixture
def base_rooms():
    return [
        {"room_id": 1, "name": "Room 101", "capacity": 60, "room_type": "classroom"},
        {"room_id": 2, "name": "Room 102", "capacity": 60, "room_type": "classroom"},
        {"room_id": 3, "name": "Lab 1", "capacity": 40, "room_type": "lab"},
    ]


@pytest.fixture
def valid_timetable_rows():
    return [
        {
            "session_id": 1,
            "slot_id": 1,
            "room_id": 1,
            "teacher_id": 10,
            "division_id": 1,
            "subject_id": 101,
            "subject_type": "theory",
            "division_strength": 50,
        },
        {
            "session_id": 2,
            "slot_id": 1,
            "room_id": 2,
            "teacher_id": 11,
            "division_id": 2,
            "subject_id": 102,
            "subject_type": "theory",
            "division_strength": 55,
        },
        {
            "session_id": 3,
            "slot_id": 2,
            "room_id": 3,
            "teacher_id": 12,
            "division_id": 1,
            "subject_id": 103,
            "subject_type": "lab",
            "division_strength": 35,
        },
    ]


def test_empty_timetable_valid() -> None:
    """Empty timetable rows should return 0 violations."""
    violations = verify_timetable([])
    assert violations == []


def test_valid_timetable(valid_timetable_rows, base_rooms) -> None:
    """A timetable meeting all hard constraints should return []."""
    violations = verify_timetable(valid_timetable_rows, rooms=base_rooms)
    assert violations == []


def test_teacher_conflict(valid_timetable_rows, base_rooms) -> None:
    """Same teacher assigned to two sessions in the same slot should trigger teacher_conflict."""
    rows = [dict(r) for r in valid_timetable_rows]
    # Set teacher 10 on both session 1 and session 2 in slot 1
    rows[1]["teacher_id"] = 10

    violations = verify_timetable(rows, rooms=base_rooms)
    v_types = [v["type"] for v in violations]
    assert "teacher_conflict" in v_types
    v = next(v for v in violations if v["type"] == "teacher_conflict")
    assert v["teacher_id"] == 10
    assert v["slot_id"] == 1
    assert set(v["session_ids"]) == {1, 2}


def test_division_conflict(valid_timetable_rows, base_rooms) -> None:
    """Same division assigned to two sessions in the same slot should trigger division_conflict."""
    rows = [dict(r) for r in valid_timetable_rows]
    # Set division 1 on both session 1 and session 2 in slot 1
    rows[1]["division_id"] = 1

    violations = verify_timetable(rows, rooms=base_rooms)
    v_types = [v["type"] for v in violations]
    assert "division_conflict" in v_types
    v = next(v for v in violations if v["type"] == "division_conflict")
    assert v["division_id"] == 1
    assert v["slot_id"] == 1
    assert set(v["session_ids"]) == {1, 2}


def test_room_conflict(valid_timetable_rows, base_rooms) -> None:
    """Same room assigned to two sessions in the same slot should trigger room_conflict."""
    rows = [dict(r) for r in valid_timetable_rows]
    # Both session 1 and session 2 assigned to Room 1 in slot 1
    rows[1]["room_id"] = 1

    violations = verify_timetable(rows, rooms=base_rooms)
    v_types = [v["type"] for v in violations]
    assert "room_conflict" in v_types
    v = next(v for v in violations if v["type"] == "room_conflict")
    assert v["room_id"] == 1
    assert v["slot_id"] == 1
    assert set(v["session_ids"]) == {1, 2}


def test_wrong_room_type(valid_timetable_rows, base_rooms) -> None:
    """Theory session assigned to lab room should trigger room_type violation."""
    rows = [dict(r) for r in valid_timetable_rows]
    # Session 1 is theory, assign to Room 3 (lab)
    rows[0]["room_id"] = 3

    violations = verify_timetable(rows, rooms=base_rooms)
    v_types = [v["type"] for v in violations]
    assert "room_type" in v_types
    v = next(v for v in violations if v["type"] == "room_type")
    assert v["session_id"] == 1
    assert v["room_id"] == 3


def test_insufficient_capacity(valid_timetable_rows, base_rooms) -> None:
    """Division strength exceeding room capacity should trigger room_capacity violation."""
    rows = [dict(r) for r in valid_timetable_rows]
    # Session 3 has division_strength 35, assign to Room 3 (capacity 40). Increase strength to 45.
    rows[2]["division_strength"] = 45

    violations = verify_timetable(rows, rooms=base_rooms)
    v_types = [v["type"] for v in violations]
    assert "room_capacity" in v_types
    v = next(v for v in violations if v["type"] == "room_capacity")
    assert v["session_id"] == 3
    assert v["capacity"] == 40
    assert v["division_strength"] == 45


def test_teacher_unavailable(valid_timetable_rows, base_rooms) -> None:
    """Assigning teacher to an unavailable slot should trigger teacher_unavailable."""
    rows = [dict(r) for r in valid_timetable_rows]
    # Teacher 10 unavailable in slot 1
    unavailability = {(10, 1)}

    violations = verify_timetable(rows, rooms=base_rooms, teacher_availability=unavailability)
    v_types = [v["type"] for v in violations]
    assert "teacher_unavailable" in v_types
    v = next(v for v in violations if v["type"] == "teacher_unavailable")
    assert v["teacher_id"] == 10
    assert v["slot_id"] == 1
    assert v["session_id"] == 1


def test_missing_slot_and_missing_room(valid_timetable_rows, base_rooms) -> None:
    """Sessions with None slot or room should report missing_slot and missing_room."""
    rows = [
        {
            "session_id": 1,
            "slot_id": None,
            "room_id": 1,
            "teacher_id": 10,
            "division_id": 1,
            "subject_type": "theory",
            "division_strength": 30,
        },
        {
            "session_id": 2,
            "slot_id": 1,
            "room_id": None,
            "teacher_id": 11,
            "division_id": 2,
            "subject_type": "theory",
            "division_strength": 30,
        },
    ]
    violations = verify_timetable(rows, rooms=base_rooms)
    v_types = [v["type"] for v in violations]
    assert "missing_slot" in v_types
    assert "missing_room" in v_types


def test_multiple_simultaneous_violations(valid_timetable_rows, base_rooms) -> None:
    """A heavily corrupted schedule should report all violation types simultaneously."""
    rows = [
        # Session 1: slot 1, room 3 (lab, for theory session) -> wrong room type
        {
            "session_id": 1,
            "slot_id": 1,
            "room_id": 3,
            "teacher_id": 10,
            "division_id": 1,
            "subject_id": 101,
            "subject_type": "theory",
            "division_strength": 50,  # also capacity 40 < 50 -> room_capacity
        },
        # Session 2: slot 1, room 3 -> room conflict with session 1, teacher 10 -> teacher conflict, division 1 -> division conflict
        {
            "session_id": 2,
            "slot_id": 1,
            "room_id": 3,
            "teacher_id": 10,
            "division_id": 1,
            "subject_id": 102,
            "subject_type": "lab",
            "division_strength": 30,
        },
    ]
    unavailability = {(10, 1)}

    violations = verify_timetable(rows, rooms=base_rooms, teacher_availability=unavailability)
    v_types = set(v["type"] for v in violations)

    assert "teacher_conflict" in v_types
    assert "division_conflict" in v_types
    assert "room_conflict" in v_types
    assert "room_type" in v_types
    assert "room_capacity" in v_types
    assert "teacher_unavailable" in v_types


if __name__ == "__main__":
    pytest.main([__file__])
