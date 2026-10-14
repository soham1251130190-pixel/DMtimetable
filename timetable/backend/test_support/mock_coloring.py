"""TEST ONLY - MOCK MEMBER 2 INTERFACE

This module provides a mock coloring provider mimicking Member 2's conflict graph coloring.
It returns deterministic slot maps {session_id: slot_id} for Member 3 tests.
It does NOT implement Member 2's actual DSATUR or graph-coloring algorithm.
When Member 2 provides their real implementation, this mock will be replaced or adapted.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from timetable.backend.core.verifier import check_teacher_availability


class MockColoringProvider:
    """Mock coloring provider conforming to Member 2 interface."""

    def __init__(
        self,
        custom_slot_maps: Optional[Dict[int, Dict[int, int]]] = None,
        fail_first_n_attempts: int = 0,
    ) -> None:
        """Initialize mock coloring provider.

        Parameters:
            custom_slot_maps: Optional dict mapping attempt number -> {session_id: slot_id}
            fail_first_n_attempts: Number of initial attempts to return an overconstrained
                                   slot map (packing sessions into slot 1) to test retries.
        """
        self.custom_slot_maps = custom_slot_maps or {}
        self.fail_first_n_attempts = fail_first_n_attempts
        self.call_history: List[Dict[str, Any]] = []

    def color_graph(
        self,
        sessions: List[Dict[str, Any]],
        timeslots: List[Dict[str, Any]],
        seed: int = 0,
        attempt: int = 0,
        availability: Any = None,
        **kwargs: Any,
    ) -> Dict[int, int]:
        """Generate a deterministic slot mapping {session_id: slot_id}.

        Parameters:
            sessions: List of session records
            timeslots: List of timeslot records
            seed: Deterministic seed
            attempt: Retry attempt number
            availability: Optional teacher availability constraints

        Returns:
            Dict mapping session_id -> slot_id
        """
        self.call_history.append({"seed": seed, "attempt": attempt})

        # 1. Check custom slot maps
        if attempt in self.custom_slot_maps:
            return dict(self.custom_slot_maps[attempt])
        if -1 in self.custom_slot_maps:
            return dict(self.custom_slot_maps[-1])

        slot_ids = sorted(t["slot_id"] for t in timeslots) if timeslots else [1]
        sorted_sessions = sorted(sessions, key=lambda s: s["session_id"])

        # 2. Check retry failure simulation
        if attempt < self.fail_first_n_attempts:
            # Overconstrain by mapping all sessions to slot 1
            first_slot = slot_ids[0]
            return {s["session_id"]: first_slot for s in sorted_sessions}

        # 3. Default deterministic conflict-free slot scheduling
        # Shift slot ordering based on (seed + attempt)
        num_slots = len(slot_ids)
        shift = (seed + attempt) % num_slots
        ordered_slots = slot_ids[shift:] + slot_ids[:shift]

        slot_map: Dict[int, int] = {}
        teacher_busy: Set[Tuple[int, int]] = set()  # (teacher_id, slot_id)
        division_busy: Set[Tuple[int, int]] = set()  # (division_id, slot_id)

        for s in sorted_sessions:
            sid = s["session_id"]
            tid = s.get("teacher_id")
            did = s.get("division_id")

            # Find first slot without teacher conflict, division conflict, or teacher unavailability
            assigned_slot = None
            for slot in ordered_slots:
                t_conflict = tid is not None and (tid, slot) in teacher_busy
                d_conflict = did is not None and (did, slot) in division_busy
                t_unavail = (
                    tid is not None
                    and availability is not None
                    and not check_teacher_availability(availability, tid, slot)
                )

                if not t_conflict and not d_conflict and not t_unavail:
                    assigned_slot = slot
                    break

            if assigned_slot is None:
                # Secondary fallback: at least respect teacher availability
                for slot in ordered_slots:
                    t_unavail = (
                        tid is not None
                        and availability is not None
                        and not check_teacher_availability(availability, tid, slot)
                    )
                    if not t_unavail:
                        assigned_slot = slot
                        break

            if assigned_slot is None:
                assigned_slot = ordered_slots[sid % num_slots]

            slot_map[sid] = assigned_slot
            if tid is not None:
                teacher_busy.add((tid, assigned_slot))
            if did is not None:
                division_busy.add((did, assigned_slot))

        return slot_map
