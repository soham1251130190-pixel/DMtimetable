"""Room assignment Constraint Satisfaction Problem (CSP) solver for Member 3.

This module assigns physical rooms to scheduled sessions for each timeslot.
It uses backtracking search with Minimum Remaining Values (MRV) heuristic
and forward checking constraint propagation.
"""

from typing import Any, Dict, List, Optional, Set


class RoomAssignmentError(Exception):
    """Raised when no valid room assignment exists for scheduled sessions."""

    def __init__(
        self,
        slot_id: Optional[int],
        affected_session_ids: List[int],
        reason: str,
    ) -> None:
        self.slot_id = slot_id
        self.affected_session_ids = affected_session_ids
        self.reason = reason
        super().__init__(reason)


def is_room_type_compatible(subject_type: str, room_type: str) -> bool:
    """Check if the given room type is compatible with session subject type.

    Rules:
    - 'theory' and 'elective' require 'classroom'
    - 'lab' requires 'lab'
    - Case-insensitive exact matches also accepted (e.g., 'classroom' == 'classroom')
    """
    st = str(subject_type).strip().lower()
    rt = str(room_type).strip().lower()

    if st == rt:
        return True
    if st in ("theory", "elective", "classroom") and rt in ("classroom", "theory"):
        return True
    if st == "lab" and rt == "lab":
        return True
    return False


def get_compatible_rooms_for_session(
    session: Dict[str, Any], rooms: List[Dict[str, Any]]
) -> List[int]:
    """Return list of room_ids that satisfy room type and capacity requirements."""
    subject_type = session.get("subject_type", "theory")
    division_strength = session.get("division_strength")
    if division_strength is None:
        division_strength = 0

    compatible: List[int] = []
    # Sort rooms deterministically by room_id
    sorted_rooms = sorted(rooms, key=lambda r: (r["room_id"]))

    for r in sorted_rooms:
        r_type = r.get("room_type", "")
        r_cap = r.get("capacity", 0)
        if is_room_type_compatible(subject_type, r_type) and r_cap >= division_strength:
            compatible.append(r["room_id"])

    return compatible


class RoomCSP:
    """Deterministic CSP solver for room assignments in a single slot."""

    def __init__(
        self,
        slot_id: int,
        sessions_in_slot: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
    ) -> None:
        self.slot_id = slot_id
        self.sessions = sorted(sessions_in_slot, key=lambda s: s["session_id"])
        self.rooms = rooms
        self.room_dict = {r["room_id"]: r for r in rooms}
        self.search_nodes = 0

        # Build initial domains for each session_id
        self.initial_domains: Dict[int, List[int]] = {}
        for s in self.sessions:
            sid = s["session_id"]
            self.initial_domains[sid] = get_compatible_rooms_for_session(s, rooms)

    def solve(self) -> Optional[Dict[int, int]]:
        """Solve room assignment for this slot using MRV and Forward Checking."""
        # Initial check for immediately empty domains
        for s in self.sessions:
            sid = s["session_id"]
            if not self.initial_domains[sid]:
                raise RoomAssignmentError(
                    slot_id=self.slot_id,
                    affected_session_ids=[sid],
                    reason=(
                        f"Session {sid} (type '{s.get('subject_type')}', strength {s.get('division_strength')}) "
                        f"has no compatible room with sufficient capacity in slot {self.slot_id}."
                    ),
                )

        # Quick pigeonhole check: total sessions > total unique available rooms
        all_candidate_rooms: Set[int] = set()
        for dom in self.initial_domains.values():
            all_candidate_rooms.update(dom)

        if len(self.sessions) > len(all_candidate_rooms):
            session_ids = [s["session_id"] for s in self.sessions]
            raise RoomAssignmentError(
                slot_id=self.slot_id,
                affected_session_ids=session_ids,
                reason=(
                    f"{len(self.sessions)} sessions require suitable rooms in slot {self.slot_id}, "
                    f"but only {len(all_candidate_rooms)} suitable rooms are available."
                ),
            )

        # Start backtracking search
        domains = {sid: list(dom) for sid, dom in self.initial_domains.items()}
        assignment: Dict[int, int] = {}
        assigned_session_ids: Set[int] = set()

        result = self._backtrack(assignment, assigned_session_ids, domains)
        return result

    def _backtrack(
        self,
        assignment: Dict[int, int],
        assigned_session_ids: Set[int],
        domains: Dict[int, List[int]],
    ) -> Optional[Dict[int, int]]:
        if len(assigned_session_ids) == len(self.sessions):
            return dict(assignment)

        # MRV: Choose unassigned session with smallest domain
        # Deterministic tie-breaking on session_id
        unassigned = [s for s in self.sessions if s["session_id"] not in assigned_session_ids]
        candidate_session = min(
            unassigned,
            key=lambda s: (len(domains[s["session_id"]]), s["session_id"]),
        )
        cid = candidate_session["session_id"]

        for room_id in list(domains[cid]):
            self.search_nodes += 1
            assignment[cid] = room_id
            assigned_session_ids.add(cid)

            # Forward checking: remove room_id from remaining unassigned sessions
            new_domains = {s_id: list(dom) for s_id, dom in domains.items()}
            domain_wipeout = False

            for other in unassigned:
                oid = other["session_id"]
                if oid == cid:
                    continue
                if room_id in new_domains[oid]:
                    new_domains[oid] = [r for r in new_domains[oid] if r != room_id]
                    if len(new_domains[oid]) == 0:
                        domain_wipeout = True
                        break

            if not domain_wipeout:
                res = self._backtrack(assignment, assigned_session_ids, new_domains)
                if res is not None:
                    return res

            # Backtrack
            del assignment[cid]
            assigned_session_ids.remove(cid)

        return None


def assign_rooms(
    sessions: List[Dict[str, Any]],
    slot_map: Dict[int, int],
    rooms: List[Dict[str, Any]],
) -> Dict[int, int]:
    """Assign suitable physical rooms to sessions according to timeslots.

    Parameters:
        sessions: List of session dicts
        slot_map: Dict mapping session_id -> slot_id
        rooms: List of room dicts

    Returns:
        Dict mapping session_id -> room_id

    Raises:
        RoomAssignmentError: When no valid room assignment exists.
    """
    assign_rooms.search_nodes = 0  # type: ignore[attr-defined]

    if not sessions:
        return {}

    # Check for missing slots
    missing_slots = [s["session_id"] for s in sessions if s["session_id"] not in slot_map]
    if missing_slots:
        raise RoomAssignmentError(
            slot_id=None,
            affected_session_ids=missing_slots,
            reason=f"Sessions {missing_slots} have no slot assigned in slot_map.",
        )

    # Group sessions by slot_id
    sessions_by_slot: Dict[int, List[Dict[str, Any]]] = {}
    for s in sessions:
        sid = s["session_id"]
        slot_id = slot_map[sid]
        sessions_by_slot.setdefault(slot_id, []).append(s)

    # Sort slots deterministically
    sorted_slot_ids = sorted(sessions_by_slot.keys())
    overall_assignment: Dict[int, int] = {}
    total_nodes = 0

    for slot_id in sorted_slot_ids:
        slot_sessions = sessions_by_slot[slot_id]
        csp = RoomCSP(slot_id, slot_sessions, rooms)
        slot_assignment = csp.solve()
        total_nodes += csp.search_nodes

        if slot_assignment is None:
            session_ids = [s["session_id"] for s in slot_sessions]
            raise RoomAssignmentError(
                slot_id=slot_id,
                affected_session_ids=session_ids,
                reason=(
                    f"Constraint satisfaction failed: No collision-free room assignment "
                    f"found for {len(slot_sessions)} sessions in slot {slot_id}."
                ),
            )

        overall_assignment.update(slot_assignment)

    assign_rooms.search_nodes = total_nodes  # type: ignore[attr-defined]
    return overall_assignment


assign_rooms.search_nodes = 0  # type: ignore[attr-defined]
