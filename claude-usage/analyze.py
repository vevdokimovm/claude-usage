"""
Metrics over a session. No I/O, no formatting — so it can be tested on fixtures.

The one opinionated thing here is the **cost model**. Token counts alone do not
answer "what did this turn cost me", because a cached read and a fresh write are
not the same money. Weights are declared as a constant and printed with the
result, so numbers from different runs stay comparable and nobody has to guess
which formula produced them.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from .reader import Rejection, Session, Turn

# Relative weights, not dollars. cache_read is an order of magnitude cheaper than
# a fresh write; output is billed like fresh input. Change these and every past
# number becomes incomparable — that is why they live in one place.
COST = {"cache_read": 0.1, "cache_creation": 2.0, "input": 1.0, "output": 1.0}
BUCKET = 25_000


def turn_cost(t: Turn) -> float:
    return (t.cache_read * COST["cache_read"] + t.cache_creation * COST["cache_creation"]
            + t.input * COST["input"] + t.output * COST["output"])


def slope(values: list[float]) -> float:
    """Least-squares slope over turn index. No numpy — it is four lines."""
    n = len(values)
    if n < 2:
        return 0.0
    mx, my = (n - 1) / 2, sum(values) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (v - my) for i, v in enumerate(values)) / den if den else 0.0


@dataclass
class Bucket:
    floor: int
    turns: int
    avg_cost: float
    avg_cache_read: float


def buckets(turns: list[Turn]) -> list[Bucket]:
    acc: dict[int, list[Turn]] = {}
    for t in turns:
        acc.setdefault(t.context // BUCKET * BUCKET, []).append(t)
    return [Bucket(lo, len(v),
                   sum(turn_cost(x) for x in v) / len(v),
                   sum(x.cache_read for x in v) / len(v))
            for lo, v in sorted(acc.items())]


def context_drops(turns: list[Turn], floor: int = 50_000, factor: float = 0.5
                  ) -> list[tuple[int, int, int]]:
    """Turns where context more than halved.

    🔴 Deliberately NOT labelled "auto-compact": a restart of the session looks
    identical from the log. The tool reports the event; the conclusion is yours.
    """
    out = []
    for i in range(1, len(turns)):
        prev, cur = turns[i - 1].context, turns[i].context
        if prev > floor and cur < prev * factor:
            out.append((i + 1, prev, cur))
    return out


def limit_state(s: Session, now: float | None = None) -> dict[str, dict]:
    """Per-window limit state.

    🔴 Trap 2: `resets_at` in the future does NOT mean you are blocked.
    A rejection is considered *cleared* when a successful turn exists after it.
    Observed in a real log: 149 successful turns after a rejection whose stated
    reset time had not yet arrived.
    """
    now = now if now is not None else datetime.datetime.now().timestamp()
    last_ok = s.last_ok_ts
    latest: dict[str, Rejection] = {}
    for r in s.rejections:
        if r.window not in latest or r.resets_at > latest[r.window].resets_at:
            latest[r.window] = r

    out = {}
    for window, r in latest.items():
        cleared = bool(last_ok and r.ts and last_ok > r.ts)
        left = int(r.resets_at - now)
        out[window] = {
            "hit_at": r.ts,
            "resets_at": r.resets_at,
            "resets_local": datetime.datetime.fromtimestamp(r.resets_at).isoformat(timespec="minutes"),
            "seconds_left": max(0, left),
            "cleared_by_later_success": cleared,
            "possibly_blocked": (left > 0) and not cleared,
            "overage": r.overage,
            "overage_disabled_because": r.overage_disabled_because,
        }
    return out


@dataclass
class Summary:
    session_id: str
    project: str
    models: dict[str, int]
    efforts: dict[str, int]
    turns: int
    max_context: int
    median_context: int
    growth_per_turn: float
    cache_read: int
    cache_creation: int
    fresh_input: int
    output: int
    thinking: int
    ttl_1h: int
    ttl_5m: int
    hit_rate: float
    buckets: list[Bucket]
    drops: list[tuple[int, int, int]]
    limits: dict[str, dict]
    sidechain_turns: int
    api_errors: int
    cli_versions: list[str]

    @property
    def cost_growth(self) -> float:
        """How much more a turn costs at the top of the range than at the bottom."""
        if len(self.buckets) < 2 or not self.buckets[0].avg_cost:
            return 1.0
        return self.buckets[-1].avg_cost / self.buckets[0].avg_cost


def summarize(s: Session) -> Summary | None:
    if not s.turns:
        return None
    ctx = [t.context for t in s.turns]
    models: dict[str, int] = {}
    efforts: dict[str, int] = {}
    for t in s.turns:
        models[t.model] = models.get(t.model, 0) + 1
        if t.effort:
            efforts[t.effort] = efforts.get(t.effort, 0) + 1
    cr = sum(t.cache_read for t in s.turns)
    cc = sum(t.cache_creation for t in s.turns)
    return Summary(
        session_id=s.id, project=s.project, models=models, efforts=efforts,
        turns=len(s.turns), max_context=max(ctx),
        median_context=sorted(ctx)[len(ctx) // 2],
        growth_per_turn=slope([float(c) for c in ctx]),
        cache_read=cr, cache_creation=cc,
        fresh_input=sum(t.input for t in s.turns),
        output=sum(t.output for t in s.turns),
        thinking=sum(t.thinking for t in s.turns),
        ttl_1h=sum(t.ttl_1h for t in s.turns), ttl_5m=sum(t.ttl_5m for t in s.turns),
        hit_rate=(cr / (cr + cc) * 100) if (cr + cc) else 0.0,
        buckets=buckets(s.turns), drops=context_drops(s.turns),
        limits=limit_state(s), sidechain_turns=s.sidechain_turns,
        api_errors=s.api_errors, cli_versions=sorted(s.cli_versions),
    )
