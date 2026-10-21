"""Items: recipes, what a set of components can build, stat bonuses.

Everything here reads the knowledge base (generated records plus curated
item stats); no item number lives in this module. Only one item family is used
at a time (Set 18: ``DA``), so older copies of the same item never mix in.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations_with_replacement
from typing import Any

from tft_engine.gamedata.schema import STATUSES

BUILT_KINDS = ("completed", "emblem")


def _norm(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


@dataclass(frozen=True)
class Build:
    item: str  # item id
    pair: tuple[str, str]  # the two component ids, sorted


class RecipeBook:
    """Component pairs and the item each pair makes, for one item family."""

    def __init__(self, kb, family: str = "DA") -> None:
        self.kb = kb
        self.family = family
        items = kb.items
        self.components = sorted(
            i["id"] for i in items.values() if i["kind"] == "component" and i["family"] == family
        )
        self.recipes: dict[tuple[str, str], str] = {}
        for i in items.values():
            if i["family"] != family or i["kind"] not in BUILT_KINDS or not i.get("recipe"):
                continue
            pair = tuple(sorted(i["recipe"]))
            if len(pair) != 2:
                continue
            if pair in self.recipes:
                raise ValueError(f"recipe {pair} makes both {self.recipes[pair]} and {i['id']}")
            self.recipes[pair] = i["id"]  # type: ignore[index]
        self._by_name = {_norm(i["name"]): i["id"] for i in items.values() if i["family"] == family}

    # --- names ------------------------------------------------------------

    def item_id(self, name_or_id: str) -> str:
        """Item id from an id or a display name ("B.F. Sword", "bf sword")."""
        if name_or_id in self.kb.items and self.kb.items[name_or_id]["family"] == self.family:
            return name_or_id
        key = _norm(name_or_id)
        if key in self._by_name:
            return self._by_name[key]
        raise KeyError(f"no {self.family} item named {name_or_id!r}")

    def name(self, item_id: str) -> str:
        return self.kb.items[item_id]["name"]

    # --- recipes ----------------------------------------------------------

    @property
    def complete(self) -> bool:
        """Every component pair makes exactly one item."""
        pairs = combinations_with_replacement(self.components, 2)
        return all(p in self.recipes for p in pairs)

    def make(self, a: str, b: str) -> str | None:
        return self.recipes.get(tuple(sorted((a, b))))  # type: ignore[arg-type]

    def recipe_of(self, item_id: str) -> tuple[str, str] | None:
        return next((p for p, i in self.recipes.items() if i == item_id), None)

    def options(self, have: Iterable[str]) -> list[Build]:
        """Every item one pair of the held components can make."""
        bag = Counter(have)
        out = []
        for pair, item in sorted(self.recipes.items()):
            need = Counter(pair)
            if all(bag[c] >= n for c, n in need.items()):
                out.append(Build(item, pair))
        return out

    def missing_for(self, item_id: str, have: Iterable[str]) -> list[str]:
        """Components still needed to build ``item_id`` from what is held."""
        pair = self.recipe_of(item_id)
        if pair is None:
            raise ValueError(f"{item_id} has no recipe")
        bag = Counter(have)
        out = []
        for c in pair:
            if bag[c] > 0:
                bag[c] -= 1
            else:
                out.append(c)
        return out

    def full_builds(self, have: Iterable[str]) -> list[tuple[str, ...]]:
        """Every way to turn all held components into items (pairs), as sorted item tuples.

        With an odd count one component stays unused; it is left out of the tuple.
        """
        comps = sorted(have)
        found: set[tuple[str, ...]] = set()

        def go(rest: list[str], made: tuple[str, ...]) -> None:
            if len(rest) < 2:
                found.add(tuple(sorted(made)))
                return
            first = rest[0]
            for j in range(1, len(rest)):
                if j > 1 and rest[j] == rest[j - 1]:
                    continue
                item = self.make(first, rest[j])
                if item is not None:
                    go(rest[1:j] + rest[j + 1 :], made + (item,))
            if len(rest) % 2 == 1:  # leave this one unused
                go(rest[1:], made)

        go(comps, ())
        return sorted(found)


# --- stats -------------------------------------------------------------------


@dataclass(frozen=True)
class StatBonus:
    stats: dict[str, float]  # summed bonuses, keys from curated.STAT_KEYS
    status: str  # weakest status among the items used
    sources: tuple[str, ...]
    missing: tuple[str, ...]  # items with no stat record (bonus unknown)


def stat_bonus(kb, item_ids: Iterable[str]) -> StatBonus:
    """Summed stat bonuses of items (no combat rules: percentages stay percentages)."""
    total: dict[str, float] = {}
    statuses, sources, missing = [], [], []
    for iid in item_ids:
        item = kb.items[iid]
        if "stats" not in item:
            missing.append(iid)
            continue
        for k, v in item["stats"].items():
            total[k] = total.get(k, 0) + v
        statuses.append(item.get("stats_status", "unknown"))
        sources += [s for s in item.get("stats_source_ids", []) if s not in sources]
    weakest = max(statuses, key=STATUSES.index) if statuses else "unknown"
    return StatBonus(total, weakest, tuple(sources), tuple(missing))


def emblem_trait(kb, item_id: str) -> str | None:
    """Trait id an emblem gives, matched by name ("Blossom Emblem" -> Blossom)."""
    item = kb.items[item_id]
    if item["kind"] != "emblem":
        return None
    linked: Any = item.get("associated_traits") or []
    if len(linked) == 1:
        return linked[0]
    name = item["name"].removesuffix(" Emblem")
    hits = [t["id"] for t in kb.traits.values() if t["name"] == name]
    return hits[0] if len(hits) == 1 else None
