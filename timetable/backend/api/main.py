"""FastAPI application for the Smart College Timetable Generator (Member 4)."""
import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Smart College Timetable Generator API",
        description="REST API for timetable generation, schedule retrieval, and conflict visualization.",
        version="0.1.0",
    )

    allowed_origins = get_allowed_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["Health"])
    def health_check():
        """Health check endpoint independent of database or scheduling engine."""
        return {"status": "ok"}

    return app


app = create_app()
