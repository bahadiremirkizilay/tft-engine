"""Active traits of a board: which trait is on, at which breakpoint, with what values.

Counting rules, each with its source:
  * a champion counts once per trait, however many copies are on the board
    (trait breakpoints are by unique champions; standard TFT rule, the same as
    the trait texts' "(N)" rows);
  * an Avatar (Set 18 Lux) counts its chosen trait twice (DA_18_LuxUniqueTrait
    text: "An Avatar's chosen Trait is counted twice for Trait bonuses");
  * an emblem adds its trait to its holder; on a holder that already has the
    trait it adds nothing (game data parameter ``emblem_on_same_trait_counts``).
Breakpoint values come from the knowledge base (with patch overrides).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from tft_engine.rules.items import emblem_trait

# Trait whose holders count their other traits twice (read from its text in Set 18).
DOUBLE_COUNT_MARKER = "is counted twice"


@dataclass(frozen=True)
class ActiveTrait:
    trait_id: str
    name: str
    count: int
    breakpoint: int | None  # min units of the reached breakpoint; None = not active
    next_breakpoint: int | None
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.breakpoint is not None


def _double_count_traits(kb) -> set[str]:
    return {t["id"] for t in kb.traits.values() if DOUBLE_COUNT_MARKER in (t.get("text") or "")}


def trait_counts(
    kb,
    champions: Iterable[str],
    emblems: Mapping[str, Iterable[str]] | None = None,
    emblem_on_same_trait_counts: bool = False,
) -> tuple[dict[str, int], list[str]]:
    """Trait id -> count for unique champions; emblems by holder champion id.

    Returns the counts and notes (emblems that added nothing, unknown emblems).
    """
    doublers = _double_count_traits(kb)
    unique = list(dict.fromkeys(champions))
    counts: dict[str, int] = {}
    notes: list[str] = []
    for cid in unique:
        if cid not in kb.champions:
            raise KeyError(f"unknown champion {cid}")
        own = list(kb.champions[cid]["traits"])
        weight = 2 if any(t in doublers for t in own) else 1
        for t in own:
            if t in doublers:
                counts[t] = counts.get(t, 0) + 1
            else:
                counts[t] = counts.get(t, 0) + weight
    for holder, items in (emblems or {}).items():
        if holder not in unique:
            raise ValueError(f"emblem holder {holder} is not on the board")
        own = set(kb.champions[holder]["traits"])
        for iid in items:
            t = emblem_trait(kb, iid)
            if t is None:
                notes.append(f"{iid}: not an emblem of a known trait")
                continue
            if t in own and not emblem_on_same_trait_counts:
                notes.append(f"{kb.items[iid]['name']} on {holder} adds nothing (already has it)")
                continue
            counts[t] = counts.get(t, 0) + 1
            own.add(t)
    return counts, notes


def _reached(breakpoints: list[dict[str, Any]], n: int) -> dict[str, Any] | None:
    """The highest breakpoint reached with n units.

    Several rows with the same minimum (Set 18 Rival: 1+, 1-1, 2+) are told apart
    by their maximum: the last row whose maximum fits wins.
    """
    reached = [b for b in breakpoints if b["min_units"] <= n]
    if not reached:
        return None
    top = max(b["min_units"] for b in reached)
    rows = [b for b in reached if b["min_units"] == top]
    fitting = [b for b in rows if b.get("max_units") is None or n <= b["max_units"]]
    return (fitting or rows)[-1]


def active_traits(kb, counts: Mapping[str, int]) -> list[ActiveTrait]:
    """Every trait with at least one unit, active ones first (higher breakpoint first)."""
    out = []
    for tid, n in counts.items():
        t = kb.traits[tid]
        bps = [b for b in t.get("breakpoints", []) if b.get("min_units") is not None]
        bp = _reached(bps, n)
        higher = sorted({b["min_units"] for b in bps if b["min_units"] > n})
        out.append(
            ActiveTrait(
                tid,
                t["name"],
                n,
                bp["min_units"] if bp else None,
                higher[0] if higher else None,
                dict(bp.get("values", {})) if bp else {},
            )
        )
    out.sort(key=lambda a: (not a.active, -(a.breakpoint or 0), -a.count, a.name))
    return out
