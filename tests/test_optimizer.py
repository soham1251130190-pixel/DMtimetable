"""Tests for Slot-Swap Local Search Optimizer (Member 3).

Verifies:
1. Score never increases (strictly non-increasing)
2. Deliberately bad timetable improves
3. Hard constraints remain valid after optimization
4. Teacher availability remains valid after optimization
5. Same seed produces same deterministic result
6. Empty timetable works cleanly
7. Already optimal timetable remains valid and optimal
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from timetable.backend.core.optimizer import optimize_timetable
from timetable.backend.core.verifier import verify_timetable
from timetable.backend.core.scoring import score_timetable


@pytest.fixture
def base_rooms():
    return [
        {"room_id": 1, "name": "Room 101", "capacity": 60, "room_type": "classroom"},
        {"room_id": 2, "name": "Room 102", "capacity": 60, "room_type": "classroom"},
    ]


@pytest.fixture
def base_timeslots():
    return [
        {"slot_id": 1, "day": "Monday", "period": 1, "start_time": "09:00", "end_time": "10:00"},
        {"slot_id": 2, "day": "Monday", "period": 2, "start_time": "10:00", "end_time": "11:00"},
        {"slot_id": 3, "day": "Monday", "period": 3, "start_time": "11:00", "end_time": "12:00"},
        {"slot_id": 4, "day": "Monday", "period": 4, "start_time": "12:00", "end_time": "13:00"},
        {"slot_id": 5, "day": "Tuesday", "period": 1, "start_time": "09:00", "end_time": "10:00"},
        {"slot_id": 6, "day": "Tuesday", "period": 2, "start_time": "10:00", "end_time": "11:00"},
    ]


def test_empty_timetable_optimizer() -> None:
    """Empty timetable input should return empty list."""
    res = optimize_timetable([])
    assert res == []


def test_already_optimal_timetable(base_rooms, base_timeslots) -> None:
    """Already optimal timetable (score 0) remains valid and unchanged in score."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "slot_id": 1, "room_id": 1, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "slot_id": 2, "room_id": 1, "day": "Monday", "period": 2, "subject_type": "theory", "division_strength": 50},
    ]
    initial_score = score_timetable(rows, timeslots=base_timeslots)["total"]
    assert initial_score == 0

    optimized = optimize_timetable(rows, rooms=base_rooms, timeslots=base_timeslots, iterations=100, seed=42)
    assert verify_timetable(optimized, rooms=base_rooms, timeslots=base_timeslots) == []
    final_score = score_timetable(optimized, timeslots=base_timeslots)["total"]
    assert final_score == 0


def test_deliberately_bad_timetable_improves(base_rooms, base_timeslots) -> None:
    """Deliberately sub-optimal schedule (4 consecutive lectures) should improve by moving a lecture to Tuesday."""
    # 4 consecutive lectures on Monday: periods 1, 2, 3, 4
    # Tuesday slots (5, 6) are free
    bad_rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "slot_id": 1, "room_id": 1, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "slot_id": 2, "room_id": 1, "day": "Monday", "period": 2, "subject_type": "theory", "division_strength": 50},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "slot_id": 3, "room_id": 1, "day": "Monday", "period": 3, "subject_type": "theory", "division_strength": 50},
        {"session_id": 4, "division_id": 1, "teacher_id": 4, "subject_id": 104, "slot_id": 4, "room_id": 1, "day": "Monday", "period": 4, "subject_type": "theory", "division_strength": 50},
    ]
    initial_score = score_timetable(bad_rows, timeslots=base_timeslots)["total"]
    assert initial_score == 5  # 1 excess consecutive lecture = 5

    optimized = optimize_timetable(
        bad_rows,
        rooms=base_rooms,
        timeslots=base_timeslots,
        iterations=200,
        seed=1,
    )
    final_score = score_timetable(optimized, timeslots=base_timeslots)["total"]
    assert final_score < initial_score
    assert final_score == 0  # Should achieve perfect 0 by swapping slot 4 with empty Tuesday slot 5 or 6


def test_score_never_increases(base_rooms, base_timeslots) -> None:
    """Across various random seeds and iterations, score must never be higher than initial."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "slot_id": 1, "room_id": 1, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "slot_id": 2, "room_id": 1, "day": "Monday", "period": 2, "subject_type": "theory", "division_strength": 50},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "slot_id": 4, "room_id": 1, "day": "Monday", "period": 4, "subject_type": "theory", "division_strength": 50},  # Gap at period 3
    ]
    initial_score = score_timetable(rows, timeslots=base_timeslots)["total"]

    for seed in [10, 42, 99]:
        optimized = optimize_timetable(
            rows,
            rooms=base_rooms,
            timeslots=base_timeslots,
            iterations=150,
            seed=seed,
        )
        final_score = score_timetable(optimized, timeslots=base_timeslots)["total"]
        assert final_score <= initial_score


def test_hard_constraints_remain_valid(base_rooms, base_timeslots) -> None:
    """Optimizer must never introduce any hard constraint violation."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "slot_id": 1, "room_id": 1, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 2, "division_id": 2, "teacher_id": 2, "subject_id": 102, "slot_id": 1, "room_id": 2, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "slot_id": 3, "room_id": 1, "day": "Monday", "period": 3, "subject_type": "theory", "division_strength": 50},
    ]
    assert verify_timetable(rows, rooms=base_rooms, timeslots=base_timeslots) == []

    optimized = optimize_timetable(
        rows,
        rooms=base_rooms,
        timeslots=base_timeslots,
        iterations=300,
        seed=7,
    )
    violations = verify_timetable(optimized, rooms=base_rooms, timeslots=base_timeslots)
    assert violations == []


def test_teacher_availability_respected(base_rooms, base_timeslots) -> None:
    """Teacher availability constraints must be preserved throughout optimization."""
    # Teacher 1 is unavailable in slot 5
    unavailability = {(1, 5)}
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "slot_id": 1, "room_id": 1, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "slot_id": 3, "room_id": 1, "day": "Monday", "period": 3, "subject_type": "theory", "division_strength": 50},
    ]

    optimized = optimize_timetable(
        rows,
        rooms=base_rooms,
        timeslots=base_timeslots,
        teacher_availability=unavailability,
        iterations=500,
        seed=123,
    )
    violations = verify_timetable(
        optimized,
        rooms=base_rooms,
        timeslots=base_timeslots,
        teacher_availability=unavailability,
    )
    assert violations == []

    # Verify session 1 with Teacher 1 was never placed in slot 5
    s1 = next(r for r in optimized if r["session_id"] == 1)
    assert s1["slot_id"] != 5


def test_determinism(base_rooms, base_timeslots) -> None:
    """Same input and same seed must produce exact same optimized timetable."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "slot_id": 1, "room_id": 1, "day": "Monday", "period": 1, "subject_type": "theory", "division_strength": 50},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "slot_id": 2, "room_id": 1, "day": "Monday", "period": 2, "subject_type": "theory", "division_strength": 50},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "slot_id": 4, "room_id": 1, "day": "Monday", "period": 4, "subject_type": "theory", "division_strength": 50},
    ]

    res1 = optimize_timetable(rows, rooms=base_rooms, timeslots=base_timeslots, iterations=200, seed=555)
    res2 = optimize_timetable(rows, rooms=base_rooms, timeslots=base_timeslots, iterations=200, seed=555)

    assert res1 == res2


if __name__ == "__main__":
    pytest.main([__file__])
