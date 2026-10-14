"""Tests for Room Assigner CSP (Member 3).

Verifies backtracking search, MRV heuristic, forward checking,
room type compatibility, capacity constraints, determinism, and error reporting.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from timetable.backend.core.room_assigner import assign_rooms, RoomAssignmentError, RoomCSP
from timetable.backend.test_support.mock_data import (
    DATASET_A_SESSIONS,
    DATASET_A_ROOMS,
    DATASET_A_SLOT_MAP,
    DATASET_B_SESSIONS,
    DATASET_B_ROOMS,
    DATASET_B_SLOT_MAP,
    DATASET_C_SESSIONS,
    DATASET_C_ROOMS,
    DATASET_C_SLOT_MAP,
    DATASET_D_SESSIONS,
    DATASET_D_ROOMS,
    DATASET_D_SLOT_MAP,
    DATASET_E_SESSIONS,
    DATASET_E_ROOMS,
    DATASET_E_SLOT_MAP,
    DATASET_F_SESSIONS,
    DATASET_F_ROOMS,
    DATASET_F_SLOT_MAP,
    DATASET_G_SESSIONS,
    DATASET_G_ROOMS,
    DATASET_G_SLOT_MAP,
    DATASET_H_SESSIONS,
    DATASET_H_ROOMS,
    DATASET_H_SLOT_MAP,
)


def test_empty_sessions() -> None:
    """Empty sessions list should return empty assignment without error."""
    result = assign_rooms([], {}, [])
    assert result == {}


def test_dataset_a_success() -> None:
    """Dataset A: 3 sessions, 3 suitable rooms -> assignment succeeds."""
    assignment = assign_rooms(DATASET_A_SESSIONS, DATASET_A_SLOT_MAP, DATASET_A_ROOMS)
    assert len(assignment) == 3
    # Check all sessions got assigned distinct rooms in the same slot
    assigned_rooms = list(assignment.values())
    assert len(set(assigned_rooms)) == 3
    for sid, rid in assignment.items():
        assert rid in [101, 102, 103]


def test_dataset_b_failure() -> None:
    """Dataset B: 3 sessions in same slot, 2 suitable rooms -> raises RoomAssignmentError."""
    with pytest.raises(RoomAssignmentError) as exc_info:
        assign_rooms(DATASET_B_SESSIONS, DATASET_B_SLOT_MAP, DATASET_B_ROOMS)

    err = exc_info.value
    assert err.slot_id == 1
    assert set(err.affected_session_ids) == {1, 2, 3}
    assert "2 suitable rooms are available" in err.reason or "sessions require suitable rooms" in err.reason


def test_dataset_c_room_types() -> None:
    """Dataset C: Theory session must get classroom; lab session must get lab."""
    assignment = assign_rooms(DATASET_C_SESSIONS, DATASET_C_SLOT_MAP, DATASET_C_ROOMS)
    # Session 1 is theory -> Room 201 (classroom)
    # Session 2 is lab -> Room 202 (lab)
    assert assignment[1] == 201
    assert assignment[2] == 202


def test_dataset_d_capacity_filtering() -> None:
    """Dataset D: Session 1 (strength 60) must get Large Room 302 (cap 65); Session 2 gets Room 301."""
    assignment = assign_rooms(DATASET_D_SESSIONS, DATASET_D_SLOT_MAP, DATASET_D_ROOMS)
    assert assignment[1] == 302
    assert assignment[2] == 301


def test_dataset_e_multiple_sessions_no_collision() -> None:
    """Dataset E: Multiple sessions in same slot must have no room collision."""
    assignment = assign_rooms(DATASET_E_SESSIONS, DATASET_E_SLOT_MAP, DATASET_E_ROOMS)
    assert len(assignment) == 4
    # All room assignments must be strictly unique
    assert len(set(assignment.values())) == 4


def test_dataset_f_room_reuse_across_slots() -> None:
    """Dataset F: Sessions in different slots may reuse the same room."""
    assignment = assign_rooms(DATASET_F_SESSIONS, DATASET_F_SLOT_MAP, DATASET_F_ROOMS)
    assert len(assignment) == 2
    assert assignment[1] == 501
    assert assignment[2] == 501


def test_dataset_g_no_suitable_room() -> None:
    """Dataset G: One session requiring a lab but only classroom exists -> clear failure."""
    with pytest.raises(RoomAssignmentError) as exc_info:
        assign_rooms(DATASET_G_SESSIONS, DATASET_G_SLOT_MAP, DATASET_G_ROOMS)

    err = exc_info.value
    assert err.slot_id == 1
    assert 1 in err.affected_session_ids
    assert "no compatible room" in err.reason or "suitable" in err.reason


def test_dataset_h_mrv_advantage() -> None:
    """Dataset H: Domains designed so MRV selects the constrained session first."""
    csp = RoomCSP(1, DATASET_H_SESSIONS, DATASET_H_ROOMS)
    # Check that session 1 has domain size 1, while sessions 2 & 3 have domain size 3
    assert len(csp.initial_domains[1]) == 1  # Only room 701 has capacity >= 90
    assert len(csp.initial_domains[2]) == 3
    assert len(csp.initial_domains[3]) == 3

    assignment = csp.solve()
    assert assignment is not None
    assert assignment[1] == 701
    assert set(assignment.values()) == {701, 702, 703}
    # With MRV and forward checking, session 1 is selected first and no deep backtracking is required
    assert csp.search_nodes <= 4


def test_mrv_vs_plain_backtracking_comparison() -> None:
    """Explicitly verify that MRV explores fewer or equal search nodes than static variable ordering."""
    # Run RoomCSP with MRV
    mrv_csp = RoomCSP(1, DATASET_H_SESSIONS, DATASET_H_ROOMS)
    mrv_solution = mrv_csp.solve()
    mrv_nodes = mrv_csp.search_nodes

    # Plain backtracking simulation: static variable ordering [session 2, session 3, session 1]
    static_order = [DATASET_H_SESSIONS[1], DATASET_H_SESSIONS[2], DATASET_H_SESSIONS[0]]
    static_domains = {s["session_id"]: list(mrv_csp.initial_domains[s["session_id"]]) for s in static_order}

    plain_nodes = 0

    def plain_backtrack(idx: int, current_assignment: dict) -> bool:
        nonlocal plain_nodes
        if idx == len(static_order):
            return True
        curr_session = static_order[idx]
        cid = curr_session["session_id"]
        for r_id in static_domains[cid]:
            if r_id in current_assignment.values():
                continue
            plain_nodes += 1
            current_assignment[cid] = r_id
            if plain_backtrack(idx + 1, current_assignment):
                return True
            del current_assignment[cid]
        return False

    plain_backtrack(0, {})

    # MRV chooses constrained session 1 first, avoiding failed branches in session 2/3
    assert mrv_solution is not None
    assert mrv_nodes < plain_nodes, f"MRV nodes ({mrv_nodes}) must be strictly less than plain static ordering ({plain_nodes})"


def test_determinism() -> None:
    """Same input must always produce exact same room assignment."""
    run1 = assign_rooms(DATASET_E_SESSIONS, DATASET_E_SLOT_MAP, DATASET_E_ROOMS)
    run2 = assign_rooms(DATASET_E_SESSIONS, DATASET_E_SLOT_MAP, DATASET_E_ROOMS)
    assert run1 == run2


def test_missing_slot_error() -> None:
    """Session missing from slot_map should raise RoomAssignmentError."""
    incomplete_slot_map = {1: 1, 2: 1}  # Session 3 missing
    with pytest.raises(RoomAssignmentError) as exc_info:
        assign_rooms(DATASET_A_SESSIONS, incomplete_slot_map, DATASET_A_ROOMS)

    err = exc_info.value
    assert 3 in err.affected_session_ids
    assert "no slot assigned" in err.reason


if __name__ == "__main__":
    pytest.main([__file__])
