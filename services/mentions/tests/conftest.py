import os
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.pop("INTERNAL_TOKEN", None)
