"""FastAPI application for the Smart College Timetable Generator (Member 4).

Provides endpoints for:
- Health check
- Available academic datasets
- Timetable retrieval (latest verified schedule from SQLite)
- Course conflict network serialization (for React Flow visualization)
- Timetable generation triggering (coordinated with Member 2 & 3 pipeline)
"""
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is at the front of sys.path to disambiguate root core (Member 2) from timetable/backend/core (Member 3)
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path or sys.path[0] != str(REPO_ROOT):
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import timetable.backend.db.config as cfg
import timetable.backend.db.db as dal
from core.graph_builder import build_conflict_graph, graph_statistics
from timetable.backend.core.pipeline import generate_timetable
from timetable.backend.core.scoring import score_timetable
from timetable.backend.core.verifier import verify_timetable

# Global thread lock to prevent concurrent generation race conditions
_generation_lock = threading.Lock()


def get_allowed_origins() -> List[str]:
    """Resolve allowed CORS origins for local development and deployed frontend."""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # Read production frontend origin(s) from environment variable
    frontend_origin = os.getenv("FRONTEND_ORIGIN")
    if frontend_origin:
        for item in frontend_origin.split(","):
            cleaned = item.strip().rstrip("/")
            if cleaned and cleaned not in origins:
                origins.append(cleaned)
    return origins


def get_db_path(dataset: Optional[str] = None) -> Path:
    """Resolve the SQLite database path based on environment or dataset parameter."""
    # Allow overriding default DB via environment variable for Render persistent disk
    env_db = os.getenv("TIMETABLE_DB_PATH")
    if env_db and (not dataset or dataset in ("default", "main")):
        return Path(env_db).resolve()

    if not dataset or dataset in ("default", "main", "medium"):
        return cfg.DEFAULT_DB

    clean_name = dataset.strip().lower()
    if clean_name in cfg.DATASET_NAMES:
        return cfg.DATA_DIR / f"{clean_name}.db"

    raise HTTPException(
        status_code=400,
        detail=f"Unknown dataset '{dataset}'. Supported datasets: default, {', '.join(cfg.DATASET_NAMES)}",
    )


class GenerateRequest(BaseModel):
    """Configuration options for timetable generation."""

    dataset: Optional[str] = Field(
        default="default",
        description="Dataset scope to schedule: 'default', 'small', 'medium', 'stress', 'impossible'",
    )
    seed: Optional[int] = Field(
        default=42,
        description="Random seed for deterministic generation and local search optimization",
    )
    max_attempts: Optional[int] = Field(
        default=10,
        description="Maximum retry attempts for coloring and room allocation solver stages",
    )
    optimizer_iterations: Optional[int] = Field(
        default=500,
        description="Number of slot-swap iterations for soft constraint optimization",
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Smart College Timetable Generator API",
        description="REST API for timetable generation, schedule retrieval, and conflict visualization.",
        version="0.2.0",
    )

    allowed_origins = get_allowed_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    def root():
        """Root landing endpoint for browser visits."""
        return {
            "name": "Smart College Timetable Generator API",
            "version": "0.2.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    @app.get("/api/health", tags=["Health"])
    def health_check():
        """Health check endpoint independent of database or scheduling engine."""
        return {"status": "ok"}

    @app.get("/api/datasets", tags=["Academic Scope"])
    def list_datasets():
        """List supported academic dataset options for scheduling."""
        return {
            "datasets": [
                {
                    "id": "default",
                    "name": "Standard College Schedule (Medium — 72 Sessions, 4 Divisions)",
                    "is_default": True,
                },
                {
                    "id": "small",
                    "name": "Department Sample (Small — 16 Sessions, 2 Divisions)",
                    "is_default": False,
                },
                {
                    "id": "stress",
                    "name": "Multi-Department Benchmark (Stress — 261 Sessions)",
                    "is_default": False,
                },
                {
                    "id": "impossible",
                    "name": "Over-Constrained Test Case (Demonstrates Failure Handling)",
                    "is_default": False,
                },
            ]
        }

    @app.get("/api/timetable/latest", tags=["Timetable"])
    def get_latest_timetable(
        dataset: Optional[str] = Query(None, description="Dataset scope (e.g., small, medium, stress)"),
        division_id: Optional[int] = Query(None, description="Optional division ID filter"),
        teacher_id: Optional[int] = Query(None, description="Optional teacher ID filter"),
    ):
        """Retrieve the latest verified timetable from the SQLite database."""
        db_path = get_db_path(dataset)
        if not db_path.exists():
            raise HTTPException(status_code=404, detail=f"Database file not found at {db_path.name}")

        conn = dal.connect(db_path)
        try:
            divisions = dal.load_divisions(conn)
            teachers = dal.load_teachers(conn)
            rooms = dal.load_rooms(conn)
            timeslots = dal.load_timeslots(conn)
            availability = dal.load_availability(conn)

            runs = dal.list_runs(conn)
            # Find the most recent run with completed/sample status
            valid_runs = [r for r in runs if r.get("status") in ("completed", "sample", "ok")]

            if not valid_runs:
                return {
                    "status": "empty",
                    "message": "No scheduled timetable found in the selected database. Generate a new timetable to populate.",
                    "run_id": None,
                    "dataset": dataset or "default",
                    "created_at": None,
                    "colors_used": 0,
                    "total_sessions": 0,
                    "score": None,
                    "violations": [],
                    "divisions": divisions,
                    "teachers": teachers,
                    "rooms": rooms,
                    "timeslots": timeslots,
                    "rows": [],
                }

            latest_run = valid_runs[-1]
            run_id = latest_run["run_id"]

            all_rows = dal.get_timetable(conn, run_id)
            filtered_rows = dal.get_timetable(conn, run_id, division_id=division_id, teacher_id=teacher_id)

            # Verify hard constraints across full schedule
            violations = verify_timetable(
                all_rows,
                rooms=rooms,
                timeslots=timeslots,
                teacher_availability=availability,
            )

            # Score schedule soft constraints
            score = score_timetable(all_rows, timeslots=timeslots)

            colors_used = latest_run.get("colors_used") or len(set(r["slot_id"] for r in all_rows))

            return {
                "status": latest_run.get("status", "completed"),
                "run_id": run_id,
                "dataset": dataset or "default",
                "created_at": latest_run.get("created_at"),
                "colors_used": colors_used,
                "total_sessions": len(all_rows),
                "score": score,
                "violations": violations,
                "divisions": divisions,
                "teachers": teachers,
                "rooms": rooms,
                "timeslots": timeslots,
                "rows": filtered_rows,
            }
        finally:
            conn.close()

    @app.get("/api/graph", tags=["Conflict Graph"])
    def get_conflict_graph(
        dataset: Optional[str] = Query(None, description="Dataset scope (e.g., small, medium, stress)")
    ):
        """Build and serialize the session conflict network formatted for React Flow visualization."""
        db_path = get_db_path(dataset)
        if not db_path.exists():
            raise HTTPException(status_code=404, detail=f"Database file not found at {db_path.name}")

        conn = dal.connect(db_path)
        try:
            sessions = dal.load_sessions(conn)
            divisions = dal.load_divisions(conn)
            teachers = dal.load_teachers(conn)

            G = build_conflict_graph(sessions)
            stats = graph_statistics(G)

            # Lookup latest timetable rows to annotate graph nodes with assigned timeslots
            runs = dal.list_runs(conn)
            valid_runs = [r for r in runs if r.get("status") in ("completed", "sample", "ok")]
            tt_map = {}
            if valid_runs:
                tt_rows = dal.get_timetable(conn, valid_runs[-1]["run_id"])
                tt_map = {r["session_id"]: r for r in tt_rows}

            div_order = {d["division_id"]: idx for idx, d in enumerate(divisions)}
            div_names = {d["division_id"]: d["name"] for d in divisions}
            teacher_names = {t["teacher_id"]: t["name"] for t in teachers}
            sessions_dict = {s["session_id"]: s for s in sessions}

            div_counters: Dict[int, int] = {}
            nodes = []

            for node_id in sorted(G.nodes):
                session_data = sessions_dict.get(node_id, {})
                row_info = tt_map.get(node_id, {})

                div_id = session_data.get("division_id") or row_info.get("division_id", 1)
                col_idx = div_order.get(div_id, 0)
                row_idx = div_counters.get(div_id, 0)
                div_counters[div_id] = row_idx + 1

                # Layout: separate column for each class division with consistent spacing
                x = 80 + col_idx * 380
                y = 80 + row_idx * 190

                sub_code = row_info.get("subject_code") or session_data.get("subject_code", f"S{node_id}")
                div_name = row_info.get("division_name") or div_names.get(div_id, f"Class {div_id}")
                teacher_id = row_info.get("teacher_id") or session_data.get("teacher_id")
                teacher_name = row_info.get("teacher_name") or teacher_names.get(teacher_id, "Faculty")

                nodes.append(
                    {
                        "id": str(node_id),
                        "type": "default",
                        "position": {"x": x, "y": y},
                        "data": {
                            "sessionId": node_id,
                            "label": f"{sub_code} ({div_name})",
                            "subjectCode": sub_code,
                            "subjectName": row_info.get("subject_name")
                            or session_data.get("subject_name", "Academic Course"),
                            "subjectType": row_info.get("subject_type")
                            or session_data.get("subject_type", "theory"),
                            "divisionId": div_id,
                            "divisionName": div_name,
                            "teacherId": teacher_id,
                            "teacherName": teacher_name,
                            "slotId": row_info.get("slot_id"),
                            "day": row_info.get("day"),
                            "period": row_info.get("period"),
                            "startTime": row_info.get("start_time"),
                            "endTime": row_info.get("end_time"),
                            "roomName": row_info.get("room_name"),
                        },
                    }
                )

            edges = []
            for u, v, data in G.edges(data=True):
                reasons = data.get("reasons", [])
                label = " & ".join(r.capitalize() for r in reasons)
                edges.append(
                    {
                        "id": f"e{u}-{v}",
                        "source": str(u),
                        "target": str(v),
                        "label": label,
                        "data": {"reasons": reasons},
                    }
                )

            return {
                "metadata": {
                    "dataset": dataset or "default",
                    "total_nodes": stats["nodes"],
                    "total_edges": stats["edges"],
                    "density": round(stats["density"], 4),
                    "max_degree": stats["max_degree"],
                    "connected_components": stats["connected_components"],
                    "color_lower_bound": stats["color_lower_bound"],
                    "description": "Course conflict network representing simultaneous scheduling constraints across faculty and student divisions.",
                },
                "nodes": nodes,
                "edges": edges,
            }
        finally:
            conn.close()

    @app.post("/api/generate", tags=["Timetable Generation"])
    def generate(req: Optional[GenerateRequest] = None):
        """Trigger the complete timetable generation pipeline and persist results to SQLite."""
        if req is None:
            req = GenerateRequest()

        db_path = get_db_path(req.dataset)
        if not db_path.exists():
            raise HTTPException(status_code=404, detail=f"Database file not found at {db_path.name}")

        # Guard against concurrent duplicate generation processes
        if not _generation_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409,
                detail="A timetable generation process is already in progress. Please wait for it to complete.",
            )

        try:
            conn = dal.connect(db_path)
            try:
                result = generate_timetable(
                    conn=conn,
                    seed=req.seed,
                    max_attempts=req.max_attempts,
                    optimizer_iterations=req.optimizer_iterations,
                )
            finally:
                conn.close()
        finally:
            _generation_lock.release()

        if result.get("status") != "ok":
            return JSONResponse(
                status_code=422,
                content={
                    "status": "failed",
                    "message": result.get(
                        "reason",
                        "Unable to produce a valid schedule satisfying all hard constraints.",
                    ),
                    "run_id": result.get("run_id"),
                    "violations": result.get("violations", []),
                    "dataset": req.dataset,
                },
            )

        return {
            "status": "ok",
            "message": "Timetable successfully generated, verified, and saved to database.",
            "run_id": result.get("run_id"),
            "colors_used": result.get("colors_used"),
            "score": result.get("score"),
            "violations": result.get("violations", []),
            "dataset": req.dataset,
        }

    return app


app = create_app()
