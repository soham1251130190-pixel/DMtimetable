"""Independent hard constraint verifier for Member 3.

This module independently verifies timetable schedules without calling the CSP solver.
It checks:
1. Teacher conflict (no teacher in multiple sessions in same slot)
2. Division conflict (no division in multiple sessions in same slot)
3. Room conflict (no room assigned to multiple sessions in same slot)
4. Room type compatibility (theory -> classroom, lab -> lab)
5. Room capacity sufficiency (room capacity >= division strength)
6. Teacher availability (teachers only scheduled in available slots)
7. Missing slot or missing room assignments
"""

from typing import Any, Callable, Dict, List, Optional, Set, Union
from .room_assigner import is_room_type_compatible


def check_teacher_availability(
    availability: Any, teacher_id: int, slot_id: int
) -> bool:
    """Check if teacher is available in slot_id using various availability representations."""
    if availability is None:
        return True

    # Callable: fn(teacher_id, slot_id) -> bool
    if callable(availability):
        return bool(availability(teacher_id, slot_id))

    # Object with is_available method
    if hasattr(availability, "is_available") and callable(getattr(availability, "is_available")):
        return bool(availability.is_available(teacher_id, slot_id))

    # Set of unavailable (teacher_id, slot_id) tuples
    if isinstance(availability, set):
        # By convention in availability structures:
        # If set contains (teacher_id, slot_id), check if it's unavailable or available
        # We also check an attribute or handle unavailable set
        if getattr(availability, "is_available_set", False):
            return (teacher_id, slot_id) in availability
        # Default for set: unavailable pairs
        return (teacher_id, slot_id) not in availability

    # Dict of {(teacher_id, slot_id): bool}
    if isinstance(availability, dict):
        if (teacher_id, slot_id) in availability:
            return bool(availability[(teacher_id, slot_id)])
        # Dict of {teacher_id: set_of_available_slots or list}
        if teacher_id in availability:
            teacher_slots = availability[teacher_id]
            if isinstance(teacher_slots, (set, list, tuple)):
                return slot_id in teacher_slots
            if isinstance(teacher_slots, dict):
                return bool(teacher_slots.get(slot_id, True))
        # Dict of {teacher_id: set_of_unavailable_slots}
        if hasattr(availability, "unavailable_by_teacher"):
            unavail = getattr(availability, "unavailable_by_teacher")
            return slot_id not in unavail.get(teacher_id, set())

    # List of record dicts: [{"teacher_id": 1, "slot_id": 2, "is_available": True/False}]
    if isinstance(availability, list):
        for rec in availability:
            if rec.get("teacher_id") == teacher_id and rec.get("slot_id") == slot_id:
                return bool(rec.get("is_available", True))

    return True


def verify_timetable(
    rows: List[Dict[str, Any]],
    rooms: Optional[Union[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]] = None,
    timeslots: Optional[Union[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]] = None,
    teacher_availability: Any = None,
) -> List[Dict[str, Any]]:
    """Verify that a timetable satisfies all hard constraints.

    Parameters:
        rows: List of timetable session records (each with session_id, slot_id, room_id, etc.)
        rooms: Optional room definitions (list or dict mapping room_id -> room dict)
        timeslots: Optional timeslot definitions
        teacher_availability: Optional teacher availability data or lookup structure

    Returns:
        List of violation dictionaries. Returns [] if the timetable is fully valid.
    """
    violations: List[Dict[str, Any]] = []

    if not rows:
        return violations

    # Normalize rooms lookup dict
    room_dict: Dict[int, Dict[str, Any]] = {}
    if rooms is not None:
        if isinstance(rooms, dict):
            room_dict = rooms
        elif isinstance(rooms, list):
            room_dict = {r["room_id"]: r for r in rooms}

    # Tracking structures for conflicts
    teacher_slots: Dict[tuple, List[int]] = {}  # (teacher_id, slot_id) -> [session_ids]
    division_slots: Dict[tuple, List[int]] = {}  # (division_id, slot_id) -> [session_ids]
    room_slots: Dict[tuple, List[int]] = {}  # (room_id, slot_id) -> [session_ids]

    for row in rows:
        sid = row.get("session_id")
        slot_id = row.get("slot_id")
        room_id = row.get("room_id")
        teacher_id = row.get("teacher_id")
        division_id = row.get("division_id")
        subject_type = row.get("subject_type", "theory")
        division_strength = row.get("division_strength")
        if division_strength is None:
            division_strength = 0

        # 1. Missing slot check
        if slot_id is None:
            violations.append({
                "type": "missing_slot",
                "session_id": sid,
                "message": f"Session {sid} has no assigned timeslot.",
            })
            continue

        # 2. Missing room check
        if room_id is None:
            violations.append({
                "type": "missing_room",
                "session_id": sid,
                "message": f"Session {sid} has no assigned room.",
            })

        # Track teacher conflicts
        if teacher_id is not None:
            teacher_slots.setdefault((teacher_id, slot_id), []).append(sid)

        # Track division conflicts
        if division_id is not None:
            division_slots.setdefault((division_id, slot_id), []).append(sid)

        # Track room conflicts
        if room_id is not None:
            room_slots.setdefault((room_id, slot_id), []).append(sid)

        # Room properties lookup
        room_info = room_dict.get(room_id) if room_id is not None else None
        room_type = (
            room_info.get("room_type")
            if room_info
            else row.get("room_type")
        )
        room_capacity = (
            room_info.get("capacity")
            if room_info
            else row.get("room_capacity")
        )

        # 3. Room type compatibility
        if room_id is not None and room_type is not None:
            if not is_room_type_compatible(subject_type, room_type):
                violations.append({
                    "type": "room_type",
                    "session_id": sid,
                    "room_id": room_id,
                    "subject_type": subject_type,
                    "room_type": room_type,
                    "message": (
                        f"Session {sid} requires room compatible with '{subject_type}', "
                        f"but assigned room {room_id} has type '{room_type}'."
                    ),
                })

        # 4. Room capacity sufficiency
        if room_id is not None and room_capacity is not None:
            if room_capacity < division_strength:
                violations.append({
                    "type": "room_capacity",
                    "session_id": sid,
                    "room_id": room_id,
                    "capacity": room_capacity,
                    "division_strength": division_strength,
                    "message": (
                        f"Room {room_id} capacity ({room_capacity}) is less than "
                        f"division strength ({division_strength}) for session {sid}."
                    ),
                })

        # 5. Teacher availability check
        if teacher_id is not None and teacher_availability is not None:
            if not check_teacher_availability(teacher_availability, teacher_id, slot_id):
                violations.append({
                    "type": "teacher_unavailable",
                    "session_id": sid,
                    "teacher_id": teacher_id,
                    "slot_id": slot_id,
                    "message": f"Teacher {teacher_id} is unavailable in slot {slot_id} for session {sid}.",
                })

    # 6. Aggregate teacher conflicts
    for (tid, slot), sids in teacher_slots.items():
        if len(sids) > 1:
            violations.append({
                "type": "teacher_conflict",
                "teacher_id": tid,
                "slot_id": slot,
                "session_ids": sorted(sids),
                "message": f"Teacher {tid} is assigned to multiple sessions {sorted(sids)} in slot {slot}.",
            })

    # 7. Aggregate division conflicts
    for (did, slot), sids in division_slots.items():
        if len(sids) > 1:
            violations.append({
                "type": "division_conflict",
                "division_id": did,
                "slot_id": slot,
                "session_ids": sorted(sids),
                "message": f"Division {did} is assigned to multiple sessions {sorted(sids)} in slot {slot}.",
            })

    # 8. Aggregate room conflicts
    for (rid, slot), sids in room_slots.items():
        if len(sids) > 1:
            violations.append({
                "type": "room_conflict",
                "room_id": rid,
                "slot_id": slot,
                "session_ids": sorted(sids),
                "message": f"Room {rid} is double-booked for sessions {sorted(sids)} in slot {slot}.",
            })

    return violations
