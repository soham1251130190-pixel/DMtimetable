import sys
from pathlib import Path

# make `from db import ...` work: backend/ must be on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
