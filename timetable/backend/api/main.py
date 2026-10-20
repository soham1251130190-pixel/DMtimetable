"""FastAPI application for the Smart College Timetable Generator (Member 4)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Smart College Timetable Generator API",
        description="REST API for timetable generation, schedule retrieval, and conflict visualization.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
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
