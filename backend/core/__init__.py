"""Core package (compatibility re-export from timetable.backend.core)."""
from timetable.backend.core.room_assigner import assign_rooms, RoomAssignmentError
from timetable.backend.core.verifier import verify_timetable
from timetable.backend.core.scoring import score_timetable
from timetable.backend.core.optimizer import optimize_timetable
from timetable.backend.core.pipeline import generate_timetable

__all__ = [
    "assign_rooms",
    "RoomAssignmentError",
    "verify_timetable",
    "score_timetable",
    "optimize_timetable",
    "generate_timetable",
]
