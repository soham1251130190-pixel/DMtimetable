"""Soft constraint scoring module for Member 3.

This module evaluates timetable quality based on three configurable penalty metrics:
1. Consecutive lectures penalty:
   For each division and each teacher on each day, allow up to 3 consecutive lectures.
   Every lecture in a contiguous block after the third incurs a penalty.
2. Gap penalty:
   For each division on each day, count free periods between the first and last lecture.
3. Subject spread penalty:
   For each division, if the same subject appears more than once on the same day,
   each additional occurrence incurs a spread penalty.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union

DEFAULT_WEIGHTS = {
    "consecutive": 5,
    "gap": 2,
    "spread": 3,
}


def _extract_slot_day_period(
    row: Dict[str, Any],
    timeslot_lookup: Dict[int, Dict[str, Any]],
) -> Tuple[str, int]:
    """Extract day and period for a row from row data or timeslot lookup."""
    slot_id = row.get("slot_id")
    if slot_id is not None and slot_id in timeslot_lookup:
        ts = timeslot_lookup[slot_id]
        return str(ts.get("day", "Day1")), int(ts.get("period", slot_id))

    if "day" in row and "period" in row:
        return str(row["day"]), int(row["period"])

    if slot_id is not None:
        # Fallback if no day/period metadata: single day, slot_id as period
        return "Day1", int(slot_id)

    return "Day1", 0


def _count_consecutive_excess(periods: List[int], max_allowed: int = 3) -> int:
    """Calculate excess consecutive lectures beyond max_allowed in sorted contiguous blocks."""
    if not periods:
        return 0

    unique_sorted = sorted(set(periods))
    excess = 0
    current_run = 1

    for i in range(1, len(unique_sorted)):
        if unique_sorted[i] == unique_sorted[i - 1] + 1:
            current_run += 1
        else:
            if current_run > max_allowed:
                excess += current_run - max_allowed
            current_run = 1

    if current_run > max_allowed:
        excess += current_run - max_allowed

    return excess


def score_timetable(
    rows: List[Dict[str, Any]],
    weights: Optional[Dict[str, int]] = None,
    timeslots: Optional[Union[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Calculate soft constraint penalty score for timetable rows.

    Parameters:
        rows: List of timetable session records
        weights: Penalty weights dictionary (consecutive, gap, spread)
        timeslots: Timeslots lookup list or dict (maps slot_id -> {day, period, ...})

    Returns:
        Dict with 'total' penalty score and 'breakdown' dictionary.
    """
    effective_weights = dict(DEFAULT_WEIGHTS)
    if weights is not None:
        effective_weights.update(weights)

    consecutive_weight = effective_weights.get("consecutive", 5)
    gap_weight = effective_weights.get("gap", 2)
    spread_weight = effective_weights.get("spread", 3)

    if not rows:
        return {
            "total": 0,
            "breakdown": {
                "consecutive": 0,
                "gap": 0,
                "spread": 0,
            },
        }

    # Normalize timeslot lookup
    ts_dict: Dict[int, Dict[str, Any]] = {}
    if timeslots is not None:
        if isinstance(timeslots, dict):
            ts_dict = timeslots
        elif isinstance(timeslots, list):
            ts_dict = {t["slot_id"]: t for t in timeslots}

    # Data grouping structures
    # (division_id, day) -> list of periods
    div_day_periods: Dict[Tuple[int, str], List[int]] = {}
    # (teacher_id, day) -> list of periods
    teacher_day_periods: Dict[Tuple[int, str], List[int]] = {}
    # (division_id, day, subject_id) -> count
    div_day_subject_count: Dict[Tuple[int, str, int], int] = {}

    for row in rows:
        slot_id = row.get("slot_id")
        if slot_id is None:
            continue

        day, period = _extract_slot_day_period(row, ts_dict)

        div_id = row.get("division_id")
        teacher_id = row.get("teacher_id")
        subject_id = row.get("subject_id")

        if div_id is not None:
            div_day_periods.setdefault((div_id, day), []).append(period)
            if subject_id is not None:
                key = (div_id, day, subject_id)
                div_day_subject_count[key] = div_day_subject_count.get(key, 0) + 1

        if teacher_id is not None:
            teacher_day_periods.setdefault((teacher_id, day), []).append(period)

    # 1. Consecutive lectures penalty: for each division and teacher
    consecutive_excess_units = 0

    for (div_id, day), periods in div_day_periods.items():
        consecutive_excess_units += _count_consecutive_excess(periods, max_allowed=3)

    for (teacher_id, day), periods in teacher_day_periods.items():
        consecutive_excess_units += _count_consecutive_excess(periods, max_allowed=3)

    consecutive_penalty = consecutive_excess_units * consecutive_weight

    # 2. Gap penalty: for each division and day
    gap_units = 0
    for (div_id, day), periods in div_day_periods.items():
        unique_periods = sorted(set(periods))
        if len(unique_periods) > 1:
            first_p = unique_periods[0]
            last_p = unique_periods[-1]
            span = last_p - first_p + 1
            internal_gaps = span - len(unique_periods)
            gap_units += internal_gaps

    gap_penalty = gap_units * gap_weight

    # 3. Subject spread penalty: for each division
    # If the same subject appears more than once on the same day
    spread_excess_units = 0
    for (div_id, day, sub_id), count in div_day_subject_count.items():
        if count > 1:
            spread_excess_units += (count - 1)

    spread_penalty = spread_excess_units * spread_weight

    total_score = consecutive_penalty + gap_penalty + spread_penalty

    return {
        "total": total_score,
        "breakdown": {
            "consecutive": consecutive_penalty,
            "gap": gap_penalty,
            "spread": spread_penalty,
        },
    }
