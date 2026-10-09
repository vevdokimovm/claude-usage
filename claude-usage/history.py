"""
Snapshot history (`ROADMAP.md` P1): "not recoverable retroactively — what is
not captured today is gone." Session logs under `~/.claude/projects/` are not
a durable store — they get rotated/pruned, and even while they exist, a
session's own summary changes shape as the session grows. This module
persists one row per session into an external JSONL file, so cost trends
survive log rotation and can be measured over weeks.

Upsert, not append-only: a session gets a NEW row each time `record()` sees
it, keyed by `(session_id, recorded_at)` — the point is a time series of how
a session's cost grew, not a single frozen snapshot. Re-running `record()` on
an unchanged session adds a duplicate reading; that's intentional (a record
means "the state I saw at this moment"), not a bug — callers who only want
the latest state per session should read the last row per `session_id`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .analyze import summarize
from .reader import read_session

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parent.parent / "history" / "sessions.jsonl"

HISTORY_FIELDS = ["recorded_at", "session_id", "project", "model", "turns", "max_context",
                  "cache_read", "cache_creation", "output", "hit_rate", "cost_growth"]


def record(paths: list[Path], history_path: Path | None = None) -> int:
    """Appends one row per session with turns to the history file. Returns how
    many rows were written (sessions with zero turns are skipped — nothing to
    record)."""
    history_path = history_path or DEFAULT_HISTORY_PATH
    history_path.parent.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(timezone.utc).isoformat()

    written = 0
    with history_path.open("a", encoding="utf-8") as f:
        for p in paths:
            s = summarize(read_session(p))
            if not s:
                continue
            model = max(s.models, key=s.models.get)
            row = {
                "recorded_at": recorded_at, "session_id": s.session_id, "project": s.project,
                "model": model, "turns": s.turns, "max_context": s.max_context,
                "cache_read": s.cache_read, "cache_creation": s.cache_creation,
                "output": s.output, "hit_rate": round(s.hit_rate, 1),
                "cost_growth": round(s.cost_growth, 2),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def load_history(history_path: Path | None = None) -> list[dict]:
    history_path = history_path or DEFAULT_HISTORY_PATH
    if not history_path.exists():
        return []
    return [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
