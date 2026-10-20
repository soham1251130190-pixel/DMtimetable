"""API package (compatibility re-export from timetable.backend.api)."""
from timetable.backend.api.main import app, create_app

__all__ = ["app", "create_app"]
