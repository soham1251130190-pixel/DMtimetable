"""Local search timetable optimizer for Member 3.

This module optimizes a valid timetable using slot-swap local search.
It randomly selects two timeslots and swaps all sessions scheduled in those slots,
moving their room assignments together.
Swaps are accepted strictly if:
1. Teacher availability is satisfied.
2. All hard constraints pass verification (0 violations).
3. The soft constraint penalty score strictly improves (new_score < current_score).
"""

import random
from typing import Any, Dict, List, Optional, Set, Union
from .verifier import verify_timetable
from .scoring import score_timetable


def optimize_timetable(
    rows: List[Dict[str, Any]],
    rooms: Optional[Union[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]] = None,
    timeslots: Optional[Union[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]] = None,
    teacher_availability: Any = None,
    weights: Optional[Dict[str, int]] = None,
    iterations: int = 2000,
    seed: int = 0,
) -> List[Dict[str, Any]]:
    """Optimize timetable using slot-swap local search.

    Parameters:
        rows: List of timetable session records
        rooms: Room definitions
        timeslots: Timeslot definitions
        teacher_availability: Teacher availability lookup or structure
        weights: Penalty weights for scoring
        iterations: Number of swap iterations to attempt (default 2000)
        seed: Random seed for deterministic execution

    Returns:
        List of optimized timetable session records.
    """
    if not rows:
        return []

    # Prepare timeslot lookup
    ts_dict: Dict[int, Dict[str, Any]] = {}
    if timeslots is not None:
        if isinstance(timeslots, dict):
            ts_dict = timeslots
        elif isinstance(timeslots, list):
            ts_dict = {t["slot_id"]: t for t in timeslots}

    # Collect all available slot IDs
    slot_ids_set: Set[int] = set()
    if ts_dict:
        slot_ids_set.update(ts_dict.keys())
    else:
        for r in rows:
            sid = r.get("slot_id")
            if sid is not None:
                slot_ids_set.add(sid)

    slot_ids = sorted(slot_ids_set)
    if len(slot_ids) < 2:
        return [dict(r) for r in rows]

    # Current working solution
    current_rows = [dict(r) for r in rows]
    current_score = score_timetable(current_rows, weights=weights, timeslots=timeslots)["total"]

    # If score is already 0, it is globally optimal
    if current_score == 0:
        return current_rows

    rng = random.Random(seed)

    for _ in range(iterations):
        slot_a, slot_b = rng.sample(slot_ids, 2)

        # Build candidate with swapped slots
        has_relevant_sessions = False
        candidate_rows: List[Dict[str, Any]] = []

        for r in current_rows:
            new_r = dict(r)
            sid = new_r.get("slot_id")
            if sid == slot_a:
                has_relevant_sessions = True
                new_r["slot_id"] = slot_b
                if slot_b in ts_dict:
                    ts = ts_dict[slot_b]
                    if "day" in new_r:
                        new_r["day"] = ts.get("day", new_r.get("day"))
                    if "period" in new_r:
                        new_r["period"] = ts.get("period", new_r.get("period"))
            elif sid == slot_b:
                has_relevant_sessions = True
                new_r["slot_id"] = slot_a
                if slot_a in ts_dict:
                    ts = ts_dict[slot_a]
                    if "day" in new_r:
                        new_r["day"] = ts.get("day", new_r.get("day"))
                    if "period" in new_r:
                        new_r["period"] = ts.get("period", new_r.get("period"))

            candidate_rows.append(new_r)

        if not has_relevant_sessions:
            continue

        # 1. Hard constraint check (including teacher availability)
        violations = verify_timetable(
            candidate_rows,
            rooms=rooms,
            timeslots=timeslots,
            teacher_availability=teacher_availability,
        )
        if len(violations) > 0:
            continue

        # 2. Score candidate
        candidate_score = score_timetable(
            candidate_rows, weights=weights, timeslots=timeslots
        )["total"]

        # 3. Accept strictly if improved
        if candidate_score < current_score:
            current_rows = candidate_rows
            current_score = candidate_score
            if current_score == 0:
                break

    return current_rows
