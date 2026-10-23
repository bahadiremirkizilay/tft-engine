"""Item special effects turned into what board power can count (assumption class).

The values are game data (``curated/item_effects/<patch>.json``); how they add up
over a fight uses assumptions from ``decision/assumptions.py`` (fight length, the
share of the fight above half Health, how often a unit is hit, ...).

  * extra stats per unit: flat bonuses, bonuses that hold part of the fight, and
    stacks that grow over the fight (averaged over it, with their caps);
  * per-unit extras that are not stats: mana, Precision, shields, heals, regen,
    damage when hit;
  * team effects: Shred and Sunder on the enemies (do not stack) and one Burn.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_fit import profile

# assumptions an item effect may name (share of the fight, a count)
ITEM_ASSUMPTIONS = (
    "power_enemy_attack_damage_share",
    "power_enemy_tank_share",
    "power_targeting_enemies",
    "power_upper_health_share",
)
STACK_SAMPLES = 200  # time steps used to average a stack over the fight


@dataclass
class ItemExtras:
    """What a unit's items add beyond stats."""

    precision: int = 0
    mana_per_attack: float = 0.0
    mana_per_crit: float = 0.0
    mana_gain_pct: float = 0.0
    start_mana: float = 0.0
    shield_hp: float = 0.0  # share of max Health, once a fight
    heal_once_hp: float = 0.0  # share of max Health, once a fight
    regen_hp_per_second: float = 0.0  # share of max Health per second
    heal_damage: float = 0.0  # share of the holder's damage healed to allies
    when_hit_damage: float = 0.0  # magic damage per second while being hit
    crit_stacks: list[dict] = field(default_factory=list)
    stacks: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class TeamEffects:
    reduce_armor: float = 0.0  # Sunder on the enemies
    reduce_mr: float = 0.0  # Shred on the enemies
    burn: float = 0.0  # % enemy max Health per second
    burn_holder: str | None = None


def _named(a: AssumptionSet, name: str) -> float:
    if name not in ITEM_ASSUMPTIONS:
        raise KeyError(f"item effect names an unknown assumption {name!r}")
    return a[name]


def _roles(kb, unit: str) -> set[str]:
    tags = set(profile(kb, unit).tags)
    role = (kb.champions[unit].get("role") or "").lower()
    if "fighter" in role:
        tags.add("fighter")
    return tags


def _stat_value(e: dict, a: AssumptionSet, t: float) -> float:
    v = e["value"]
    if e.get("share"):
        share = _named(a, e["share"])
        v *= 1 - share if e.get("invert") else share
    if e.get("times"):
        v *= _named(a, e["times"])
    if e.get("after"):
        v *= max(0.0, t - e["after"]) / t
    if e.get("until"):
        v *= min(1.0, e["until"] / t)
    return v


def item_extras(
    kb, units: list[str], items: dict[str, list[str]], a: AssumptionSet
) -> tuple[dict[str, dict[str, float]], dict[str, ItemExtras], TeamEffects]:
    """Static extra stats, per-unit extras and team effects of the items on a board."""
    t = a["power_fight_seconds"]
    extra: dict[str, dict[str, float]] = {}
    extras: dict[str, ItemExtras] = {}
    team = TeamEffects()
    for u in units:
        ex = ItemExtras()
        roles = _roles(kb, u)
        for it in items.get(u, []):
            rec = kb.item_effects.get(it)
            if rec is None:
                continue
            for e in rec["effects"]:
                k = e["kind"]
                if k == "stat":
                    if e.get("roles") and not roles & set(e["roles"]):
                        continue
                    if e.get("not_roles") and roles & set(e["not_roles"]):
                        continue
                    stat = e["stat"]
                    extra.setdefault(u, {})
                    extra[u][stat] = extra[u].get(stat, 0.0) + _stat_value(e, a, t)
                elif k == "stack":
                    ex.stacks.append(e)
                elif k == "crit_stack":
                    ex.crit_stacks.append(e)
                elif k == "precision":
                    ex.precision += 1
                elif k == "mana":
                    ex.mana_per_attack += e.get("per_attack", 0)
                    ex.mana_per_crit += e.get("per_crit", 0)
                    ex.mana_gain_pct += e.get("gain_pct", 0)
                    ex.start_mana += e.get("start", 0) + e.get("once", 0)
                elif k == "shield":
                    ex.shield_hp += e["value"]
                elif k == "heal_once":
                    ex.heal_once_hp += e["value"] * (1 - e.get("at_health", 0))
                elif k == "regen":
                    share = e["value"] / e.get("every", 1)
                    if e["of"] == "missing_hp":
                        share *= a["power_missing_health_share"]
                    ex.regen_hp_per_second += share
                elif k == "heal_damage":
                    ex.heal_damage += e["value"]
                elif k == "damage_when_hit":
                    if "frontline" in roles:
                        hits = a["power_aoe_targets"] if e.get("hits") == "aoe" else 1.0
                        ex.when_hit_damage += e["value"] / e.get("every", 1) * hits
                elif k == "reduce":
                    if e["what"] == "armor":
                        team.reduce_armor = max(team.reduce_armor, e["value"])
                    else:
                        team.reduce_mr = max(team.reduce_mr, e["value"])
                elif k == "burn" and e["value"] > team.burn:
                    team.burn, team.burn_holder = e["value"], u
            if rec["model_status"] != "modelled" and rec.get("note"):
                ex.notes.append(f"{kb.items[it]['name']}: {rec['note']}")
        extras[u] = ex
    return extra, extras, team


def _average_stacks(e: dict, rate: float, t: float) -> tuple[float, float]:
    """Average stacks over the fight and the share of the fight spent at the cap."""
    cap = e.get("cap")
    total = full = 0.0
    for i in range(STACK_SAMPLES):
        tau = (i + 0.5) * t / STACK_SAMPLES
        if e["per"] == "interval":
            n = int(tau // e["interval"]) + (1 if e.get("at_start") else 0)
        else:
            n = rate * tau
        if cap is not None and n >= cap:
            n = cap
            full += 1
        total += n
    return total / STACK_SAMPLES, full / STACK_SAMPLES


def stack_extras(stats_list, extras: dict[str, ItemExtras], a: AssumptionSet):
    """Extra stats from stacks; they need each unit's attack speed and crit first."""
    t = a["power_fight_seconds"]
    out: dict[str, dict[str, float]] = {}
    for s in stats_list:
        ex = extras.get(s.unit)
        if ex is None:
            continue
        add = out.setdefault(s.unit, {})
        for e in ex.stacks:
            rate = {
                "second": 1.0,
                "attack": s.attack_speed,
                "attack_or_hit": s.attack_speed + a["power_hits_taken_per_second"],
                "interval": 0.0,
            }[e["per"]]
            avg, full = _average_stacks(e, rate, t)
            for part in [e] + list(e.get("also", [])):
                add[part["stat"]] = add.get(part["stat"], 0.0) + part["value"] * avg
            for part in e.get("full", []):
                add[part["stat"]] = add.get(part["stat"], 0.0) + part["value"] * full
        for e in ex.crit_stacks:  # steady state: crits per second x duration, capped
            stacks = min(e["cap"], s.crit * s.attack_speed * e["duration"])
            add[e["stat"]] = add.get(e["stat"], 0.0) + e["value"] * stacks
    return out
