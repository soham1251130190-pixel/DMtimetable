"""End-to-end timetable generation pipeline for Member 3.

This module coordinates:
1. Loading sessions, rooms, timeslots, and availability via Member 1 (Database)
2. Generating slot coloring via Member 2 (Conflict Graph + DSATUR)
3. Assigning rooms via Member 3 Room CSP solver (with retry on failure)
4. Initial verification of hard constraints
5. Initial soft constraint penalty scoring
6. Optimization via slot-swap local search
7. Final verification of hard constraints
8. Saving verified timetable to Member 1 Database
"""

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .room_assigner import assign_rooms, RoomAssignmentError
from .verifier import verify_timetable
from .scoring import score_timetable
from .optimizer import optimize_timetable


def generate_timetable(
    conn: Any = None,
    seed: int = 0,
    weights: Optional[Dict[str, int]] = None,
    data_provider: Any = None,
    coloring_provider: Any = None,
    max_attempts: int = 10,
    optimizer_iterations: int = 1000,
) -> Dict[str, Any]:
    """Execute complete timetable generation pipeline.

    Parameters:
        conn: Optional DB connection or client object (for Member 1 integration)
        seed: Random seed for deterministic generation and optimization
        weights: Soft constraint scoring weights
        data_provider: Custom data provider (for test mocks; if None, uses Member 1)
        coloring_provider: Custom coloring provider (for test mocks; if None, uses Member 2)
        max_attempts: Maximum retry attempts for coloring/room failures (default 10)
        optimizer_iterations: Iterations for slot-swap optimization (default 1000)

    Returns:
        Dict with status, run_id, colors_used, score, and violations.
    """
    using_real_db = False
    dal = None

    # Step 1: Resolve data source (Member 1 Database or injected data_provider)
    if data_provider is None:
        import timetable.backend.db.db as dal_mod
        dal = dal_mod

        if conn is None:
            conn = dal.connect()
        elif isinstance(conn, (str, Path)):
            conn = dal.connect(conn)

        if hasattr(conn, "execute") and hasattr(conn, "cursor"):
            # Real SQLite connection
            using_real_db = True
            sessions = dal.load_sessions(conn)
            rooms = dal.load_rooms(conn)
            teacher_availability = dal.load_availability(conn)
            timeslots = dal.load_timeslots(conn)
            divisions = dal.load_divisions(conn)

            # Enrich sessions with division strength from divisions table
            div_strengths = {d["division_id"]: d.get("strength", 0) for d in divisions}
            for s in sessions:
                if "division_strength" not in s or s["division_strength"] is None:
                    s["division_strength"] = div_strengths.get(s["division_id"], 0)

            run_id = dal.new_run_id(conn, status="running")
        elif hasattr(conn, "load_sessions"):
            data_provider = conn
        else:
            from timetable.backend.test_support.mock_db import MockDataProvider
            data_provider = MockDataProvider()

    if not using_real_db:
        run_id = f"run_{seed}_{uuid.uuid4().hex[:8]}"
        sessions = data_provider.load_sessions()
        rooms = data_provider.load_rooms()
        teacher_availability = data_provider.load_availability()
        timeslots = data_provider.load_timeslots()

    # Step 2: Resolve coloring engine (Member 2 or injected coloring_provider)
    using_real_coloring = False
    if coloring_provider is None:
        using_real_coloring = True
        from core.graph_builder import build_conflict_graph
        from core.coloring import color_graph, ColoringError

        G = build_conflict_graph(sessions)
        slot_capacity = {
            "classroom": sum(1 for r in rooms if r.get("room_type") == "classroom"),
            "lab": sum(1 for r in rooms if r.get("room_type") == "lab"),
        }

    # Step 3: Coloring & Room Assignment with Retry Loop
    slot_map: Optional[Dict[int, int]] = None
    room_assignment: Optional[Dict[int, int]] = None
    last_assignment_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        current_seed = seed + attempt * 1000
        try:
            if using_real_coloring:
                # Try coloring using Member 2 DSATUR
                cap = slot_capacity if attempt % 2 == 0 else None
                slot_map = color_graph(
                    G,
                    availability=teacher_availability,
                    timeslots=timeslots,
                    slot_capacity=cap,
                    seed=current_seed,
                )
            else:
                try:
                    slot_map = coloring_provider.color_graph(
                        sessions=sessions,
                        timeslots=timeslots,
                        seed=current_seed,
                        attempt=attempt,
                        availability=teacher_availability,
                    )
                except TypeError:
                    slot_map = coloring_provider.color_graph(
                        sessions=sessions,
                        timeslots=timeslots,
                        seed=current_seed,
                        attempt=attempt,
                    )

            room_assignment = assign_rooms(sessions, slot_map, rooms)
            last_assignment_error = None
            break
        except Exception as err:
            last_assignment_error = err
            continue

    if room_assignment is None or slot_map is None:
        failure_prefix = (
            "Room assignment"
            if isinstance(last_assignment_error, RoomAssignmentError)
            else "Coloring"
        )
        error_msg = (
            f"{failure_prefix} failed after {max_attempts} attempts: "
            f"{getattr(last_assignment_error, 'reason', str(last_assignment_error))}"
        )
        if using_real_db and dal is not None:
            dal.update_run(conn, run_id, status="failed")

        return {
            "run_id": run_id,
            "status": "failed",
            "reason": error_msg,
            "violations": [
                {
                    "type": "pipeline_failure",
                    "slot_id": getattr(last_assignment_error, "slot_id", None),
                    "session_ids": getattr(last_assignment_error, "affected_session_ids", []),
                    "reason": str(last_assignment_error),
                }
            ],
        }

    # Step 4: Build timetable rows
    rooms_dict = {r["room_id"]: r for r in rooms}
    ts_dict = {t["slot_id"]: t for t in timeslots}

    timetable_rows: List[Dict[str, Any]] = []
    for s in sessions:
        sid = s["session_id"]
        slot_id = slot_map[sid]
        room_id = room_assignment[sid]

        ts_info = ts_dict.get(slot_id, {})
        rm_info = rooms_dict.get(room_id, {})

        row = dict(s)
        row["slot_id"] = slot_id
        row["room_id"] = room_id
        row["day"] = ts_info.get("day", "Day1")
        row["period"] = ts_info.get("period", slot_id)
        row["room_name"] = rm_info.get("name")
        row["room_capacity"] = rm_info.get("capacity")
        row["room_type"] = rm_info.get("room_type")
        timetable_rows.append(row)

    # Step 5: Verify initial timetable
    initial_violations = verify_timetable(
        timetable_rows,
        rooms=rooms,
        timeslots=timeslots,
        teacher_availability=teacher_availability,
    )
    if initial_violations:
        if using_real_db and dal is not None:
            dal.update_run(conn, run_id, status="failed")
        return {
            "run_id": run_id,
            "status": "failed",
            "reason": f"Initial timetable failed verification with {len(initial_violations)} violations.",
            "violations": initial_violations,
        }

    # Step 6: Optimize timetable via local search
    optimized_rows = optimize_timetable(
        timetable_rows,
        rooms=rooms,
        timeslots=timeslots,
        teacher_availability=teacher_availability,
        weights=weights,
        iterations=optimizer_iterations,
        seed=seed,
    )

    # Step 7: Verify optimized timetable
    final_violations = verify_timetable(
        optimized_rows,
        rooms=rooms,
        timeslots=timeslots,
        teacher_availability=teacher_availability,
    )
    if final_violations:
        if using_real_db and dal is not None:
            dal.update_run(conn, run_id, status="failed")
        return {
            "run_id": run_id,
            "status": "failed",
            "reason": f"Optimized timetable failed verification with {len(final_violations)} violations.",
            "violations": final_violations,
        }

    # Step 8: Final Score
    final_score = score_timetable(optimized_rows, weights=weights, timeslots=timeslots)

    # Step 9: Save verified timetable
    colors_used = len(set(r["slot_id"] for r in optimized_rows))

    if using_real_db and dal is not None:
        dal.save_timetable(conn, run_id, optimized_rows)
        dal.update_run(
            conn,
            run_id,
            status="completed",
            colors_used=colors_used,
            penalty_score=float(final_score["total"]),
        )
    elif data_provider is not None and hasattr(data_provider, "save_timetable"):
        data_provider.save_timetable(run_id, optimized_rows)

    return {
        "run_id": run_id,
        "status": "ok",
        "colors_used": colors_used,
        "score": final_score,
        "violations": [],
    }
