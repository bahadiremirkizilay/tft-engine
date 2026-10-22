"""How strong a board is, from its unit stats (assumption class, B6 first step).

Per unit:
  * damage per second = attacks (AD x attack speed x crit) + ability casts, both
    raised by damage amp; ability damage per cast is a stand-in by cost and star
    (``power_ability_base``) scaled by AP (AP abilities) or by AD gained (AD
    abilities) until ability values are recorded;
  * effective Health = Health x (1 + resist weight x average Armor/MR / 100)
    / (1 - durability), plus omnivamp healing; tanks turn part of their ability
    value into effective Health instead of damage.
Board power = sqrt(total damage per second x total effective Health): both halves
matter and the number grows like a single unit's "fight value". Every input
assumption sits in ``decision/assumptions.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_fit import profile
from tft_engine.rules.board_stats import BoardStats, UnitStats

# Set 18 units with a mana bar of 3 count attacks, not mana (Caitlyn: every third attack)


@dataclass(frozen=True)
class UnitPower:
    unit: str
    dps: float
    ehp: float
    casts: float


@dataclass(frozen=True)
class BoardPower:
    power: float
    dps: float
    ehp: float
    units: tuple[UnitPower, ...]
    traits: tuple
    stats: tuple[UnitStats, ...]


def unit_power(kb, s: UnitStats, a: AssumptionSet, star_ad: float = 1.0) -> UnitPower:
    """star_ad: the star multiplier on AD, so AD abilities grow only with bonus AD."""
    c = kb.champions[s.unit]
    text = c["ability"].get("text") or ""
    tank = "tank" in profile(kb, s.unit).tags
    t = a["power_fight_seconds"]
    crit_mult = (c["stats"].get("critMultiplier") or a["power_default_crit_mult"]) - 1
    attacks = s.ad * s.attack_speed * (1 + s.crit * crit_mult)
    if s.mana <= 0:
        casts = 0.0  # passive ability (Kayle): its value is in the attacks
    elif s.mana <= a["power_attack_count_mana"]:
        # a tiny mana bar counts attacks ("every third attack", Caitlyn, Master Yi)
        casts = t * s.attack_speed / s.mana
    else:
        gained = s.initial_mana + t * (s.attack_speed * a["power_mana_per_attack"] + s.mana_regen)
        casts = min(gained / s.mana, t / a["power_min_cast_seconds"])
    base = a["power_ability_base"][c["cost"]] * a["power_ability_star"][s.star]
    if "scaleAD" in text:
        base_ad = (c["stats"].get("damage") or 0) * star_ad
        scale = s.ad / base_ad if base_ad else 1.0
    else:
        scale = s.ap / 100
    ability = base * scale * casts
    amp = 1 + s.damage_amp
    resist = (s.armor + s.mr) / 2
    ehp = (
        s.hp
        * (1 + a["power_resist_weight"] * resist / 100)
        / max(1 - s.durability, a["power_min_damage_taken"])
    )
    if tank:
        ehp += a["power_tank_ability_share"] * ability
        dps = attacks * amp
    else:
        dps = (attacks + ability / t) * amp
    ehp += s.omnivamp * dps * t
    return UnitPower(s.unit, dps, ehp, casts)


def board_power(
    stats: BoardStats,
    units: list[tuple[str, int]],
    items: dict[str, list[str]] | None = None,
    emblems: dict[str, list[str]] | None = None,
    a: AssumptionSet | None = None,
) -> BoardPower:
    a = a or AssumptionSet()
    unit_stats, traits = stats.compute(units, items, emblems)
    parts = tuple(unit_power(stats.kb, s, a, stats.mult["ad"][s.star - 1]) for s in unit_stats)
    dps = sum(p.dps for p in parts)
    ehp = sum(p.ehp for p in parts)
    return BoardPower(math.sqrt(max(dps, 0) * max(ehp, 0)), dps, ehp, parts, tuple(traits),
                      tuple(unit_stats))  # fmt: skip
