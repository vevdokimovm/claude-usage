#!/usr/bin/env python3
"""
Tests for `cli.py::cmd_csv` — one row per session, machine-readable. Synthetic
fixtures, no network, no real logs (same convention as `test_reader.py`).
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli import CSV_FIELDS, cmd_csv  # noqa: E402

FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  \033[92m✓\033[0m {name}")
    else:
        FAILED.append(name)
        print(f"  \033[91m✗\033[0m {name}  {detail}")


def turn(ts: str, read: int, create: int = 0, out: int = 100,
         model: str = "claude-opus-5") -> dict:
    return {"type": "assistant", "timestamp": ts, "isSidechain": False,
            "version": "2.1.238", "effort": "high",
            "message": {"model": model, "usage": {
                "input_tokens": 2, "cache_read_input_tokens": read,
                "cache_creation_input_tokens": create, "output_tokens": out,
                "output_tokens_details": {"thinking_tokens": out // 3},
                "cache_creation": {"ephemeral_1h_input_tokens": create,
                                   "ephemeral_5m_input_tokens": 0}}}}


def write(records: list[dict]) -> Path:
    d = Path(tempfile.mkdtemp()) / "proj"
    d.mkdir()
    p = d / "sess.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return p


print("\n\033[1mCSV EXPORT\033[0m")

path_a = write([turn("2026-08-21T10:00:00Z", 1000), turn("2026-08-21T10:05:00Z", 2000)])
path_b = write([turn("2026-08-21T11:00:00Z", 500, model="claude-sonnet-5")])

buf = io.StringIO()
with redirect_stdout(buf):
    rc = cmd_csv([path_a, path_b])
check("exits 0", rc == 0)

rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
check("one row per session", len(rows) == 2)
check("header matches CSV_FIELDS", list(rows[0].keys()) == CSV_FIELDS)
check("turns counted correctly", rows[0]["turns"] == "2")
check("model recorded", rows[0]["model"] == "opus-5")  # reader.py strips "claude-" prefix
check("second session's model recorded separately", rows[1]["model"] == "sonnet-5")

buf_empty = io.StringIO()
with redirect_stdout(buf_empty):
    cmd_csv([Path("/nope/none.jsonl")])
rows_empty = list(csv.DictReader(io.StringIO(buf_empty.getvalue())))
check("session with no turns produces no row, only header", len(rows_empty) == 0)
check("header still printed for empty input", buf_empty.getvalue().strip() == ",".join(CSV_FIELDS))

print()
if FAILED:
    print(f"\033[91mFAILED: {len(FAILED)}\033[0m — " + " · ".join(FAILED))
    sys.exit(1)
print("\033[92mall green\033[0m")
