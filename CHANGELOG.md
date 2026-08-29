# CHANGELOG — claude-usage

## [1.3.4] — 2026-08-29 — Пересборка: архив содержал устаревший канон (PATCH)

### Архив пересобран: в предыдущем лежал устаревший канон

🔴 **Порядок шагов подвёл.** Архивы 62 реп собирались пакетно, а раздача
канона идёт **шестым шагом ритуала базы** — то есть после того, как база
закрыла свой батч. Получилось так:

1. репы получили архивы с каноном `v4.4x`;
2. база закрыла ещё несколько батчей;
3. раздача обновила `_base/` во всех 62 репах;
4. **архивы остались со старым китом**.

Проверено на живом файле: в `acting` после сборки архива изменились
`_base/BASE_FINGERPRINT`, `_base/BASE_VERSION`, `_base/CHANGELOG.md`
и остальной кит.

**Урок:** архив репы-наследника действителен ровно до следующей раздачи.
Пересобирать надо **после** неё, а не до.

Содержание самой репы не менялось — только вложенный канон.

## [1.3.3] — 2026-08-29 — README приведён к стандарту 98 (PATCH)

### README приведён к стандарту `98-readme-standard.md`

Стандарт заведён 29.08.2026 по требованию владельца: *«сделай стандарт README
на основе того, как он сделан у `personal-finance-dss` — там самый подробный —
и сделай у всех других по этому стандарту подробный README»*.

🔴 **Прямо копировать образец нельзя**, и это главное в стандарте: у базы
знаний нет API и быстрого старта. Замер подтвердил различие — `product`
в среднем **165 строк**, `satellite` **69**. Разница не в небрежности:
у продукта больше того, что надо рассказать.

Поэтому общий скелет из семи разделов + разделы по классу репы.

**Что добавлено сборщиком `rebuild_readme.py`** — всё **из написанного
человеком**, ничего не сочинено:

- **«С чего начать»** — только существующие файлы, в порядке чтения;
- **«Что здесь можно узнать»** — из **заголовков документов**: заголовок
  и есть вопрос, на который документ отвечает;
- **«Границы — чего здесь НЕТ»** — предложения `MANIFEST.md` §1 с отрицанием;
- **таблица структуры** — столбец «что внутри по существу» берётся
  из `MANIFEST.md` §3, иначе из заголовков файлов, иначе пишется честно,
  что описания нет.

Прежняя таблица «Repository map» с **пустым столбцом Contents** снята —
это и была та «херня с таблицей», о которой говорил владелец.

**По системе:** медиана README **56 → 77 строк**, у баз знаний 61 → 84.

## [1.3.2] — 2026-08-28 — Закрытые задачи вынесены в историю (PATCH)

Закрытые пункты вынесены в `ROADMAP_HISTORY.md`/`TASKS_HISTORY.md` скриптом
`base-repo/scripts/archive_closed_tasks.py`. Рабочие файлы держат только
открытое — требование владельца 28.08.2026 («чисть выполненные в логи, не
оставляй их внутри»). Формулировки перенесены как есть, вместе с обоснованием
снятия. Опустевшие секции свёрнуты в строку-пойнтер, а не удалены.

Накопление найдено хуком `.claude/hooks/task-hygiene.sh` (`base-repo` [3.100.0]),
он же подтвердил чистоту после: 0 реп с накоплением против 8 до.

## [1.3.1] — 2026-08-28 — README: описание укорочено, «Структура» убрана (PATCH)

Владелец заметил на GitHub, что описание карточки репы обрезается (204
символа при видимом лимите ~175) — укорочено до 174 на GitHub и в
`.repo-meta`. README: убран служебный блок «Структура» (внутренний
артефакт `base-repo`). Заодно исправлено `.repo-meta`: `private=true`
при факте `PUBLIC` на GitHub.

## [1.3.0] — 2026-08-28 — Snapshot history (MINOR)

Закрывает `ROADMAP.md` P1: «Snapshot history» («not recoverable
retroactively» — снималось первым из оставшихся пунктов).

### Added
- `claude_usage/history.py` — `record()`/`load_history()`, append-only
  JSONL в `history/sessions.jsonl`. Не upsert: каждый вызов `--record`
  добавляет новую строку с текущим состоянием сессии — time series роста
  стоимости, не единственный «последний» снимок.
- `cli.py --record` — записать текущие сессии в историю.
- `tests/test_history.py` — 10 assertions.

Проверено вживую: 63 реальные сессии записаны, повторный прогон добавил
ещё 63 (126 строк) — подтверждён append, не перезапись.

## [1.2.0] — 2026-08-28 — CSV-экспорт (MINOR)

Закрывает пункт `BOARD.md`: «Export to CSV for external analysis».

### Added
- `cli.py --csv` — по строке на сессию, в stdout, стандартный `csv`-модуль
  (без новых зависимостей). Поля: session_id, project, model, turns,
  max_context, median_context, growth_per_turn, cache_read, cache_creation,
  fresh_input, output, thinking, hit_rate, cost_growth, sidechain_turns,
  api_errors.
- `tests/test_cli.py` — 8 assertions на синтетических фикстурах, без сети
  и без реальных логов.

Проверено вживую на настоящих логах сессии — корректный CSV с реальными
числами (7351 ход, ~1M токенов контекста и т.д.).

## [1.1.1] — 2026-08-26 — Отчёт о ревизии добавлен (reports/revision-2026-08-26.md) (PATCH)

По заказу владельца — каждой ревизуемой репе отдельный отчёт по шаблону finpilot.

## [1.1.0] — 2026-08-26 — Манифест: описание, теги (публичная репа) (MINOR)

Написан MANIFEST.md, дублей нет.

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
