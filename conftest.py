import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "timetable"))
sys.path.insert(0, str(ROOT_DIR / "timetable" / "backend"))
