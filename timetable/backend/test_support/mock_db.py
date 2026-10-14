"""TEST ONLY - MOCK MEMBER 1 INTERFACE

This module provides a mock data provider mimicking Member 1's eventual database layer.
It allows Member 3 to develop and run comprehensive tests independently.
When Member 1 provides their real database/ORM implementation, this mock will be replaced
or adapted without changing any Member 3 core algorithms.
"""

from typing import Any, Dict, List, Optional
from .mock_data import get_small_dataset


class MockDataProvider:
    """Mock database access provider conforming to Member 1 contract."""

    def __init__(
        self,
        sessions: Optional[List[Dict[str, Any]]] = None,
        rooms: Optional[List[Dict[str, Any]]] = None,
        availability: Any = None,
        timeslots: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Initialize mock data provider with explicit or default fixture data."""
        if sessions is None or rooms is None or timeslots is None:
            default_data = get_small_dataset()
            self._sessions = sessions if sessions is not None else default_data["sessions"]
            self._rooms = rooms if rooms is not None else default_data["rooms"]
            self._availability = (
                availability if availability is not None else default_data["availability"]
            )
            self._timeslots = timeslots if timeslots is not None else default_data["timeslots"]
        else:
            self._sessions = sessions
            self._rooms = rooms
            self._availability = availability if availability is not None else set()
            self._timeslots = timeslots

        # Storage for saved timetables: {run_id: rows}
        self.saved_timetables: Dict[str, List[Dict[str, Any]]] = {}

    def load_sessions(self) -> List[Dict[str, Any]]:
        """Load scheduled session definitions from mock database."""
        return [dict(s) for s in self._sessions]

    def load_rooms(self) -> List[Dict[str, Any]]:
        """Load physical room definitions from mock database."""
        return [dict(r) for r in self._rooms]

    def load_availability(self) -> Any:
        """Load teacher availability constraints from mock database."""
        if isinstance(self._availability, set):
            return set(self._availability)
        if isinstance(self._availability, dict):
            return dict(self._availability)
        if isinstance(self._availability, list):
            return [dict(x) if isinstance(x, dict) else x for x in self._availability]
        return self._availability

    def load_timeslots(self) -> List[Dict[str, Any]]:
        """Load timeslot definitions from mock database."""
        return [dict(t) for t in self._timeslots]

    def save_timetable(self, run_id: str, timetable_rows: List[Dict[str, Any]]) -> None:
        """Persist generated timetable rows to mock database."""
        self.saved_timetables[run_id] = [dict(r) for r in timetable_rows]
