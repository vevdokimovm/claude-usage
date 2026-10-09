#!/usr/bin/env python3
"""
Tests for `claude-usage/history.py` — synthetic fixtures, temp dir instead of
`history/`, no network, no real logs.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude-usage.history import load_history, record  # noqa: E402

FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  \033[92m✓\033[0m {name}")
    else:
        FAILED.append(name)
        print(f"  \033[91m✗\033[0m {name}  {detail}")


def turn(ts: str, read: int, out: int = 100, model: str = "claude-opus-5") -> dict:
    return {"type": "assistant", "timestamp": ts, "isSidechain": False,
            "version": "2.1.238", "effort": "high",
            "message": {"model": model, "usage": {
                "input_tokens": 2, "cache_read_input_tokens": read,
                "cache_creation_input_tokens": 0, "output_tokens": out,
                "output_tokens_details": {"thinking_tokens": out // 3},
                "cache_creation": {"ephemeral_1h_input_tokens": 0,
                                   "ephemeral_5m_input_tokens": 0}}}}


def write(records: list[dict]) -> Path:
    d = Path(tempfile.mkdtemp()) / "proj"
    d.mkdir()
    p = d / "sess.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return p


print("\n\033[1mSNAPSHOT HISTORY\033[0m")

with tempfile.TemporaryDirectory() as tmp:
    hist_path = Path(tmp) / "sessions.jsonl"

    path_a = write([turn("2026-08-21T10:00:00Z", 1000)])
    written = record([path_a], history_path=hist_path)
    check("one session with turns → one row written", written == 1)
    check("history file created", hist_path.exists())

    rows = load_history(hist_path)
    check("load_history sees the row", len(rows) == 1)
    check("row keys match HISTORY_FIELDS shape", set(rows[0]) == {
        "recorded_at", "session_id", "project", "model", "turns", "max_context",
        "cache_read", "cache_creation", "output", "hit_rate", "cost_growth"})

    empty_session = write([])
    written2 = record([empty_session], history_path=hist_path)
    check("session with zero turns writes nothing", written2 == 0)
    check("no-op record doesn't grow the file", len(load_history(hist_path)) == 1)

    written3 = record([path_a], history_path=hist_path)
    check("re-recording the SAME session appends a new row, not an upsert",
          written3 == 1 and len(load_history(hist_path)) == 2)
    rows_after = load_history(hist_path)
    check("both rows share the same session_id",
          rows_after[0]["session_id"] == rows_after[1]["session_id"])
    check("but have different recorded_at timestamps",
          rows_after[0]["recorded_at"] != rows_after[1]["recorded_at"])

    check("load_history on a missing file returns empty, not an error",
          load_history(Path(tmp) / "nope.jsonl") == [])

print()
if FAILED:
    print(f"\033[91mFAILED: {len(FAILED)}\033[0m — " + " · ".join(FAILED))
    sys.exit(1)
print("\033[92mall green\033[0m")
