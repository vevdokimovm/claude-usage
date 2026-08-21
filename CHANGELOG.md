# CHANGELOG — claude-usage

## [1.0.0] — 2026-08-21 — MVP: three format traps, measured and tested (MINOR)

Level `1.0.0` per `base-repo/00-infrastructure/83-project-maturity-levels.md` §3:
runs on real logs with one command, 22 tests on fixtures, ceiling stated in README.

### Added
- `claude_usage/reader.py` — everything the project knows about the raw JSONL
  format, so the rest sees clean dataclasses.
- `claude_usage/analyze.py` — context growth, cost buckets, cache split,
  limit windows. No I/O, testable on fixtures.
- `cli.py` — one entry point: session, `--all`, `--limits`, `--json`, `--list`.
- 22 tests on synthetic fixtures, no network.

### The three traps this exists for
1. **A refusal looks like a successful turn** — `type: assistant` with `usage`.
   Counting it inflates turns and skews average cost.
2. **A refusal is not a block until `resetsAt`** — 149 successful turns were
   observed after one. Blocked-or-not is decided by a later success, not a clock.
3. **Sub-agent spend is absent from the parent log** — ~191k tokens with zero
   `isSidechain` records. Printed with an explanation, not as a bare zero.

All three were found by reading output against reality, not by tests.
Each now has one.
