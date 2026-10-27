# claude-usage — ROADMAP

**Level `1.0.0`** (`base-repo/83` §3).
**Exit criterion for `2.0.0`, written now:** the tool answers *"what changed
between two periods"* — not just what a single session looked like. That needs
history, and history needs snapshots.

**NEXT TASK:** P1 — aggregate across sessions (cost per project/model/effort
level), building on `--record`'s history store. CSV export `[1.2.0]` and
snapshot history `[1.3.0]` closed 28.08.2026.

## P1
- [ ] Aggregate across sessions: cost per project, per model, per effort level
- [ ] `--since` / `--until` filters

## P2
- [ ] Model comparison from real data: Opus vs Sonnet cache-write volume at
      comparable session length (measured 1.64M vs 6.37M once — needs more points)
- [ ] Effort level as a factor
      --csv`, stdlib `csv` module, no new dependency. 8 tests on synthetic
      fixtures, verified live against a real session log. `[1.2.0]`

## P3
- [ ] Chart output (matplotlib optional dependency, off by default)
- [ ] Watch mode

## P3 — принято из заметок владельца 27.10.2026 · порядок не назначен

> Слово владельца 27.10.2026: «разнеси это по репам в роадмапы». Приоритет внутри P3 не назначался: порядок выбирает владелец. Исследовательские пункты ставятся учебной целью (стандарт 22 §3а), приёмка — признак работы, а не наличие файла.

- [ ] [зав. 27.10] 🤖 **Дешевле ли другой поставщик Claude (Яндекс Маркет, GGSel, WB)** — оценить числами цену за месяц против официальных планов и API. Отдельным разделом риски перепродажи доступа (бан аккаунта, условия сервиса, передача входа чужому); решение за владельцем. Приёмка: таблица «поставщик → цена → что именно продаётся → риск», официальные тарифы сверены на дату.
