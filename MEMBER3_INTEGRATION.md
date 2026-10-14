# MEMBER 3 INTEGRATION GUIDE: Stage 2 Timetable Generation

This document defines the data contracts, algorithmic guarantees, and integration touchpoints for **Member 3 (Stage 2)** of the Smart College Timetable Generator.

Member 3 operates independently of the eventual database implementation (Member 1) and graph-coloring algorithm (Member 2) using clear interface boundaries.

---

## 1. Data Contracts

### 1.1 Session Structure
Expected dictionary format for each scheduled session:
```python
{
    "session_id": 1,               # int: Unique session identifier
    "subject_id": 101,             # int: Course / Subject ID
    "division_id": 1,              # int: Student division / class group ID
    "teacher_id": 10,              # int: Faculty ID
    "session_no": 1,               # int: 1-indexed lecture occurrence of the week
    "subject_type": "theory",      # str: "theory" (requires classroom) or "lab" (requires lab)
    "elective_group_id": None,     # Optional[int]: None if core course, int if elective group
    "division_strength": 55        # int: Number of students requiring seating
}
```

### 1.2 Room Structure
Expected dictionary format for physical rooms:
```python
{
    "room_id": 1,                  # int: Unique room identifier
    "name": "C101",                # str: Room label / name
    "capacity": 60,                # int: Maximum student capacity
    "room_type": "classroom"       # str: "classroom" or "lab"
}
```

### 1.3 Timeslot Structure
Expected dictionary format for timeslots:
```python
{
    "slot_id": 1,                  # int: Unique timeslot ID
    "day": "Monday",               # str: Day of the week
    "period": 1,                   # int: 1-indexed period index within the day
    "start_time": "09:00",         # str: Optional formatted start time
    "end_time": "10:00"            # str: Optional formatted end time
}
```

### 1.4 Teacher Availability Structure
Can be provided in any of the following flexible formats:
- **Set of unavailable pairs**: `{(teacher_id, slot_id), ...}`
- **Dictionary lookup**: `{(teacher_id, slot_id): bool}`
- **Teacher slot lists**: `{teacher_id: [available_slot_ids, ...]}`
- **Table / List of records**: `[{"teacher_id": 10, "slot_id": 1, "is_available": False}, ...]`
- **Helper object / callable**: Object with `.is_available(teacher_id, slot_id) -> bool` or function `fn(teacher_id, slot_id) -> bool`

### 1.5 Slot Map Structure (Member 2 Contract)
Output provided by Member 2 coloring:
```python
slot_map = {
    session_id: slot_id
}
```

---

## 2. Core Member 3 Function Contracts

### 2.1 `assign_rooms(sessions, slot_map, rooms) -> Dict[int, int]`
- **File**: `timetable/backend/core/room_assigner.py`
- **Algorithm**: Constraint Satisfaction Problem (CSP) solved per slot with:
  - **MRV (Minimum Remaining Values)** heuristic for variable selection
  - **Forward Checking** constraint propagation
- **Domain Constraints**:
  - Room type match: `"theory"` -> `"classroom"`, `"lab"` -> `"lab"`
  - Seating sufficiency: `room["capacity"] >= session["division_strength"]`
  - Hard constraint: No two sessions share a room in the same slot
- **Error Handling**: Raises `RoomAssignmentError(slot_id, affected_session_ids, reason)` on failure.

### 2.2 `verify_timetable(rows, rooms=None, timeslots=None, teacher_availability=None) -> List[Dict]`
- **File**: `timetable/backend/core/verifier.py`
- **Independent Hard Constraint Checker** (never calls CSP solver).
- **Violations Checked**:
  - `teacher_conflict`: Same teacher in multiple sessions in same slot
  - `division_conflict`: Same division in multiple sessions in same slot
  - `room_conflict`: Double-booked room in same slot
  - `room_type`: Incompatible room type
  - `room_capacity`: Room capacity smaller than division strength
  - `teacher_unavailable`: Teacher assigned to unavailable slot
  - `missing_room` / `missing_slot`: Incomplete session scheduling
- **Return**: `[]` if fully valid; list of violation dictionaries if invalid.

### 2.3 `score_timetable(rows, weights=None, timeslots=None) -> Dict`
- **File**: `timetable/backend/core/scoring.py`
- **Soft Constraint Penalty Metrics**:
  - `consecutive`: Excess lectures beyond 3 in a contiguous block per division / teacher (`default weight = 5`)
  - `gap`: Internal idle periods between first and last lecture per division per day (`default weight = 2`)
  - `spread`: More than 1 lecture of the same subject on the same day for a division (`default weight = 3`)
- **Return**:
  ```python
  {
      "total": int,
      "breakdown": {
          "consecutive": int,
          "gap": int,
          "spread": int
      }
  }
  ```

### 2.4 `optimize_timetable(rows, rooms=None, timeslots=None, teacher_availability=None, weights=None, iterations=2000, seed=0) -> List[Dict]`
- **File**: `timetable/backend/core/optimizer.py`
- **Algorithm**: Slot-swap local search. Swaps all sessions in two randomly chosen slots, moving room assignments together.
- **Acceptance Rule**: Accepts strictly if hard constraints pass (`verify_timetable(...) == []`) AND `new_score < current_score`. Never worsens score.

### 2.5 `generate_timetable(conn=None, seed=0, weights=None, data_provider=None, coloring_provider=None, max_attempts=10, optimizer_iterations=1000) -> Dict`
- **File**: `timetable/backend/core/pipeline.py`
- **Pipeline Execution**:
  1. Load data via `data_provider` (or `conn`)
  2. Color conflict graph via `coloring_provider`
  3. Assign rooms via CSP (with retry up to `max_attempts` on `RoomAssignmentError`)
  4. Verify initial hard constraints
  5. Optimize via slot-swap search
  6. Verify final hard constraints
  7. Persist via `data_provider.save_timetable(...)`
- **Return on Success**:
  ```python
  {
      "run_id": str,
      "status": "ok",
      "colors_used": int,
      "score": {"total": int, "breakdown": {...}},
      "violations": []
  }
  ```
- **Return on Failure**:
  ```python
  {
      "run_id": str,
      "status": "failed",
      "reason": str,
      "violations": [...]
  }
  ```

---

## 3. Integration with Teammates

### When Member 1 (Database) Arrives:
Member 1 will provide the database access layer. Replace or adapt the test `MockDataProvider` by supplying a class or connection object that implements:
```python
class ProductionDataProvider:
    def load_sessions(self) -> List[Dict[str, Any]]: ...
    def load_rooms(self) -> List[Dict[str, Any]]: ...
    def load_availability(self) -> Any: ...
    def load_timeslots(self) -> List[Dict[str, Any]]: ...
    def save_timetable(self, run_id: str, timetable_rows: List[Dict[str, Any]]) -> None: ...
```
Then invoke:
```python
generate_timetable(conn=db_connection, data_provider=ProductionDataProvider(db_connection))
```
**No changes to Member 3 algorithms (`room_assigner.py`, `verifier.py`, `scoring.py`, `optimizer.py`) are required.**

### When Member 2 (Graph Coloring) Arrives:
Member 2 will provide the conflict graph builder and DSATUR coloring algorithm. Replace the test `MockColoringProvider` by supplying:
```python
class ProductionColoringProvider:
    def color_graph(self, sessions, timeslots, seed=0, attempt=0, availability=None) -> Dict[int, int]:
        # Member 2's conflict graph construction and DSATUR execution
        return slot_map
```
Then invoke:
```python
generate_timetable(coloring_provider=ProductionColoringProvider())
```
**No changes to Member 3 algorithms are required.**

---

## 4. Verification and Test Suite

Execute the full Member 3 test suite:
```powershell
pytest tests/test_rooms.py
pytest tests/test_verifier.py
pytest tests/test_scoring.py
pytest tests/test_optimizer.py
pytest tests/test_pipeline.py
pytest
```
All 43 tests pass cleanly.
