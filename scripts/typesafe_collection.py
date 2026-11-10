"""Repository compatibility entry point; the bundle owns the only implementation."""
from pathlib import Path

_source = Path(__file__).resolve().parents[1] / ".apm/skills/core-typesafe/scripts/typesafe_collection.py"
exec(compile(_source.read_bytes(), str(_source), "exec"), globals())
