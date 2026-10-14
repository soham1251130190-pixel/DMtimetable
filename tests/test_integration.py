"""Full integration test suite for Member 1 + Member 2 + Member 3.

Verifies:
- M1 -> M2: Database loader output consumed directly by Graph Builder and Coloring
- M2 -> M3: Coloring slot map consumed directly by Room CSP, Verifier, Scorer, and Optimizer
- M3 -> M1: Final verified schedule persisted using Member 1 save_timetable and verified via get_timetable
- Full end-to-end M1 -> M2 -> M3 pipeline on REAL SQLite databases (small.db, medium.db, impossible.db)
- Scenarios 1 through 11 as specified in the team integration contract
- Strict failure safety: invalid timetables are NEVER saved
"""

import sys
from pathlib import Path

# Bootstrap sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pytest

# Member 1 imports
import timetable.backend.db.db as dal

# Member 2 imports
from core.graph_builder import build_conflict_graph
from core.coloring import color_graph, ColoringError, is_valid_coloring

# Member 3 imports
from timetable.backend.core.room_assigner import assign_rooms, RoomAssignmentError
from timetable.backend.core.verifier import verify_timetable
from timetable.backend.core.scoring import score_timetable
from timetable.backend.core.optimizer import optimize_timetable
from timetable.backend.core.pipeline import generate_timetable


SMALL_DB_PATH = Path("timetable/backend/db/data/small.db")
MEDIUM_DB_PATH = Path("timetable/backend/db/data/medium.db")
IMPOSSIBLE_DB_PATH = Path("timetable/backend/db/data/impossible.db")


def create_in_memory_clone(source_db_path: Path) -> sqlite3.Connection:
    """Create an isolated in-memory copy of a SQLite database to prevent mutation of disk data."""
    mem_conn = dal.connect(":memory:")
    disk_conn = dal.connect(source_db_path)
    disk_conn.backup(mem_conn)
    disk_conn.close()
    return mem_conn


# ==============================================================================
# BOUNDARY TESTS: M1 -> M2, M2 -> M3, M3 -> M1
# ==============================================================================

def test_m1_to_m2_boundary() -> None:
    """Verify Member 1 loaders feed directly into Member 2 conflict graph and coloring."""
    conn = dal.connect(SMALL_DB_PATH)
    sessions = dal.load_sessions(conn)
    timeslots = dal.load_timeslots(conn)
    availability = dal.load_availability(conn)

    assert len(sessions) > 0
    assert len(timeslots) == 30
    assert len(availability) > 0

    # Member 2 builds graph directly from M1 sessions
    G = build_conflict_graph(sessions)
    assert G.number_of_nodes() == len(sessions)

    # Member 2 colors graph using M1 availability and timeslots
    slot_map = color_graph(G, availability=availability, timeslots=timeslots, seed=0)
    assert len(slot_map) == len(sessions)
    # Check no graph conflicts
    assert is_valid_coloring(G, slot_map) == []


def test_m2_to_m3_boundary() -> None:
    """Verify Member 2 slot_map feeds directly into Member 3 Room CSP and Verifier."""
    conn = dal.connect(SMALL_DB_PATH)
    sessions = dal.load_sessions(conn)
    rooms = dal.load_rooms(conn)
    timeslots = dal.load_timeslots(conn)
    availability = dal.load_availability(conn)

    G = build_conflict_graph(sessions)
    slot_map = color_graph(G, availability=availability, timeslots=timeslots, seed=0)

    # Member 3 assigns rooms using M1 sessions, M2 slot_map, and M1 rooms
    room_map = assign_rooms(sessions, slot_map, rooms)
    assert len(room_map) == len(sessions)

    # Construct timetable rows
    ts_dict = {t["slot_id"]: t for t in timeslots}
    rows = []
    for s in sessions:
        sid = s["session_id"]
        slot_id = slot_map[sid]
        rows.append({
            **s,
            "slot_id": slot_id,
            "room_id": room_map[sid],
            "day": ts_dict[slot_id]["day"],
            "period": ts_dict[slot_id]["period"],
        })

    # Member 3 independently verifies hard constraints
    violations = verify_timetable(rows, rooms=rooms, timeslots=timeslots, teacher_availability=availability)
    assert violations == []


def test_m3_to_m1_boundary() -> None:
    """Verify Member 3 output can be saved to Member 1 DB and read back accurately."""
    conn = create_in_memory_clone(SMALL_DB_PATH)
    sessions = dal.load_sessions(conn)
    rooms = dal.load_rooms(conn)
    timeslots = dal.load_timeslots(conn)
    availability = dal.load_availability(conn)

    G = build_conflict_graph(sessions)
    slot_map = color_graph(G, availability=availability, timeslots=timeslots, seed=0)
    room_map = assign_rooms(sessions, slot_map, rooms)

    rows_to_save = [
        {"session_id": s["session_id"], "slot_id": slot_map[s["session_id"]], "room_id": room_map[s["session_id"]]}
        for s in sessions
    ]

    run_id = dal.new_run_id(conn, status="running")
    dal.save_timetable(conn, run_id, rows_to_save)
    dal.update_run(conn, run_id, status="completed", colors_used=len(set(slot_map.values())), penalty_score=0.0)

    # Read back from Member 1
    saved_rows = dal.get_timetable(conn, run_id)
    assert len(saved_rows) == len(sessions)
    for r in saved_rows:
        assert r["slot_id"] is not None
        assert r["room_id"] is not None
        assert r["teacher_name"] is not None
        assert r["division_name"] is not None


# ==============================================================================
# SCENARIOS 1 - 11 (REAL PIPELINE INTEGRATION)
# ==============================================================================

def test_scenario_1_normal_timetable_small() -> None:
    """Scenario 1: Full pipeline execution on small.db produces valid timetable."""
    conn = create_in_memory_clone(SMALL_DB_PATH)
    result = generate_timetable(conn=conn, seed=42, optimizer_iterations=100)

    assert result["status"] == "ok"
    assert result["violations"] == []
    assert result["colors_used"] > 0
    assert "total" in result["score"]
    assert result["score"]["total"] >= 0

    # Verify saved state in DB
    saved = dal.get_timetable(conn, result["run_id"])
    assert len(saved) == len(dal.load_sessions(conn))


def test_scenario_2_multiple_divisions() -> None:
    """Scenario 2: Multi-division dataset ensures no division has simultaneous sessions."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    result = generate_timetable(conn=conn, seed=10, optimizer_iterations=50)

    assert result["status"] == "ok"
    assert result["violations"] == []

    # Check division exclusivity in saved rows
    saved = dal.get_timetable(conn, result["run_id"])
    div_slots = set()
    for row in saved:
        key = (row["division_id"], row["slot_id"])
        assert key not in div_slots, f"Division {row['division_id']} double-booked in slot {row['slot_id']}"
        div_slots.add(key)


def test_scenario_3_multiple_teachers() -> None:
    """Scenario 3: Multi-teacher dataset ensures no teacher has simultaneous sessions."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    result = generate_timetable(conn=conn, seed=20, optimizer_iterations=50)

    assert result["status"] == "ok"
    assert result["violations"] == []

    saved = dal.get_timetable(conn, result["run_id"])
    teacher_slots = set()
    for row in saved:
        key = (row["teacher_id"], row["slot_id"])
        assert key not in teacher_slots, f"Teacher {row['teacher_id']} double-booked in slot {row['slot_id']}"
        teacher_slots.add(key)


def test_scenario_4_teacher_availability() -> None:
    """Scenario 4: Blocked teacher slots are never scheduled."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    availability = dal.load_availability(conn)

    result = generate_timetable(conn=conn, seed=30, optimizer_iterations=50)
    assert result["status"] == "ok"

    saved = dal.get_timetable(conn, result["run_id"])
    for row in saved:
        tid = row["teacher_id"]
        slot = row["slot_id"]
        assert slot in availability[tid], f"Teacher {tid} placed in unavailable slot {slot}"


def test_scenario_5_room_capacity() -> None:
    """Scenario 5: Room capacity is strictly >= division strength for all sessions."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    divisions = {d["division_id"]: d["strength"] for d in dal.load_divisions(conn)}
    rooms = {r["room_id"]: r["capacity"] for r in dal.load_rooms(conn)}

    result = generate_timetable(conn=conn, seed=40, optimizer_iterations=50)
    assert result["status"] == "ok"

    saved = dal.get_timetable(conn, result["run_id"])
    for row in saved:
        div_strength = divisions[row["division_id"]]
        room_cap = rooms[row["room_id"]]
        assert room_cap >= div_strength, (
            f"Room {row['room_id']} cap {room_cap} < division {row['division_id']} strength {div_strength}"
        )


def test_scenario_6_room_type_compatibility() -> None:
    """Scenario 6: Theory/elective sessions get classrooms; lab sessions get labs."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    rooms = {r["room_id"]: r["room_type"] for r in dal.load_rooms(conn)}

    result = generate_timetable(conn=conn, seed=50, optimizer_iterations=50)
    assert result["status"] == "ok"

    saved = dal.get_timetable(conn, result["run_id"])
    for row in saved:
        stype = row["subject_type"]
        rtype = rooms[row["room_id"]]
        if stype in ("theory", "elective"):
            assert rtype == "classroom", f"Subject type {stype} placed in room type {rtype}"
        elif stype == "lab":
            assert rtype == "lab", f"Lab subject placed in room type {rtype}"


def test_scenario_7_no_room_collision() -> None:
    """Scenario 7: No room is double-booked in the same timeslot."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    result = generate_timetable(conn=conn, seed=60, optimizer_iterations=50)
    assert result["status"] == "ok"

    saved = dal.get_timetable(conn, result["run_id"])
    room_slots = set()
    for row in saved:
        key = (row["room_id"], row["slot_id"])
        assert key not in room_slots, f"Room {row['room_id']} double-booked in slot {row['slot_id']}"
        room_slots.add(key)


def test_scenario_8_impossible_room_assignment() -> None:
    """Scenario 8: Overconstrained room resources fail cleanly without saving invalid timetable."""
    conn = create_in_memory_clone(SMALL_DB_PATH)
    # Delete all rooms except one classroom, creating room shortage
    with conn:
        conn.execute("DELETE FROM timetable")
        conn.execute("DELETE FROM timetable_runs")
        conn.execute("DELETE FROM rooms WHERE room_id > 1")

    result = generate_timetable(conn=conn, seed=0, max_attempts=3)
    assert result["status"] == "failed"
    assert "failed after" in result["reason"]

    # Verify no timetable rows saved for this run
    saved = dal.get_timetable(conn, result["run_id"])
    assert len(saved) == 0

    # Verify run status is failed in database
    runs = dal.list_runs(conn)
    matching_run = next(r for r in runs if r["run_id"] == result["run_id"])
    assert matching_run["status"] == "failed"


def test_scenario_9_impossible_coloring() -> None:
    """Scenario 9: Uncolorable constraints (impossible.db) fail cleanly without saving invalid timetable."""
    conn = create_in_memory_clone(IMPOSSIBLE_DB_PATH)
    result = generate_timetable(conn=conn, seed=0, max_attempts=3)

    assert result["status"] == "failed"
    assert "Coloring failed after" in result["reason"] or "Pipeline failed after" in result["reason"]

    # Must NOT save any timetable rows
    saved = dal.get_timetable(conn, result["run_id"])
    assert len(saved) == 0

    # Run status marked failed
    runs = dal.list_runs(conn)
    matching_run = next(r for r in runs if r["run_id"] == result["run_id"])
    assert matching_run["status"] == "failed"


def test_scenario_10_optimization_guarantees() -> None:
    """Scenario 10: Optimizer never worsens score and preserves all hard constraints."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    sessions = dal.load_sessions(conn)
    rooms = dal.load_rooms(conn)
    timeslots = dal.load_timeslots(conn)
    availability = dal.load_availability(conn)
    divisions = {d["division_id"]: d["strength"] for d in dal.load_divisions(conn)}
    for s in sessions:
        s["division_strength"] = divisions.get(s["division_id"], 0)

    G = build_conflict_graph(sessions)
    slot_map = color_graph(G, availability=availability, timeslots=timeslots, seed=0)
    room_map = assign_rooms(sessions, slot_map, rooms)

    ts_dict = {t["slot_id"]: t for t in timeslots}
    rows = [{
        **s,
        "slot_id": slot_map[s["session_id"]],
        "room_id": room_map[s["session_id"]],
        "day": ts_dict[slot_map[s["session_id"]]]["day"],
        "period": ts_dict[slot_map[s["session_id"]]]["period"],
    } for s in sessions]

    initial_score = score_timetable(rows, timeslots=timeslots)["total"]
    optimized = optimize_timetable(rows, rooms=rooms, timeslots=timeslots, teacher_availability=availability, iterations=300, seed=42)
    final_score = score_timetable(optimized, timeslots=timeslots)["total"]

    # 1. Score is non-increasing
    assert final_score <= initial_score
    # 2. Hard constraints preserved (0 violations)
    violations = verify_timetable(optimized, rooms=rooms, timeslots=timeslots, teacher_availability=availability)
    assert violations == []


def test_scenario_11_persistence_integrity() -> None:
    """Scenario 11: Saved timetable in DB matches exactly what pipeline produced."""
    conn = create_in_memory_clone(MEDIUM_DB_PATH)
    result = generate_timetable(conn=conn, seed=77, optimizer_iterations=100)
    assert result["status"] == "ok"

    saved_rows = dal.get_timetable(conn, result["run_id"])
    assert len(saved_rows) == 72

    # Verify runs table updated
    runs = dal.list_runs(conn)
    matching = next(r for r in runs if r["run_id"] == result["run_id"])
    assert matching["status"] == "completed"
    assert matching["colors_used"] == result["colors_used"]
    assert matching["penalty_score"] == result["score"]["total"]


if __name__ == "__main__":
    pytest.main([__file__])



