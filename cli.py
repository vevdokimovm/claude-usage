#!/usr/bin/env python3
"""
claude-usage — where your Claude Code budget actually goes.

    python3 cli.py                      # newest session in the current project
    python3 cli.py --list               # what sessions exist
    python3 cli.py --all                # every session, one line each
    python3 cli.py --limits             # rate-limit windows across all logs
    python3 cli.py --json               # machine-readable
    python3 cli.py path/to/session.jsonl

No dependencies. Nothing leaves your machine.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path

from claude_usage.analyze import BUCKET, COST, summarize
from claude_usage.reader import find_sessions, read_session

C = {"h": "\033[96m", "g": "\033[92m", "y": "\033[93m", "r": "\033[91m",
     "b": "\033[1m", "d": "\033[90m", "x": "\033[0m"}


def c(t: str, k: str = "h") -> str:
    return f"{C[k]}{t}{C['x']}"


def n(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def pick(args) -> list[Path]:
    if args.path:
        return [Path(args.path).expanduser()]
    found = list(find_sessions(project=args.project))
    if not found:
        return []
    return found if (args.all or args.csv or args.limits or args.list) else found[:1]


def cmd_list(paths: list[Path]) -> int:
    print(c("SESSIONS", "b"))
    print(f"  {'project':<40}{'session':<14}{'size':>9}  modified")
    for p in paths[:40]:
        mt = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m %H:%M")
        print(f"  {p.parent.name[:39]:<40}{p.stem[:12]:<14}"
              f"{p.stat().st_size // 1024:>7} KB  {mt}")
    if len(paths) > 40:
        print(c(f"  … and {len(paths) - 40} more", "d"))
    return 0


def cmd_limits(paths: list[Path]) -> int:
    print(c("RATE LIMITS — from quotaLimits records in the logs\n", "b"))
    windows: dict[str, dict] = {}
    total = 0
    for p in paths:
        s = read_session(p)
        total += len(s.rejections)
        for w, st in summarize(s).limits.items() if s.turns else []:
            if w not in windows or st["resets_at"] > windows[w]["resets_at"]:
                windows[w] = st
    if not total:
        print("  No rate-limit rejections in any log.")
        print(c("  This does NOT mean you are far from the limit — it means you", "d"))
        print(c("  have not been refused yet. The record only appears on refusal.", "d"))
        return 0
    print(f"  rejections recorded: {total}\n")
    for w, st in sorted(windows.items()):
        if st["cleared_by_later_success"]:
            mark = c("cleared — successful turns came after it", "g")
        elif st["possibly_blocked"]:
            m = st["seconds_left"] // 60
            mark = c(f"possibly blocked · {m // 60}h {m % 60}m until reset", "r")
        else:
            mark = c("window reset by time", "g")
        print(f"  {w:<12} {mark}")
        print(f"     last refusal : {st['hit_at']}")
        print(f"     resets at    : {st['resets_local']}   (unix {st['resets_at']})")
        if st.get("overage") == "rejected":
            print(c("     overage      : rejected — work STOPS, it does not continue paid", "y"))
    print()
    print(c("  Note: a refusal does not mean you were blocked until the reset time.", "d"))
    print(c("  In a real log, 149 successful turns followed a refusal whose stated", "d"))
    print(c("  reset had not yet arrived. Blocked-or-not is decided by a later", "d"))
    print(c("  successful turn, never by comparing clocks.", "d"))
    return 0


def one_line(p: Path) -> str | None:
    s = summarize(read_session(p))
    if not s:
        return None
    model = max(s.models, key=s.models.get)
    return (f"  {s.project[:30]:<31}{model[:14]:<15}{s.turns:>6}"
            f"{n(s.max_context):>12}{s.hit_rate:>8.1f}%{s.cost_growth:>8.1f}x")


def cmd_all(paths: list[Path]) -> int:
    print(c("ALL SESSIONS\n", "b"))
    print(f"  {'project':<31}{'model':<15}{'turns':>6}{'max ctx':>12}"
          f"{'hit':>9}{'cost↑':>8}")
    rows = [r for r in (one_line(p) for p in paths) if r]
    for r in rows:
        print(r)
    print(f"\n  {len(rows)} sessions with turns")
    print(c(f"  cost↑ = how much more a turn costs at the top of its context range "
            f"than at the bottom", "d"))
    return 0


CSV_FIELDS = ["session_id", "project", "model", "turns", "max_context", "median_context",
              "growth_per_turn", "cache_read", "cache_creation", "fresh_input", "output",
              "thinking", "hit_rate", "cost_growth", "sidechain_turns", "api_errors"]


def cmd_csv(paths: list[Path]) -> int:
    """One row per session — for external analysis (spreadsheet, pandas, whatever).
    Dict/list-typed fields (models per turn, buckets, drops, limits) don't fit a flat
    row; `model` here is whichever model saw the most turns, matching `--all`."""
    writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for p in paths:
        s = summarize(read_session(p))
        if not s:
            continue
        model = max(s.models, key=s.models.get)
        writer.writerow({
            "session_id": s.session_id, "project": s.project, "model": model,
            "turns": s.turns, "max_context": s.max_context,
            "median_context": s.median_context, "growth_per_turn": round(s.growth_per_turn),
            "cache_read": s.cache_read, "cache_creation": s.cache_creation,
            "fresh_input": s.fresh_input, "output": s.output, "thinking": s.thinking,
            "hit_rate": round(s.hit_rate, 1), "cost_growth": round(s.cost_growth, 2),
            "sidechain_turns": s.sidechain_turns, "api_errors": s.api_errors,
        })
    return 0


def cmd_one(path: Path, as_json: bool) -> int:
    s = read_session(path)
    summ = summarize(s)
    if not summ:
        print(c(f"no turns with usage in {path.name} — is this a session log?", "r"),
              file=sys.stderr)
        return 1
    if as_json:
        d = dict(summ.__dict__)
        d["buckets"] = [b.__dict__ for b in summ.buckets]
        d["cost_model"] = COST
        print(json.dumps(d, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"{c('SESSION', 'b')} {summ.session_id}")
    print(f"  project      {summ.project}")
    print(f"  CLI          {', '.join(summ.cli_versions) or '—'}")
    print(f"  model        {', '.join(f'{k} x{v}' for k, v in sorted(summ.models.items(), key=lambda x: -x[1]))}")
    print(f"  effort       {', '.join(f'{k} x{v}' for k, v in summ.efforts.items()) or 'not recorded'}")

    print(f"\n{c('CONTEXT', 'b')}")
    print(f"  turns        {summ.turns}")
    print(f"  peak         {n(summ.max_context)}   median {n(summ.median_context)}")
    print(f"  growth       {summ.growth_per_turn:+.0f} tokens per turn")
    if summ.drops:
        print(c(f"  drops        {len(summ.drops)} — context more than halved", "y"))
        for turn_no, before, after in summ.drops[:5]:
            print(f"     turn {turn_no}: {n(before)} → {n(after)}")
        print(c("     auto-compact and a session restart look identical here.", "d"))
    else:
        print(c("  drops        none — the peak above is a floor for this session's ceiling", "g"))

    print(f"\n{c('CACHE', 'b')}")
    print(f"  read         {n(summ.cache_read)}")
    print(f"  written      {n(summ.cache_creation)}")
    print(f"  hit rate     {summ.hit_rate:.1f}%")
    ttl = "1h" if summ.ttl_1h >= summ.ttl_5m else "5m"
    print(f"  write TTL    1h {n(summ.ttl_1h)} · 5m {n(summ.ttl_5m)}"
          + (c("   (cheap mode)", "g") if ttl == "1h" else c("   (short TTL)", "y")))
    print(c("  Hit rate is the number everyone quotes and the least useful one:", "d"))
    print(c("  what you pay for is BYTES WRITTEN to cache, not the ratio.", "d"))

    print(f"\n{c('OUTPUT', 'b')}")
    pct = (summ.thinking / summ.output * 100) if summ.output else 0
    print(f"  tokens       {n(summ.output)}   thinking {n(summ.thinking)} ({pct:.0f}%)")
    print(f"  fresh input  {n(summ.fresh_input)}   (everything else arrived via cache)")

    print(f"\n{c('COST PER TURN', 'b')}  buckets of {BUCKET // 1000}K context")
    print(c(f"  weights: {COST}", "d"))
    print(f"  {'context':>12}{'turns':>7}{'cost':>12}{'cache_read':>13}")
    for b in summ.buckets:
        print(f"  {n(b.floor):>12}{b.turns:>7}{n(b.avg_cost):>12}{n(b.avg_cache_read):>13}")
    if len(summ.buckets) > 1:
        print(f"  {c('→', 'y')} a turn at {n(summ.buckets[-1].floor)} costs "
              f"{c(f'{summ.cost_growth:.1f}x', 'y')} what it costs at {n(summ.buckets[0].floor)}")
        print(c("    Cost is dominated by cache_read, and cache_read equals the size", "d"))
        print(c("    of your context. The growth is linear by construction.", "d"))

    print(f"\n{c('WHAT THIS CANNOT TELL YOU', 'b')}")
    print(f"  sub-agent turns in this log: {summ.sidechain_turns}")
    if not summ.sidechain_turns:
        print(c("  Zero does NOT mean sub-agents were free or absent. Their spend is", "r"))
        print(c("  not written to the parent log at all — measured: ~191k tokens of", "r"))
        print(c("  sub-agent work with zero isSidechain records. Measuring delegation", "r"))
        print(c("  needs their own logs or --forward-subagent-text.", "r"))
    print(f"  API error records skipped: {summ.api_errors}")
    print(c("  A rate-limit refusal carries type=assistant AND usage — it looks like", "d"))
    print(c("  a successful turn. Counting it would inflate turns and skew avg cost.", "d"))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Where your Claude Code budget goes")
    p.add_argument("path", nargs="?", help="specific .jsonl session log")
    p.add_argument("--project", help="filter sessions by project directory name")
    p.add_argument("--list", action="store_true", help="list available sessions")
    p.add_argument("--all", action="store_true", help="one line per session")
    p.add_argument("--csv", action="store_true", help="one CSV row per session, to stdout")
    p.add_argument("--limits", action="store_true", help="rate-limit windows")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    a = p.parse_args()

    paths = pick(a)
    if not paths:
        print(c("No session logs found under ~/.claude/projects/", "r"), file=sys.stderr)
        return 1
    if a.list:
        return cmd_list(paths)
    if a.limits:
        return cmd_limits(paths)
    if a.csv:
        return cmd_csv(paths)
    if a.all:
        return cmd_all(paths)
    return cmd_one(paths[0], a.json)


if __name__ == "__main__":
    sys.exit(main())
