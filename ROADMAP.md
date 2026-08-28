# claude-usage — ROADMAP

**Level `1.0.0`** (`base-repo/83` §3).
**Exit criterion for `2.0.0`, written now:** the tool answers *"what changed
between two periods"* — not just what a single session looked like. That needs
history, and history needs snapshots.

**NEXT TASK:** P1 — snapshot history (one record per session into an external
store). CSV export closed 28.08.2026 (`[1.2.0]`).

## P1
- [ ] Snapshot history: one record per session into an external store, so cost
      trends can be measured over weeks. **Not recoverable retroactively** —
      what is not captured today is gone.
- [ ] Aggregate across sessions: cost per project, per model, per effort level
- [ ] `--since` / `--until` filters

## P2
- [ ] Model comparison from real data: Opus vs Sonnet cache-write volume at
      comparable session length (measured 1.64M vs 6.37M once — needs more points)
- [ ] Effort level as a factor
- [x] **Export to CSV for external analysis — closed 28.08.2026.** `cli.py
      --csv`, stdlib `csv` module, no new dependency. 8 tests on synthetic
      fixtures, verified live against a real session log. `[1.2.0]`

## P3
- [ ] Chart output (matplotlib optional dependency, off by default)
- [ ] Watch mode
