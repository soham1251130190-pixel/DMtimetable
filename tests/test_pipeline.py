"""Tests for Member 3 Timetable Generation Pipeline.

Verifies:
1. Successful end-to-end generation
2. Room assignment integration
3. Constraint verification
4. Soft scoring
5. Local search optimization
6. Final verification
7. Persistence via data provider save_timetable
8. Run ID generation
9. colors_used metric
10. Returned score structure
11. Zero final violations
12. Room assignment failure handling
13. Retry behavior with different seeds
14. All retries failing cleanly (no indefinite loop)
15. Deterministic pipeline generation
16. Small dataset integration
17. Medium dataset integration
18. Impossible dataset failure
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from timetable.backend.core.pipeline import generate_timetable
from timetable.backend.test_support.mock_data import (
    get_small_dataset,
    get_medium_dataset,
    get_impossible_dataset,
)
from timetable.backend.test_support.mock_db import MockDataProvider
from timetable.backend.test_support.mock_coloring import MockColoringProvider


def test_pipeline_successful_generation_small_dataset() -> None:
    """Test full pipeline execution on small dataset."""
    db = MockDataProvider()
    coloring = MockColoringProvider()

    result = generate_timetable(
        data_provider=db,
        coloring_provider=coloring,
        seed=42,
        optimizer_iterations=100,
    )

    # 1. Status is ok
    assert result["status"] == "ok"
    # 2. Run ID generated
    assert result["run_id"].startswith("run_42_")
    # 3. Colors used is positive integer
    assert result["colors_used"] > 0
    # 4. Zero violations
    assert result["violations"] == []
    # 5. Score is returned and non-negative
    assert "total" in result["score"]
    assert result["score"]["total"] >= 0
    # 6. Saved to db provider
    assert result["run_id"] in db.saved_timetables
    saved_rows = db.saved_timetables[result["run_id"]]
    assert len(saved_rows) == len(db.load_sessions())
    # All rows have room and slot
    for row in saved_rows:
        assert row["slot_id"] is not None
        assert row["room_id"] is not None


def test_pipeline_medium_dataset() -> None:
    """Test full pipeline execution on medium dataset (4 divisions, 8 rooms, 10 teachers)."""
    medium_data = get_medium_dataset()
    db = MockDataProvider(
        sessions=medium_data["sessions"],
        rooms=medium_data["rooms"],
        availability=medium_data["availability"],
        timeslots=medium_data["timeslots"],
    )
    coloring = MockColoringProvider()

    result = generate_timetable(
        data_provider=db,
        coloring_provider=coloring,
        seed=100,
        optimizer_iterations=200,
    )

    assert result["status"] == "ok"
    assert result["violations"] == []
    assert result["colors_used"] > 0
    assert result["run_id"] in db.saved_timetables
    saved_rows = db.saved_timetables[result["run_id"]]
    assert len(saved_rows) == len(medium_data["sessions"])


def test_pipeline_retry_behavior() -> None:
    """Test that pipeline catches RoomAssignmentError, retries with new seed/attempt, and succeeds."""
    small_data = get_small_dataset()
    db = MockDataProvider(
        sessions=small_data["sessions"],
        rooms=small_data["rooms"],
        availability=small_data["availability"],
        timeslots=small_data["timeslots"],
    )
    # Configure coloring provider to fail on attempts 0 and 1, then succeed on attempt 2
    coloring = MockColoringProvider(fail_first_n_attempts=2)

    result = generate_timetable(
        data_provider=db,
        coloring_provider=coloring,
        seed=7,
        max_attempts=10,
        optimizer_iterations=50,
    )

    assert result["status"] == "ok"
    assert result["violations"] == []
    # Verify coloring was called 3 times (attempts 0, 1, 2)
    assert len(coloring.call_history) == 3
    assert coloring.call_history[0]["attempt"] == 0
    assert coloring.call_history[1]["attempt"] == 1
    assert coloring.call_history[2]["attempt"] == 2


def test_pipeline_all_retries_fail_impossible_dataset() -> None:
    """Test impossible dataset: all retries fail, returns status='failed', does NOT save to db."""
    imp_data = get_impossible_dataset()
    db = MockDataProvider(
        sessions=imp_data["sessions"],
        rooms=imp_data["rooms"],
        availability=imp_data["availability"],
        timeslots=imp_data["timeslots"],
    )
    # Mock coloring packs sessions into slot 1 on all attempts
    coloring = MockColoringProvider(fail_first_n_attempts=999)

    result = generate_timetable(
        data_provider=db,
        coloring_provider=coloring,
        seed=0,
        max_attempts=5,
        optimizer_iterations=50,
    )

    # Status must be 'failed'
    assert result["status"] == "failed"
    assert "Room assignment failed after 5 attempts" in result["reason"]
    assert len(result["violations"]) > 0
    # Must NOT save invalid timetable
    assert result["run_id"] not in db.saved_timetables
    # Must not loop infinitely, exactly 5 attempts made
    assert len(coloring.call_history) == 5


def test_pipeline_determinism() -> None:
    """Same input and same seed must produce identical timetable and scores."""
    small_data = get_small_dataset()

    db1 = MockDataProvider(
        sessions=small_data["sessions"],
        rooms=small_data["rooms"],
        availability=small_data["availability"],
        timeslots=small_data["timeslots"],
    )
    coloring1 = MockColoringProvider()
    res1 = generate_timetable(data_provider=db1, coloring_provider=coloring1, seed=77, optimizer_iterations=100)

    db2 = MockDataProvider(
        sessions=small_data["sessions"],
        rooms=small_data["rooms"],
        availability=small_data["availability"],
        timeslots=small_data["timeslots"],
    )
    coloring2 = MockColoringProvider()
    res2 = generate_timetable(data_provider=db2, coloring_provider=coloring2, seed=77, optimizer_iterations=100)

    assert res1["status"] == res2["status"] == "ok"
    assert res1["colors_used"] == res2["colors_used"]
    assert res1["score"] == res2["score"]
    assert db1.saved_timetables[res1["run_id"]] == db2.saved_timetables[res2["run_id"]]


if __name__ == "__main__":
    pytest.main([__file__])
