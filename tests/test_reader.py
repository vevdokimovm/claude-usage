#!/usr/bin/env python3
"""
Tests on synthetic fixtures. No network, no dependency on anyone's real logs —
a test that needs your ~/.claude to pass is not a test, it is a demo.

Every assertion below corresponds to a trap named in reader.py. The traps are
the reason this project exists: each one silently corrupts statistics and each
one produces plausible-looking numbers, which is why they survive review.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_usage.analyze import limit_state, summarize, turn_cost   # noqa: E402
from claude_usage.reader import Turn, read_session                   # noqa: E402

FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  \033[92m✓\033[0m {name}")
    else:
        FAILED.append(name)
        print(f"  \033[91m✗\033[0m {name}  {detail}")


def turn(ts: str, read: int, create: int = 0, out: int = 100, sidechain: bool = False,
         model: str = "claude-opus-5") -> dict:
    return {"type": "assistant", "timestamp": ts, "isSidechain": sidechain,
            "version": "2.1.238", "effort": "high",
            "message": {"model": model, "usage": {
                "input_tokens": 2, "cache_read_input_tokens": read,
                "cache_creation_input_tokens": create, "output_tokens": out,
                "output_tokens_details": {"thinking_tokens": out // 3},
                "cache_creation": {"ephemeral_1h_input_tokens": create,
                                   "ephemeral_5m_input_tokens": 0}}}}


def rejection(ts: str, resets_at: int, window: str = "five_hour") -> dict:
    """A refusal. Note it carries type=assistant AND usage — that is the trap."""
    return {"type": "assistant", "timestamp": ts, "isApiErrorMessage": True,
            "quotaLimits": {"status": "rejected", "resetsAt": resets_at,
                            "rateLimitType": window, "overageStatus": "rejected",
                            "overageDisabledReason": "org_level_disabled"},
            "message": {"model": "claude-opus-5", "usage": {
                "input_tokens": 0, "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0, "output_tokens": 0}}}


def write(records: list[dict]) -> Path:
    d = Path(tempfile.mkdtemp()) / "proj"
    d.mkdir()
    p = d / "sess.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return p


print("\n\033[1mTRAP 1 — a refusal looks like a successful turn\033[0m")
s = read_session(write([
    turn("2026-08-21T10:00:00Z", 1000),
    rejection("2026-08-21T10:05:00Z", 1787332200),
    turn("2026-08-21T10:10:00Z", 2000),
]))
check("refusal is NOT counted as a turn", len(s.turns) == 2, f"got {len(s.turns)}")
check("refusal is captured separately", len(s.rejections) == 1)
check("refusal counted as an API error", s.api_errors == 1)
check("resets_at read as a unix timestamp", s.rejections[0].resets_at == 1787332200)
check("window type preserved", s.rejections[0].window == "five_hour")

print("\n\033[1mTRAP 2 — a refusal is not a block until resets_at\033[0m")
far_future = 4102444800          # 2100-01-01, deliberately beyond any clock skew
s = read_session(write([
    turn("2026-08-21T10:00:00Z", 1000),
    rejection("2026-08-21T10:05:00Z", far_future),
    turn("2026-08-21T10:10:00Z", 2000),          # success AFTER the refusal
]))
st = limit_state(s)["five_hour"]
check("reset time is still in the future", st["seconds_left"] > 0)
check("but the refusal is marked cleared", st["cleared_by_later_success"] is True)
check("so we are NOT reported as blocked", st["possibly_blocked"] is False)

s2 = read_session(write([
    turn("2026-08-21T10:00:00Z", 1000),
    rejection("2026-08-21T10:05:00Z", far_future),   # nothing succeeds after it
]))
st2 = limit_state(s2)["five_hour"]
check("no later success → possibly blocked", st2["possibly_blocked"] is True)
check("overage refusal is surfaced", st2["overage"] == "rejected")

print("\n\033[1mTRAP 3 — sub-agent spend is absent, and that is reported\033[0m")
s = read_session(write([
    turn("2026-08-21T10:00:00Z", 1000),
    turn("2026-08-21T10:01:00Z", 1500, sidechain=True),
]))
check("sidechain turn not mixed into main thread", len(s.turns) == 1)
check("but it is counted separately", s.sidechain_turns == 1)

print("\n\033[1mCONTEXT AND COST\033[0m")
s = read_session(write([turn(f"2026-08-21T10:{i:02d}:00Z", 1000 * (i + 1)) for i in range(10)]))
summ = summarize(s)
check("context = input + read + creation", s.turns[0].context == 2 + 1000)
check("growth per turn is positive", summ.growth_per_turn > 0)
check("peak is the largest context", summ.max_context == 2 + 10000)
check("hit rate is 100% with no writes", summ.hit_rate == 100.0)
# turn() above builds a raw log RECORD; turn_cost takes a parsed Turn.
# Mixing them is exactly the kind of quiet type confusion the tests exist for.
_mk = lambda read, out: Turn(ts="t", model="m", effort=None, input=0,
                             cache_read=read, cache_creation=0, output=out,
                             thinking=0, ttl_1h=0, ttl_5m=0)
check("cached read is cheaper than the same volume of fresh output",
      turn_cost(_mk(1000, 0)) < turn_cost(_mk(0, 1000)))
check("a cache WRITE is the most expensive of all",
      turn_cost(Turn("t", "m", None, 0, 0, 1000, 0, 0, 0, 0)) > turn_cost(_mk(0, 1000)))

print("\n\033[1mCONTEXT DROPS\033[0m")
s = read_session(write([
    turn("2026-08-21T10:00:00Z", 200_000),
    turn("2026-08-21T10:01:00Z", 5_000),          # halved and then some
    turn("2026-08-21T10:02:00Z", 6_000),
]))
check("a drop is detected", len(summarize(s).drops) == 1)
s = read_session(write([turn(f"2026-08-21T10:{i:02d}:00Z", 100_000 + i) for i in range(3)]))
check("steady context reports no drops", len(summarize(s).drops) == 0)

print("\n\033[1mEDGE CASES\033[0m")
check("empty log summarizes to None", summarize(read_session(write([]))) is None)
p = write([turn("2026-08-21T10:00:00Z", 100)])
# The broken line must look RELEVANT, otherwise the cheap prefilter skips it
# before json.loads ever runs. First version of this test used "{ broken json",
# which carries no "usage" key — it was skipped, bad_lines stayed 0, and the
# test failed for a reason that had nothing to do with error handling.
p.write_text(p.read_text(encoding="utf-8") + '\n{"usage": broken', encoding="utf-8")
s = read_session(p)
check("malformed relevant line counted, not fatal", s.bad_lines == 1 and len(s.turns) == 1,
      f"bad_lines={s.bad_lines} turns={len(s.turns)}")
p.write_text(p.read_text(encoding="utf-8") + "\nnot json at all\n", encoding="utf-8")
check("irrelevant garbage is skipped without counting", read_session(p).bad_lines == 1)
check("missing file yields empty session", read_session(Path("/nope/none.jsonl")).turns == [])

print()
if FAILED:
    print(f"\033[91mFAILED: {len(FAILED)}\033[0m — " + " · ".join(FAILED))
    sys.exit(1)
print("\033[92mall green\033[0m")
