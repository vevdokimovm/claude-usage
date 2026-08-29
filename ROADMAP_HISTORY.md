# ROADMAP_HISTORY — закрытое, `claude-usage`

> Куда переезжают выполненные пункты `ROADMAP.md`.
> Формулировки перенесены как есть — вместе с обоснованием
> снятия: у части пунктов ценность именно в нём.

---

## Вынесено 2026-08-28

- [x] **Snapshot history — closed 28.08.2026.** `claude_usage/history.py`,
      `cli.py --record`. Appends (not upserts) one row per session with turns
      to `history/sessions.jsonl` — a time series, not a frozen latest-state
      snapshot. Verified live: 63 real sessions recorded, re-running appended
      63 more (126 rows), not a rewrite. 10 new tests, `tests/test_history.py`.
      `[1.3.0]`
- [x] **Export to CSV for external analysis — closed 28.08.2026.** `cli.py
