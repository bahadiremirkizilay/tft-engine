"""Which comps fit what you hold, and the best three items for a carry (B5).

Both answers are explainable rankings (assumption class): the score weights
come from ``assumptions.comp_match_weights`` and say nothing about win rates.
Site statistics are shown next to a comp, never mixed into its score (plan
rule 10).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_fit import item_fit
from tft_engine.rules.comps import CompSet
from tft_engine.rules.items import RecipeBook


@dataclass(frozen=True)
class CompMatch:
    comp_id: str
    name: str
    score: float
    owned: tuple[str, ...]  # comp units already owned
    missing: tuple[str, ...]
    item_uses: tuple[str, ...]  # "component -> item (carry)" for held components
    stats: tuple[dict[str, Any], ...] = ()  # site statistics, shown apart from the score
    tiers: tuple[dict[str, Any], ...] = ()  # editorial tier labels (guides)
    style: str = ""
    items_known: bool = True  # False: no carry builds known, items did not count
    trust: str = "assumption"


@dataclass(frozen=True)
class TrioOption:
    items: tuple[str, ...]
    missing_components: tuple[str, ...]
    basis: str  # "meta: <site> <patch> <rank>" or "rule"
    score: float | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def _carry_builds(comps: CompSet, unit_id: str) -> list[tuple[tuple[str, ...], str]]:
    """Known three-item builds for a unit: (items, basis), templates first."""
    out = []
    for r in comps.templates.values():
        for c in r.get("carry_items", []):
            if c["unit"] == unit_id:
                out += [(tuple(b), f"template {r['id']}") for b in c["builds"]]
    for row in comps.unit_builds(unit_id):
        out.append(
            (tuple(row["items"]), f"meta: {row['site']} {row['patch']} {row['rank_filter']}")
        )
    return out


def missing_components(
    book: RecipeBook, build: Iterable[str], components: Iterable[str], held: Iterable[str] = ()
) -> list[str]:
    """Components still needed to finish ``build`` from held items and components."""
    held_left = Counter(held)
    need: Counter = Counter()
    for item in build:
        if held_left[item] > 0:
            held_left[item] -= 1
            continue
        pair = book.recipe_of(item)
        if pair is None:
            need[f"(no recipe: {item})"] += 1
            continue
        need.update(pair)
    have = Counter(components)
    return sorted((need - have).elements())


def match_comps(
    kb,
    comps: CompSet,
    owned_units: Iterable[str],
    components: Iterable[str],
    a: AssumptionSet,
    book: RecipeBook | None = None,
) -> list[CompMatch]:
    book = book or RecipeBook(kb)
    w = a["comp_match_weights"]
    owned = set(owned_units)
    comps_held = list(components)
    out = []
    for cid, r in comps.templates.items():
        units = [u["id"] for u in r["units"]]
        weight = {u: kb.champions[u]["cost"] ** w["unit_cost_exp"] for u in units}
        have = [u for u in units if u in owned]
        unit_share = sum(weight[u] for u in have) / sum(weight.values())
        uses = []
        used = 0
        carries = [u["id"] for u in r["units"] if u["role"] == "carry"]
        wanted: dict[str, str] = {}  # component -> "item (carry)"
        for c in carries:
            for build, _ in _carry_builds(comps, c):
                for item in build:
                    for comp in book.recipe_of(item) or ():
                        wanted.setdefault(comp, f"{book.name(item)} ({kb.champions[c]['name']})")
        for comp in comps_held:
            if comp in wanted:
                used += 1
                uses.append(f"{book.name(comp)} -> {wanted[comp]}")
        # comps without known carry builds get no item term, so they are not penalised
        denom = max(len(comps_held), w["min_components"])
        item_share = used / denom if comps_held and wanted else 0.0
        if not wanted:
            # rank on units alone: scale so the item weight does not decide between comps
            score = w["units"] * unit_share
        else:
            score = w["units"] * unit_share + w["items"] * item_share
        out.append(
            CompMatch(
                cid,
                r["name"],
                round(score, 3),
                tuple(have),
                tuple(u for u in units if u not in owned),
                tuple(uses),
                tuple(comps.comp_stats(cid)),
                tuple(comps.tiers(cid)),
                r.get("style", ""),
                bool(wanted),
            )
        )
    out.sort(key=lambda m: (-m.score, m.name))
    return out


def best_trio(
    kb,
    comps: CompSet,
    unit_id: str,
    components: Iterable[str],
    a: AssumptionSet,
    held_items: Iterable[str] = (),
    book: RecipeBook | None = None,
    top: int = 5,
) -> list[TrioOption]:
    """Three-item options for a carry, fewest missing components first.

    Known builds (templates, site statistics) come first; when there are none,
    rule-based options from what the held components can make.
    """
    book = book or RecipeBook(kb)
    comps_held, held = list(components), list(held_items)
    known = _carry_builds(comps, unit_id)
    if known:
        opts = []
        for build, basis in known:
            miss = missing_components(book, build, comps_held, held)
            opts.append(TrioOption(build, tuple(miss), basis))
        opts.sort(key=lambda o: len(o.missing_components))  # stable: keeps source order
        return opts[:top]
    # rule fallback: every item one held pair can make, plus held items; best sums of three
    pool = list(dict.fromkeys(held + [b.item for b in book.options(comps_held)]))
    scored = {i: item_fit(kb, unit_id, i, a).score for i in pool}
    options = []
    for trio in combinations(pool, min(3, len(pool))):
        miss = missing_components(book, trio, comps_held, held)
        options.append(
            TrioOption(
                trio,
                tuple(miss),
                "rule",
                round(sum(scored[i] for i in trio), 2),
                ("rule-based fit, not statistics",),
            )
        )
    options.sort(key=lambda o: (len(o.missing_components), -(o.score or 0)))
    return options[:top]
