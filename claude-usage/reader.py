"""
Reading Claude Code session logs. Everything this project knows about the raw
format lives here — the rest of the package sees clean dataclasses.

🔴 THREE TRAPS IN THE FORMAT. Each one was found the hard way, each one silently
corrupts statistics, and each has a test.

1. **A rate-limit rejection looks exactly like a successful turn.**
   It carries `type: "assistant"` AND `message.usage`, so any naive
   "count assistant records with usage" includes failed calls. First version of
   this reader counted them as turns; the numbers looked plausible, which is why
   it survived. Marked by `isApiErrorMessage: true` and/or a `quotaLimits` field.

2. **A rejection does NOT mean you were blocked until `resetsAt`.**
   Observed in a real log: a `five_hour` rejection, and then **149 successful
   turns** before the stated reset time ever arrived. So "are we limited right
   now" is answered by a *fact* (was there a successful turn after the
   rejection), never by comparing clocks.

3. **Sub-agent spend is not in the parent log at all.**
   Zero `isSidechain: true` records in sessions that demonstrably ran sub-agents
   consuming ~191k tokens. This tool reports that honestly instead of printing 0
   and letting you read it as "sub-agents are free".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

DEFAULT_ROOT = Path.home() / ".claude" / "projects"


@dataclass
class Turn:
    """One successful assistant turn."""
    ts: str
    model: str
    effort: str | None
    input: int
    cache_read: int
    cache_creation: int
    output: int
    thinking: int
    ttl_1h: int
    ttl_5m: int

    @property
    def context(self) -> int:
        """What the model actually saw. This is the number that grows."""
        return self.input + self.cache_read + self.cache_creation


@dataclass
class Rejection:
    """A rate-limit refusal, with the machine-readable reset time."""
    ts: str
    window: str          # five_hour, seven_day, …
    resets_at: int       # unix timestamp — no screen parsing, no timezone guessing
    overage: str | None
    overage_disabled_because: str | None


@dataclass
class Session:
    path: Path
    turns: list[Turn] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    sidechain_turns: int = 0
    api_errors: int = 0
    cli_versions: set[str] = field(default_factory=set)
    bad_lines: int = 0

    @property
    def id(self) -> str:
        return self.path.stem

    @property
    def project(self) -> str:
        return self.path.parent.name

    @property
    def last_ok_ts(self) -> str | None:
        return self.turns[-1].ts if self.turns else None


def _is_rejection(rec: dict) -> bool:
    q = rec.get("quotaLimits")
    return isinstance(q, dict) and bool(q.get("resetsAt"))


def _is_error(rec: dict) -> bool:
    return bool(rec.get("isApiErrorMessage")) or _is_rejection(rec)


def read_session(path: Path) -> Session:
    s = Session(path=path)
    try:
        fh = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return s
    with fh:
        for line in fh:
            if '"usage"' not in line and '"quotaLimits"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                s.bad_lines += 1
                continue

            if rec.get("version"):
                s.cli_versions.add(rec["version"])

            # Trap 1: check the rejection BEFORE the success branch. A rejection
            # carries type=assistant and usage, so the success branch would eat it.
            if _is_rejection(rec):
                q = rec["quotaLimits"]
                s.rejections.append(Rejection(
                    ts=rec.get("timestamp", ""),
                    window=q.get("rateLimitType", "unknown"),
                    resets_at=int(q["resetsAt"]),
                    overage=q.get("overageStatus"),
                    overage_disabled_because=q.get("overageDisabledReason"),
                ))
                s.api_errors += 1
                continue

            msg = rec.get("message") or {}
            usage = msg.get("usage")
            if not usage or rec.get("type") != "assistant":
                continue
            if _is_error(rec):
                s.api_errors += 1
                continue
            if rec.get("isSidechain"):
                s.sidechain_turns += 1
                continue

            cc = usage.get("cache_creation") or {}
            s.turns.append(Turn(
                ts=rec.get("timestamp", ""),
                model=(msg.get("model") or "unknown").replace("claude-", ""),
                effort=rec.get("effort"),
                input=usage.get("input_tokens") or 0,
                cache_read=usage.get("cache_read_input_tokens") or 0,
                cache_creation=usage.get("cache_creation_input_tokens") or 0,
                output=usage.get("output_tokens") or 0,
                thinking=(usage.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
                ttl_1h=cc.get("ephemeral_1h_input_tokens") or 0,
                ttl_5m=cc.get("ephemeral_5m_input_tokens") or 0,
            ))
    s.turns.sort(key=lambda t: t.ts)
    s.rejections.sort(key=lambda r: r.ts)
    return s


def find_sessions(root: Path | None = None, project: str | None = None) -> Iterator[Path]:
    """All session logs, newest first. No hand-written directory list."""
    root = root or DEFAULT_ROOT
    if not root.is_dir():
        return iter(())
    pattern = f"*{project}*/*.jsonl" if project else "*/*.jsonl"
    return iter(sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True))
