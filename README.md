# claude-usage

**Where your Claude Code budget actually goes.** Reads the session logs already on
your disk (`~/.claude/projects/*.jsonl`) and answers the questions `/usage` does not:
how context grows, what a turn costs at 300K versus at 25K, when your rate limit
resets, and what the logs *cannot* tell you.

No dependencies. No network. Nothing leaves your machine.

```bash
python3 cli.py              # newest session in this project
python3 cli.py --all        # one line per session
python3 cli.py --csv        # one CSV row per session, to stdout
python3 cli.py --record     # append today's sessions to history/sessions.jsonl
python3 cli.py --limits     # rate-limit windows across every log
python3 cli.py --json       # machine-readable
python3 tests/test_reader.py
python3 tests/test_cli.py
python3 tests/test_history.py
```

Session logs under `~/.claude/projects/` are not durable — they rotate and get
pruned. `--record` appends a snapshot per session into `history/sessions.jsonl`,
one row per run (not an upsert — a time series of how a session's cost grew,
so re-running it later adds a new reading, not a rewrite). Run it periodically
if you want cost trends over weeks; what isn't captured today can't be
recovered once the source log is gone.

---

## Why this exists

Three things in the log format silently corrupt any naive analysis. Each produces
**plausible-looking numbers**, which is why they survive review. All three were
found by reading output against reality, not by tests — and each now has one.

### 1. A rate-limit refusal looks exactly like a successful turn

It carries `type: "assistant"` **and** `message.usage`. Count assistant records
with usage and you have silently included failed calls: turn count inflated,
average cost skewed downward. Detectable only via `isApiErrorMessage` or the
presence of `quotaLimits`.

### 2. A refusal does not mean you were blocked until `resetsAt`

Measured in a real log: a `five_hour` refusal, then **149 successful turns**
before the stated reset time arrived. So "am I limited right now" is answered by
a **fact** — was there a successful turn after the refusal — never by comparing
clocks. The first version of this tool printed "🔴 blocked, wait 1h54m" to a
session that was demonstrably working.

### 3. Sub-agent spend is not in the parent log at all

Zero `isSidechain` records in sessions that provably ran sub-agents consuming
~191k tokens. This tool prints that zero **with an explanation**, because a bare
`0` reads as "sub-agents are free".

---

## What it measures

| | |
|---|---|
| **Context** | peak, median, growth per turn (least-squares), and drops where context more than halved |
| **Cache** | read, written, hit rate, and the **write TTL split** — 1 hour vs 5 minutes |
| **Cost per turn** | bucketed by 25K of context, with the weight model printed alongside |
| **Limits** | `resetsAt` as a **unix timestamp** — no screen scraping, no timezone guessing; plus overage status |
| **Honesty** | what the log cannot answer, stated in the output rather than left to inference |

### Real output

```
CONTEXT
  turns        732
  peak         773 066   median 432 322
  growth       +981 tokens per turn
  drops        none

CACHE
  read         311 636 387
  written      2 142 590
  hit rate     99.3%
  write TTL    1h 2 142 590 · 5m 0   (cheap mode)

COST PER TURN  buckets of 25K context
       context  turns        cost   cache_read
        25 000     12      17 834       30 152
       325 000     18      40 082      330 617
```

**A turn at 325K costs 2.2× what it costs at 25K.** Cost is dominated by
`cache_read`, and `cache_read` equals the size of your context — the growth is
linear by construction. Hit rate is the number everyone quotes and the least
useful one: what you pay for is **bytes written** to cache, not the ratio.

---

## Stated limits

- **Weights are relative, not dollars.** `cache_read: 0.1, cache_creation: 2.0,
  input: 1.0, output: 1.0`. They are printed with every result so numbers from
  different runs stay comparable. Change them and all past numbers become
  incomparable — which is why they live in exactly one place.
- **A context drop is reported, not diagnosed.** Auto-compact and a session
  restart look identical in the log. The tool names the event; the conclusion is
  yours.
- **Limit data appears only on refusal.** No refusal means no data — not "you are
  far from the limit". The tool says so instead of implying headroom.
- **One machine, one user.** Nothing is aggregated across accounts.

## Tests

`python3 tests/test_reader.py` — 22 assertions on synthetic fixtures, no network
and no dependency on anyone's real logs. A test that needs your `~/.claude` to
pass is not a test, it is a demo.

## Структура

<!-- STRUCTURE:AUTO:START -->
| Папка | Файлов | Что внутри |
|---|---|---|
| `claude_usage/` | 3 | TODO — заполнить вручную |
| `reports/` | 2 | TODO — заполнить вручную |
| `tests/` | 1 | TODO — заполнить вручную |
<!-- STRUCTURE:AUTO:END -->
