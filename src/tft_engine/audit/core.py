"""Findings, the accept list (audit.toml) and the runner."""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_NAME = "audit.toml"

# kinds an accept entry may have; only "debt" stays visible in the report
ACCEPT_KINDS = ("debt", "setting", "technical", "not_modelled", "experimental", "tool_only")
LEVELS = ("error", "warning", "debt", "accepted")


@dataclass
class Finding:
    check: str  # which check found it, e.g. "constants"
    key: str  # stable id used by audit.toml, e.g. "sim/game.py:BENCH"
    message: str
    level: str = "error"
    reason: str = ""  # the accept reason, when audit.toml has an entry

    def line(self) -> str:
        message = self.message
        if self.reason:  # the accept reason replaces the how-to-fix hint
            message = message.split("; ")[0] + f"  [{self.reason}]"
        return f"{self.level.upper():8} {self.check:10} {self.key}: {message}"


@dataclass
class AuditConfig:
    accept: dict[str, dict[str, str]] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)  # other tables, read by single checks


def load_config(root: Path = REPO_ROOT) -> AuditConfig:
    path = root / CONFIG_NAME
    if not path.exists():
        return AuditConfig()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    accept: dict[str, dict[str, str]] = {}
    for i, entry in enumerate(raw.pop("accept", [])):
        key, kind, reason = entry.get("key"), entry.get("kind"), entry.get("reason")
        if not key or kind not in ACCEPT_KINDS or not reason:
            raise ValueError(
                f"{CONFIG_NAME} accept #{i + 1}: needs key, kind ({'/'.join(ACCEPT_KINDS)}) "
                "and a reason"
            )
        if key in accept:
            raise ValueError(f"{CONFIG_NAME}: {key} is listed twice")
        accept[key] = {"kind": kind, "reason": reason}
    return AuditConfig(accept, raw)


def apply_config(findings: list[Finding], config: AuditConfig) -> list[Finding]:
    """Downgrade accepted findings and report accept entries that match nothing."""
    seen = set()
    for f in findings:
        entry = config.accept.get(f.key)
        if entry is None or f.level not in ("error", "warning"):
            continue
        seen.add(f.key)
        f.reason = entry["reason"]
        f.level = "debt" if entry["kind"] == "debt" else "accepted"
    for key in sorted(set(config.accept) - seen):
        findings.append(
            Finding(
                "config",
                key,
                f"{CONFIG_NAME} entry matches no finding any more; remove it",
                "warning",
            )
        )
    return findings


Check = Callable[[Path, AuditConfig], Iterable[Finding]]


def all_checks() -> dict[str, Check]:
    from tft_engine.audit import data, docs, layers, source_scan, wiring

    return {
        "data": data.check,
        "constants": source_scan.check_constants,
        "layers": layers.check,
        "wiring": wiring.check,
        "docs": docs.check,
    }


def run_audit(
    root: Path = REPO_ROOT, only: Iterable[str] | None = None, config: AuditConfig | None = None
) -> list[Finding]:
    config = config if config is not None else load_config(root)
    checks = all_checks()
    names = list(only) if only else list(checks)
    findings: list[Finding] = []
    for name in names:
        findings.extend(checks[name](root, config))
    if not only:  # stale entries can only be judged when every check ran
        return apply_config(findings, config)
    return [f for f in apply_config(findings, config) if f.check != "config"]
