"""Tests for Soft Constraint Scoring Module (Member 3).

Verifies hand-calculated penalties:
- Perfect timetable (0 penalty)
- Exactly 3 consecutive lectures (0 penalty)
- 4 consecutive lectures (1 penalty unit for division)
- 5 consecutive lectures (2 penalty units for division)
- Single gap (1 gap penalty unit)
- Multiple gaps (2 gap penalty units)
- Repeated subject on same day (spread penalty)
- Custom weights configuration
- Combined penalties
- Breakdown sum equals total score
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from timetable.backend.core.scoring import score_timetable, DEFAULT_WEIGHTS


def test_empty_timetable_score() -> None:
    """Empty timetable rows should produce score 0 with clean breakdown."""
    score = score_timetable([])
    assert score["total"] == 0
    assert score["breakdown"]["consecutive"] == 0
    assert score["breakdown"]["gap"] == 0
    assert score["breakdown"]["spread"] == 0


def test_perfect_timetable() -> None:
    """A clean schedule with 2 periods, different subjects, no gaps -> score 0."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
    ]
    res = score_timetable(rows)
    assert res["total"] == 0
    assert res["breakdown"]["consecutive"] == 0
    assert res["breakdown"]["gap"] == 0
    assert res["breakdown"]["spread"] == 0


def test_exactly_three_consecutive_lectures() -> None:
    """Exactly 3 consecutive lectures for a division with distinct teachers -> penalty 0."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 3, "slot_id": 3},
    ]
    res = score_timetable(rows)
    assert res["total"] == 0
    assert res["breakdown"]["consecutive"] == 0


def test_four_consecutive_lectures() -> None:
    """4 consecutive lectures for a division (with distinct teachers) -> 1 excess unit = 5 penalty."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 3, "slot_id": 3},
        {"session_id": 4, "division_id": 1, "teacher_id": 4, "subject_id": 104, "day": "Monday", "period": 4, "slot_id": 4},
    ]
    res = score_timetable(rows)
    # Division 1 has 4 consecutive -> (4 - 3) = 1 excess unit. Weight 5 -> 5.
    assert res["breakdown"]["consecutive"] == 5
    assert res["total"] == 5


def test_five_consecutive_lectures() -> None:
    """5 consecutive lectures for a division (with distinct teachers) -> 2 excess units = 10 penalty."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 3, "slot_id": 3},
        {"session_id": 4, "division_id": 1, "teacher_id": 4, "subject_id": 104, "day": "Monday", "period": 4, "slot_id": 4},
        {"session_id": 5, "division_id": 1, "teacher_id": 5, "subject_id": 105, "day": "Monday", "period": 5, "slot_id": 5},
    ]
    res = score_timetable(rows)
    # Division 1 has 5 consecutive -> (5 - 3) = 2 excess units. Weight 5 -> 10.
    assert res["breakdown"]["consecutive"] == 10
    assert res["total"] == 10


def test_one_gap() -> None:
    """Periods 1, 2, 4 (period 3 free) -> exactly 1 internal gap = 2 penalty."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 4, "slot_id": 4},
    ]
    res = score_timetable(rows)
    assert res["breakdown"]["gap"] == 2
    assert res["breakdown"]["consecutive"] == 0
    assert res["breakdown"]["spread"] == 0
    assert res["total"] == 2


def test_multiple_gaps() -> None:
    """Periods 1, 3, 5 -> 2 internal gaps (periods 2 and 4 free) = 2 * 2 = 4 penalty."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 3, "slot_id": 3},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 5, "slot_id": 5},
    ]
    res = score_timetable(rows)
    assert res["breakdown"]["gap"] == 4
    assert res["total"] == 4


def test_repeated_subject_spread() -> None:
    """Same subject appears twice on same day for division 1 -> 1 spread excess = 3 penalty."""
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 101, "day": "Monday", "period": 2, "slot_id": 2},
    ]
    res = score_timetable(rows)
    assert res["breakdown"]["spread"] == 3
    assert res["total"] == 3


def test_custom_weights() -> None:
    """Custom weights should be respected accurately."""
    custom_weights = {"consecutive": 10, "gap": 7, "spread": 4}
    # 4 consecutive lectures (1 excess) + 1 gap + 1 repeated subject
    rows = [
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 3, "slot_id": 3},
        {"session_id": 4, "division_id": 1, "teacher_id": 4, "subject_id": 104, "day": "Monday", "period": 4, "slot_id": 4},
        # Gap period 5 free
        {"session_id": 5, "division_id": 1, "teacher_id": 5, "subject_id": 101, "day": "Monday", "period": 6, "slot_id": 6},  # repeats 101
    ]
    res = score_timetable(rows, weights=custom_weights)
    # consecutive: (4 - 3) = 1 excess -> 1 * 10 = 10
    # gap: span 1 to 6 (6 periods), occupied 5 -> 1 gap * 7 = 7
    # spread: subject 101 appears twice -> 1 excess * 4 = 4
    # total = 10 + 7 + 4 = 21
    assert res["breakdown"]["consecutive"] == 10
    assert res["breakdown"]["gap"] == 7
    assert res["breakdown"]["spread"] == 4
    assert res["total"] == 21


def test_combined_penalties_and_breakdown_sum() -> None:
    """Combined penalties must equal total in both default and complex fixtures."""
    rows = [
        # Division 1, periods 1, 2, 3, 4 (4 consecutive -> excess 1 = 5)
        {"session_id": 1, "division_id": 1, "teacher_id": 1, "subject_id": 101, "day": "Monday", "period": 1, "slot_id": 1},
        {"session_id": 2, "division_id": 1, "teacher_id": 2, "subject_id": 102, "day": "Monday", "period": 2, "slot_id": 2},
        {"session_id": 3, "division_id": 1, "teacher_id": 3, "subject_id": 103, "day": "Monday", "period": 3, "slot_id": 3},
        {"session_id": 4, "division_id": 1, "teacher_id": 4, "subject_id": 104, "day": "Monday", "period": 4, "slot_id": 4},
        # Period 5 free (1 gap = 2)
        # Period 6: repeats subject 101 (spread = 3)
        {"session_id": 5, "division_id": 1, "teacher_id": 5, "subject_id": 101, "day": "Monday", "period": 6, "slot_id": 6},
    ]
    res = score_timetable(rows)
    assert res["breakdown"]["consecutive"] == 5
    assert res["breakdown"]["gap"] == 2
    assert res["breakdown"]["spread"] == 3
    assert res["total"] == 10
    assert res["total"] == (
        res["breakdown"]["consecutive"] + res["breakdown"]["gap"] + res["breakdown"]["spread"]
    )


if __name__ == "__main__":
    pytest.main([__file__])
