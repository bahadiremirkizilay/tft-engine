"""Unit stats on a board: base stats x stars, plus items, plus active trait effects (B6).

This applies game data only: champion base stats, star multipliers (game data
parameter ``star_multipliers``), item stats (curated item_stats), trait
breakpoint values and how they map to stats (curated/effects/traits.json).
How strong the result is in a fight is a separate, assumption-class question
(``decision/board_power.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tft_engine.gamedata.schema import SchemaError
from tft_engine.rules.items import emblem_trait
from tft_engine.rules.traits import active_traits, trait_counts

STATS = (
    "hp", "ad", "ap", "as", "armor", "mr", "crit", "mana_regen",
    "durability", "damage_amp", "omnivamp",
)  # fmt: skip
TARGETS = ("trait", "team", "others", "rider")
TRAIT_FLAGS = ("precision",)  # effects that switch a rule on rather than add a stat
EFFECT_STATS = (
    "hp_flat", "hp_pct", "ad_pct", "ap", "as_pct", "armor", "mr", "durability",
    "damage_amp", "omnivamp", "crit", "mana_regen", "adaptive",
)  # fmt: skip
# item stat key -> effect stat (item AP is in points, like trait AP after scaling)
ITEM_TO_EFFECT = {
    "hp": "hp_flat", "ad_pct": "ad_pct", "ap": "ap", "as_pct": "as_pct", "armor": "armor",
    "mr": "mr", "crit_pct": "crit", "mana_regen": "mana_regen", "omnivamp_pct": "omnivamp",
    "damage_amp_pct": "damage_amp", "durability_pct": "durability",
    "damage_reduction_pct": "durability",
}  # fmt: skip
PCT_ITEM_KEYS = {"ad_pct", "as_pct", "crit_pct", "omnivamp_pct", "damage_amp_pct",
                 "durability_pct", "damage_reduction_pct"}  # fmt: skip


def load_trait_models(set_id: str, root: Path | None = None) -> dict[str, dict[str, Any]]:
    base = Path(root) if root else Path(__file__).resolve().parents[3] / "data" / "sets"
    path = base / set_id / "curated" / "effects" / "traits.json"
    if not path.exists():
        return {}
    out = {}
    for r in json.loads(path.read_text(encoding="utf-8"))["records"]:
        for e in r["effects"]:
            if "flag" in e:
                if e["to"] not in TARGETS or e["flag"] not in TRAIT_FLAGS:
                    raise SchemaError(f"traits.json {r['id']}: bad target or flag in {e}")
                continue
            if e["to"] not in TARGETS or e["stat"] not in EFFECT_STATS:
                raise SchemaError(f"traits.json {r['id']}: bad target or stat in {e}")
        out[r["id"]] = r
    return out


def check_trait_models(kb, models: dict[str, dict[str, Any]]) -> list[str]:
    errors = []
    for tid, m in models.items():
        if tid not in kb.traits:
            errors.append(f"trait model {tid}: no such trait")
            continue
        names = {k for b in kb.traits[tid]["breakpoints"] for k in b["values"]}
        for e in m["effects"]:
            if "flag" in e:
                continue
            if e["value"] not in names:
                errors.append(f"trait model {tid}: value {e['value']!r} is not in the trait record")
    return errors


@dataclass
class UnitStats:
    unit: str
    star: int
    hp: float
    ad: float
    ap: float  # Ability Power points (100 = base)
    attack_speed: float
    armor: float
    mr: float
    crit: float
    mana: float
    initial_mana: float
    mana_regen: float
    durability: float
    damage_amp: float
    omnivamp: float
    range: float
    sources: list[str] = field(default_factory=list)  # what changed the stats, readable
    form: str | None = None  # Adaptor form used ("ad" / "ap"), None for other units
    flags: tuple[str, ...] = ()  # rules switched on by traits (precision)


class BoardStats:
    """Stats of every unit on a board, given stars, items and emblem holders."""

    def __init__(self, kb, data, models: dict[str, dict[str, Any]] | None = None):
        self.kb = kb
        self.mult = data.get("star_multipliers")
        self.same = bool(data.param("emblem_on_same_trait_counts").get())
        self.models = models if models is not None else load_trait_models(kb.set_id)

    def form_stats(self, unit: str, form: str | None) -> dict[str, Any]:
        """Base stats of a unit in an Adaptor form (a form may replace some of them)."""
        s = dict(self.kb.champions[unit]["stats"])
        rec = self.kb.ability(unit) if form else None
        if rec:
            s.update((rec.get("forms") or {}).get(form, {}).get("stats", {}))
        return s

    def _base(self, unit: str, star: int, form: str | None = None) -> dict[str, float]:
        s = self.form_stats(unit, form)
        return {
            "hp": (s.get("hp") or 0) * self.mult["hp"][star - 1],
            "ad": (s.get("damage") or 0) * self.mult["ad"][star - 1],
            "as": s.get("attackSpeed") or 0,
            "armor": s.get("armor") or 0,
            "mr": s.get("magicResist") or 0,
            "crit": s.get("critChance") or 0,
        }

    def compute(
        self,
        units: list[tuple[str, int]],
        items: dict[str, list[str]] | None = None,
        emblems: dict[str, list[str]] | None = None,
        forms: dict[str, str] | None = None,
        extra: dict[str, dict[str, float]] | None = None,
    ) -> tuple[list[UnitStats], list]:
        """forms: Adaptor form ("ad" or "ap") per unit; others follow their ability text.
        extra: more effect stats per unit (item special effects worked out by the caller).
        """
        items = items or {}
        forms = forms or {}
        ids = [u for u, _ in units]
        counts, _ = trait_counts(self.kb, ids, emblems, self.same)
        traits = [t for t in active_traits(self.kb, counts) if t.active]
        # which units hold each trait (emblems add the trait to their holder)
        holders: dict[str, set[str]] = {}
        for u in ids:
            for t in self.kb.champions[u]["traits"]:
                holders.setdefault(t, set()).add(u)
        for h, es in (emblems or {}).items():
            for e in es:
                holders.setdefault(emblem_trait(self.kb, e), set()).add(h)
        star_of = dict(units)
        bonus: dict[str, dict[str, float]] = {u: dict.fromkeys(EFFECT_STATS, 0.0) for u in ids}
        notes: dict[str, list[str]] = {u: [] for u in ids}
        for u in ids:
            for it in items.get(u, []):
                for k, v in (self.kb.items[it].get("stats") or {}).items():
                    key = ITEM_TO_EFFECT.get(k)
                    if key:
                        bonus[u][key] += v / 100 if k in PCT_ITEM_KEYS else v
            for k, v in (extra or {}).get(u, {}).items():
                bonus[u][k] += v
        flags: dict[str, set[str]] = {u: set() for u in ids}
        for t in traits:
            model = self.models.get(t.trait_id)
            if not model:
                continue
            members = holders.get(t.trait_id, set())
            rider = max(
                members,
                key=lambda u: (self.kb.champions[u]["cost"], star_of[u], u),
                default=None,
            )
            for e in model["effects"]:
                if "flag" in e:
                    for u in members if e["to"] == "trait" else ids:
                        flags[u].add(e["flag"])
                    continue
                v = t.values.get(e["value"])
                if v is None:
                    continue
                amount = v * e.get("scale", 1) * e.get("factor", 1)
                if e["to"] == "trait":
                    targets = members
                elif e["to"] == "team":
                    targets = set(ids)
                elif e["to"] == "others":
                    targets = set(ids) - members
                else:
                    targets = {rider} if rider else set()
                for u in targets:
                    bonus[u][e["stat"]] += amount
                    notes[u].append(f"{t.name} {t.count}: {e['stat']} {amount:+g}")
        out = []
        for u in ids:
            star = star_of[u]
            form = forms.get(u)
            b = self._base(u, star, form)
            x = bonus[u]
            if form:
                ad_scaling = form == "ad"
            else:
                ad_scaling = "scaleAD" in (self.kb.champions[u]["ability"].get("text") or "")
            ad_pct, ap = x["ad_pct"], x["ap"]
            if x["adaptive"]:
                if ad_scaling:
                    ad_pct += x["adaptive"]
                else:
                    ap += x["adaptive"] * 100
            c = self.form_stats(u, form)
            out.append(
                UnitStats(
                    unit=u,
                    star=star,
                    hp=(b["hp"] + x["hp_flat"]) * (1 + x["hp_pct"]),
                    ad=b["ad"] * (1 + ad_pct),
                    ap=100 + ap,
                    attack_speed=b["as"] * (1 + x["as_pct"]),
                    armor=b["armor"] + x["armor"],
                    mr=b["mr"] + x["mr"],
                    crit=min(1.0, b["crit"] + x["crit"]),
                    mana=c.get("mana") or 0,
                    initial_mana=c.get("initialMana") or 0,
                    mana_regen=x["mana_regen"],
                    durability=min(0.9, x["durability"]),
                    damage_amp=x["damage_amp"],
                    omnivamp=x["omnivamp"],
                    range=c.get("range") or 1,
                    sources=notes[u],
                    form=form,
                    flags=tuple(sorted(flags[u])),
                )
            )
        return out, traits
