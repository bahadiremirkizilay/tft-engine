"""How strong a board is, from its unit stats (assumption class, B6).

Per unit:
  * damage per second = attacks (AD x attack speed x crit) + ability damage, both
    raised by damage amp, split into physical, magic and true damage;
  * effective Health = Health x (1 + resist weight x average Armor/MR / 100)
    / (1 - durability), plus omnivamp healing, ability shields and heals and item
    shields, heals and regeneration.
Ability values come from the patch's ability records (``kb.ability``): each part
is scaled by AD gained (physical) or AP (magic), times targets hit, casts and
attacks. Adaptor units take the form in ``power_adaptor_form`` or the stronger
one. Without a record (patches before 18.5) the old stand-in is used: damage per
cast by cost and star (``power_ability_base``), and tanks turn part of it into
effective Health.
Items: stats, then special effects from the patch's item effect records
(``decision/item_effects.py``): stacks averaged over the fight, Precision, mana,
shields, Shred/Sunder and Burn on the enemies.
Enemies: physical and magic damage are reduced by assumed enemy Armor and MR
(after Shred/Sunder); true damage is not.
Board power = sqrt(total damage per second x total effective Health): both halves
matter and the number grows like a single unit's "fight value". Every input
assumption sits in ``decision/assumptions.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_effects import ItemExtras, TeamEffects, item_extras, stack_extras
from tft_engine.decision.item_fit import profile
from tft_engine.rules.board_stats import BoardStats, UnitStats


@dataclass(frozen=True)
class UnitPower:
    unit: str
    dps: float  # after enemy Armor and MR on the board, before: raw total
    ehp: float
    casts: float
    source: str = "stand-in"  # "record" when ability values come from the patch data
    physical: float = 0.0  # raw damage per second by type
    magic: float = 0.0
    true: float = 0.0


@dataclass(frozen=True)
class BoardPower:
    power: float
    dps: float
    ehp: float
    units: tuple[UnitPower, ...]
    traits: tuple
    stats: tuple[UnitStats, ...]
    team: TeamEffects | None = None


# assumptions an ability record may name as the chance its condition holds
CHANCE_ASSUMPTIONS = ("power_conditional_share",)
NO_EXTRAS = ItemExtras()


def _casts(s: UnitStats, a: AssumptionSet, t: float, ex: ItemExtras) -> float:
    if s.mana <= 0:
        return 0.0  # passive ability (Kayle): its value is in the attacks
    if s.mana <= a["power_attack_count_mana"]:
        # a tiny mana bar counts attacks ("every third attack", Caitlyn, Master Yi)
        return t * s.attack_speed / s.mana
    per_attack = a["power_mana_per_attack"] + ex.mana_per_attack + ex.mana_per_crit * s.crit
    per_attack *= 1 + ex.mana_gain_pct
    gained = s.initial_mana + ex.start_mana + t * (s.attack_speed * per_attack + s.mana_regen)
    return min(gained / s.mana, t / a["power_min_cast_seconds"])


def _targets(hits, a: AssumptionSet) -> float:
    if isinstance(hits, int):
        return float(hits)
    shape = {"single": 1.0, "split": 1.0}
    return shape.get(hits) or a["power_aoe_targets" if hits == "aoe" else "power_line_targets"]


def _record_parts(kb, s: UnitStats) -> list[dict] | None:
    rec = kb.ability(s.unit)
    if rec is None:
        return None
    if rec.get("forms"):
        form = s.form or next(iter(rec["forms"]))
        return rec["forms"][form].get("parts", [])
    return rec.get("parts", [])


def _ehp(s: UnitStats, a: AssumptionSet, t: float, ex: ItemExtras) -> float:
    resist = (s.armor + s.mr) / 2
    base = (
        s.hp
        * (1 + a["power_resist_weight"] * resist / 100)
        / max(1 - s.durability, a["power_min_damage_taken"])
    )
    items = s.hp * (ex.shield_hp + ex.heal_once_hp + ex.regen_hp_per_second * t)
    return base + items * a["power_sustain_weight"]


def unit_power(
    kb, s: UnitStats, a: AssumptionSet, star_ad: float = 1.0, ex: ItemExtras | None = None
) -> UnitPower:
    """star_ad: the star multiplier on AD, so AD abilities grow only with bonus AD."""
    ex = ex or NO_EXTRAS
    c = kb.champions[s.unit]
    t = a["power_fight_seconds"]
    crit_mult = (c["stats"].get("critMultiplier") or a["power_default_crit_mult"]) - 1
    attacks = s.ad * s.attack_speed * (1 + s.crit * crit_mult)
    casts = _casts(s, a, t, ex)
    amp = 1 + s.damage_amp
    ehp = _ehp(s, a, t, ex)
    parts = _record_parts(kb, s)
    if parts is None:
        return _stand_in(kb, s, a, star_ad, t, attacks, casts, amp, ehp, ex)
    base_ad = (c["stats"].get("damage") or 0) * star_ad
    if s.form:
        form_ad = kb.ability(s.unit)["forms"][s.form].get("stats", {}).get("damage")
        if form_ad:
            base_ad = form_ad * star_ad
    ad_ratio = s.ad / base_ad if base_ad else 1.0
    ap_ratio = s.ap / 100
    base_as = c["stats"].get("attackSpeed") or 0
    if s.form:
        base_as = kb.ability(s.unit)["forms"][s.form].get("stats", {}).get("attackSpeed") or base_as
    as_ratio = s.attack_speed / base_as if base_as else 1.0
    ratios = {"ap": ap_ratio, "ad": ad_ratio, "as": as_ratio}
    term_stat = {"hp": s.hp, "armor": s.armor, "mr": s.mr, "ap": ap_ratio}
    # Precision: ability damage can crit; each extra source adds 10% crit damage
    precision = ex.precision + (1 if "precision" in s.flags else 0)
    ability_crit = (
        1 + s.crit * (crit_mult + a["power_extra_precision_crit"] * (precision - 1))
        if precision
        else 1.0
    )
    by_type = {"physical": 0.0, "magic": 0.0, "true": 0.0}
    sustain = attack_bonus = speed_bonus = 0.0
    for p in parts:
        kind = p["kind"]
        if kind in ("attack_bonus", "attack_speed"):
            d = p.get("duration")
            uptime = min(1.0, d * casts / t) if d else 1.0
            if kind == "attack_bonus":
                attack_bonus += p["value"] * uptime
            else:
                speed_bonus += p["value"] * uptime
            continue
        per, d = p.get("per", "cast"), p.get("duration")
        if per == "cast":
            count = casts
        elif per == "second":
            count = d * casts if d else t
        elif per == "attack":
            count = s.attack_speed * (d * casts if d else t)
        else:  # once a fight
            count = 1.0
        chance = p.get("chance", 1.0)
        if isinstance(chance, str):  # a record may name the assumption for its condition
            if chance not in CHANCE_ASSUMPTIONS:
                raise KeyError(f"ability {s.unit}: chance {chance!r} is not a known assumption")
            chance = a[chance]
        times = p.get("times", 1)
        if p.get("times_per_bonus_as"):  # Aphelios: one more swipe per 20% bonus Attack Speed
            times += max(0.0, as_ratio - 1) / p["times_per_bonus_as"]
        if p.get("terms"):  # the formula by stat replaces the tooltip total
            value = sum(x["values"][s.star - 1] * term_stat[x["stat"]] for x in p["terms"])
            scale_by_type = False
        else:
            value = p["values"][s.star - 1]
            scale_by_type = True
        amount = value * times * chance * count
        if kind == "damage":
            scale = {"physical": ad_ratio, "magic": ap_ratio, "true": 1.0}[p["type"]]
            if not scale_by_type:
                scale = 1.0
            # damage over time: casts and attacks are spread over the fight, so on average
            # half the fight is left for it to land
            landed = min(1.0, t / 2 / p["over"]) if p.get("over") else 1.0
            hits = _targets(p.get("hits", "single"), a)
            by_type[p["type"]] += amount * hits * scale * landed * ability_crit / t
        elif kind == "health":
            sustain += amount
        else:  # shield, heal: AP unless the record names its ratios
            scale = 1.0
            for r in p.get("scales", ["ap"]) if scale_by_type else []:
                scale *= ratios[r]
            sustain += amount * scale * a["power_sustain_weight"]
    by_type["physical"] += attacks * (1 + attack_bonus) * (1 + speed_bonus)
    by_type["magic"] += ex.when_hit_damage
    phys, magic, true = (by_type[k] * amp for k in ("physical", "magic", "true"))
    dps = phys + magic + true
    ehp += sustain + s.omnivamp * dps * t
    return UnitPower(s.unit, dps, ehp, casts, "record", phys, magic, true)


def _stand_in(kb, s, a, star_ad, t, attacks, casts, amp, ehp, ex) -> UnitPower:
    """Ability by cost and star, for patches without ability records."""
    c = kb.champions[s.unit]
    text = c["ability"].get("text") or ""
    tank = "tank" in profile(kb, s.unit).tags
    base = a["power_ability_base"][c["cost"]] * a["power_ability_star"][s.star]
    physical = "scaleAD" in text
    if physical:
        base_ad = (c["stats"].get("damage") or 0) * star_ad
        scale = s.ad / base_ad if base_ad else 1.0
    else:
        scale = s.ap / 100
    ability = base * scale * casts
    phys, magic = attacks * amp, ex.when_hit_damage * amp
    if tank:
        ehp += a["power_tank_ability_share"] * ability
    elif physical:
        phys += ability / t * amp
    else:
        magic += ability / t * amp
    dps = phys + magic
    ehp += s.omnivamp * dps * t
    return UnitPower(s.unit, dps, ehp, casts, "stand-in", phys, magic, 0.0)


def adaptor_forms(kb, units: list[tuple[str, int]], a: AssumptionSet) -> tuple[dict, list]:
    """Fixed forms (assumption or a single recorded form) and the units that pick the stronger."""
    fixed: dict[str, str] = {}
    open_: list[str] = []
    for u, _ in units:
        forms = (kb.ability(u) or {}).get("forms") or {}
        if not forms:
            continue
        want = a["power_adaptor_form"].get(u)
        if want in forms:
            fixed[u] = want
        elif len(forms) == 1:
            fixed[u] = next(iter(forms))
        else:
            open_.append(u)
    return fixed, open_


def _merge(a: dict, b: dict) -> dict:
    out = {u: dict(v) for u, v in a.items()}
    for u, v in b.items():
        for k, x in v.items():
            out.setdefault(u, {})[k] = out.get(u, {}).get(k, 0.0) + x
    return out


def board_power(
    stats: BoardStats,
    units: list[tuple[str, int]],
    items: dict[str, list[str]] | None = None,
    emblems: dict[str, list[str]] | None = None,
    a: AssumptionSet | None = None,
) -> BoardPower:
    a = a or AssumptionSet()
    kb = stats.kb
    t = a["power_fight_seconds"]
    ids = [u for u, _ in units]
    extra, extras, team = item_extras(kb, ids, items or {}, a)
    fixed, open_ = adaptor_forms(kb, units, a)

    def run(form: str):
        forms = {**fixed, **dict.fromkeys(open_, form)}
        st, tr = stats.compute(units, items, emblems, forms, extra)
        if any(ex.stacks or ex.crit_stacks for ex in extras.values()):
            st, tr = stats.compute(
                units, items, emblems, forms, _merge(extra, stack_extras(st, extras, a))
            )
        ps = [unit_power(kb, x, a, stats.mult["ad"][x.star - 1], extras.get(x.unit)) for x in st]
        return st, tr, ps

    unit_stats, traits, powers = run("ap")
    if open_:  # a unit's form changes only its own stats, so pick per unit
        ad_stats, _, ad_powers = run("ad")
        for i, x in enumerate(unit_stats):
            if x.unit in open_:
                ap_p, ad_p = powers[i], ad_powers[i]
                if ad_p.dps * ad_p.ehp > ap_p.dps * ap_p.ehp:
                    unit_stats[i], powers[i] = ad_stats[i], ad_p
    # enemies: Armor and MR after the board's Sunder and Shred; one Burn on the board
    armor = a["power_enemy_armor"] * (1 - team.reduce_armor)
    mr = a["power_enemy_mr"] * (1 - team.reduce_mr)
    burn = team.burn * a["power_enemy_unit_health"]
    parts = []
    ehp_bonus = 0.0
    for p in powers:
        dps = p.physical * 100 / (100 + armor) + p.magic * 100 / (100 + mr) + p.true
        if p.unit == team.burn_holder:
            dps += burn
        ex = extras.get(p.unit)
        if ex and ex.heal_damage:  # heals allies for a share of the holder's damage
            ehp_bonus += ex.heal_damage * dps * t * a["power_sustain_weight"]
        parts.append(replace(p, dps=dps))
    dps = sum(p.dps for p in parts)
    ehp = sum(p.ehp for p in parts) + ehp_bonus
    return BoardPower(math.sqrt(max(dps, 0) * max(ehp, 0)), dps, ehp, tuple(parts),
                      tuple(traits), tuple(unit_stats), team)  # fmt: skip
