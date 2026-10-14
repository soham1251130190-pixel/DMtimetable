"""Member 3 Core Package.

This package contains Stage 2 of the Timetable Generator:
- room_assigner: Room CSP assignment using MRV and forward checking
- verifier: Independent hard constraint validator
- scoring: Soft constraint penalty scorer
- optimizer: Slot-swap local search optimizer
- pipeline: End-to-end timetable generation coordinator
"""

from .room_assigner import assign_rooms, RoomAssignmentError
from .verifier import verify_timetable
from .scoring import score_timetable
from .optimizer import optimize_timetable
from .pipeline import generate_timetable

__all__ = [
    "assign_rooms",
    "RoomAssignmentError",
    "verify_timetable",
    "score_timetable",
    "optimize_timetable",
    "generate_timetable",
]
