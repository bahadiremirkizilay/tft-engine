"""Every number P1 needs that is not game data is an assumption, listed here.

Each scalar assumption has a default and a low/high range. The sensitivity
report re-runs the evaluation at both ends of each range and shows which
assumptions change the recommended decision. None of these values come from
data yet; later milestones (M4, M5, M6) replace them with estimates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Assumption:
    default: Any
    low: Any = None
    high: Any = None
    description: str = ""
    # where the value comes from (owner, observation, a source id, "guess"); required for
    # new assumptions (the audit checks it), shown in docs/VARSAYIMLAR.md
    basis: str = ""
    # how it could be checked or replaced (an in-game count, a stats site, a later milestone)
    validate_by: str = ""

    @property
    def varied(self) -> bool:
        return self.low is not None and self.high is not None


DEFAULTS: dict[str, Assumption] = {
    # --- decision policy -------------------------------------------------
    "horizon_rounds": Assumption(3, 2, 4, "player-combat rounds looked ahead"),
    "roll_floor": Assumption(0, 0, 20, "rolling stops below this gold (candidates A and D)"),
    # --- board strength (replaced by M4) ---------------------------------
    "unit_power_cost_exp": Assumption(1.0, 0.7, 1.3, "unit power grows as cost ** this"),
    "star_mult_2": Assumption(1.8, 1.5, 2.2, "2-star unit power vs 1-star"),
    "star_mult_3": Assumption(5.0, 3.5, 6.5, "3-star unit power vs 1-star"),
    "comp_complete_bonus": Assumption(0.15, 0.0, 0.3, "strength bonus when a target comp is done"),
    # --- combat and opponents (replaced by M5, M6) -----------------------
    "win_prob_slope": Assumption(4.0, 2.0, 6.0, "how fast win chance rises with strength ratio"),
    "opp_strength_scale": Assumption(1.0, 0.8, 1.25, "multiplier on unseen opponents' strength"),
    "damage_scale": Assumption(1.0, 0.7, 1.4, "multiplier on HP lost per lost round"),
    "pool_depletion_scale": Assumption(1.0, 0.5, 1.5, "multiplier on copies held by unseen boards"),
    # --- how outcomes are weighed (HP-equivalent units) ------------------
    "elim_penalty_hp": Assumption(100.0, 50.0, 200.0, "cost of being eliminated, in HP"),
    "gold_value_hp": Assumption(
        0.5, 0.25, 1.0, "value of 1 gold at the horizon end, up to the interest cap, in HP"
    ),
    "excess_gold_value_hp": Assumption(
        0.25, 0.1, 0.5, "value of 1 gold above the interest cap (earns no interest), in HP"
    ),
    "level_value_hp": Assumption(4.0, 2.0, 8.0, "value of 1 level at the horizon end, in HP"),
    "future_rounds": Assumption(
        6, 3, 10, "rounds after the horizon in which the final board still decides fights"
    ),
    # --- tables, not varied one by one ------------------------------------
    "surviving_units_on_loss_by_stage": Assumption(
        {1: 0, 2: 2, 3: 2, 4: 2, 5: 3, 6: 4, 7: 4},
        description="enemy units left alive when a round is lost, by stage (damage = the "
        "set's stage damage + 1 per unit, from the game data)",
    ),
    "opp_level_by_stage": Assumption(
        {1: 3, 2: 4, 3: 6, 4: 7, 5: 8, 6: 8, 7: 9},
        description="typical opponent level by stage",
    ),
    "opp_unit_power_by_stage": Assumption(
        {1: 1.0, 2: 1.6, 3: 3.2, 4: 5.0, 5: 6.5, 6: 7.5, 7: 8.0},
        description="typical opponent unit power by stage, same scale as unit_power",
    ),
    "tier_taken_frac_by_stage": Assumption(
        {
            1: (0.05, 0.0, 0.0, 0.0, 0.0),
            2: (0.15, 0.05, 0.0, 0.0, 0.0),
            3: (0.25, 0.15, 0.05, 0.0, 0.0),
            4: (0.25, 0.25, 0.15, 0.05, 0.0),
            5: (0.2, 0.25, 0.25, 0.15, 0.05),
        },
        description="share of other copies per cost held by unseen boards, by stage",
    ),
    # --- item fit (B4): how much each item stat suits a champion profile ------
    "item_fit_weights": Assumption(
        {
            # profile -> stat -> weight; a stat counts when the item has it at all
            "ad": {"ad_pct": 2, "as_pct": 1, "crit_pct": 1, "damage_amp_pct": 1, "ap": 0},
            "ap": {"ap": 2, "mana_regen": 1, "damage_amp_pct": 1, "ad_pct": -1, "as_pct": 0},
            "frontline": {
                "hp": 1,
                "armor": 1,
                "mr": 1,
                "durability_pct": 1,
                "damage_reduction_pct": 1,
                "omnivamp_pct": 1,
            },
            "backline": {"hp": 0, "armor": 0, "mr": 0, "durability_pct": 0},
            # used instead of "ad"/"ap" when the champion's role is a tank
            "tank": {"hp": 1, "armor": 1, "mr": 1, "durability_pct": 1, "mana_regen": 1},
            # used instead of "ad"/"ap" for utility champions (role Specialist): more casts
            "utility": {"mana_regen": 2, "mana_effect": 2, "ap": 1},
            # added for Marksmen: their damage comes from attacks
            "marksman": {"as_pct": 1},
            # fighters get damage stats at this share (owner: Nashor's belongs on a carry)
            "fighter_damage_scale": 0.6,
            # attack range up to this counts as frontline
            "frontline_max_range": 2,
            # an item's stat counts at value / typical value, kept within these bounds
            "scale_min": 0.5,
            "scale_max": 2.0,
        },
        description="item fit rule weights by champion profile (rule-based, not statistics)",
    ),
    # --- comp matching (B5) ------------------------------------------------
    "comp_match_weights": Assumption(
        {"units": 1.0, "items": 0.3, "unit_cost_exp": 1.0, "min_components": 4},
        description="comp match score: share of the comp's units owned (weighted by cost ** "
        "unit_cost_exp) and share of held components (counted as at least min_components) "
        "that its carries' items use",
    ),
    # --- simple game simulation (sim/), not real TFT combat -----------------
    "sim_trait_bonus": Assumption(
        0.10, 0.05, 0.15, "board power bonus per active trait breakpoint step (simulation)"
    ),
    "sim_level_curve": Assumption(
        {"2-1": 4, "2-5": 5, "3-2": 6, "3-5": 7, "4-2": 8, "5-2": 9},
        description="stage at which the simulated player levels to at least this level",
    ),
    "sim_slow_roll_floor": Assumption(
        50,
        30,
        50,
        "slow roll stays above this gold",
        basis="owner's habit: slow roll above 50, may drop to 30",
    ),
    "sim_low_hp": Assumption(40, 25, 55, "below this HP the simulated player rolls deep"),
    "sim_deep_roll_floor": Assumption(10, 0, 20, "gold kept when rolling deep"),
    "sim_item_min_fit": Assumption(
        2.0, 1.0, 3.0, "below this fit no holder suits the item: keep the components"
    ),
    "sim_no_items_before": Assumption(
        "2-1",
        description="no items are crafted before this round (owner: stage 1 is won anyway)",
        basis="owner's review of a simulated game",
    ),
    "sim_lose_streak_hp": Assumption(
        60, 50, 75, "early loss streak (or Coven) keeps saving gold while HP is at least this"
    ),
    "sim_rolldown_floor": Assumption(20, 10, 30, "gold kept in the level 8 roll-down (from 4-2)"),
    "sim_excess_gold": Assumption(60, 50, 80, "above this gold, spend the excess on XP or rolls"),
    "sim_trait_progress": Assumption(
        1.0, 0.5, 2.0, "weight of trait progress among all owned units when buying"
    ),
    "sim_shop_trait_weight": Assumption(
        2.0, 1.0, 3.0, "extra weight of breakpoints that change the shop (5 Riftbeast, 5 Blossom)"
    ),
    "sim_components_per_monster_round": Assumption(
        2,
        1,
        3,
        "components dropped by each x-7 monster round (owner: many items drop)",
        basis="owner's review of a simulated game",
        validate_by="count drops in a few real games (templates/oyun_ici_kontrol.md)",
    ),
    "sim_carousel_round": Assumption(
        4, description="round x-4 is a carousel giving one component (no champion modelled)"
    ),
    "sim_carry_needs_items_value": Assumption(
        0.5, 0.25, 1.0, "share of a 4-5 cost carry's value when the held items do not suit it"
    ),
    "sim_one_short_step": Assumption(
        0.5,
        0.25,
        0.75,
        "trait step value counted when one unit short of the next breakpoint",
        basis="guess (simulation policy, 2026-10-21)",
    ),
    "sim_trait_value_floor": Assumption(
        3.0,
        1.0,
        5.0,
        "board power floor used to value trait progress early in the game",
        basis="guess (simulation policy, 2026-10-21)",
    ),
    "sim_pair_value": Assumption(
        0.3,
        0.1,
        0.5,
        "value of a copy toward a star-up, as a share of the unit's cost",
        basis="guess (simulation policy, 2026-10-21)",
    ),
    "sim_star_up_value": Assumption(
        0.5,
        0.25,
        1.0,
        "least value of a buy that completes a star-up, share of the unit's cost",
        basis="guess (simulation policy, 2026-10-21)",
    ),
    "sim_interest_break_gain": Assumption(
        0.15,
        0.05,
        0.3,
        "gain (share of board power) worth dropping below an interest step",
        basis="guess (simulation policy, 2026-10-21)",
    ),
    "sim_item_holder_weight": Assumption(
        0.1,
        0.0,
        0.3,
        "weight of a holder's unit value next to item fit when crafting",
        basis="guess (simulation policy, 2026-10-21)",
    ),
    "sim_survivor_share": Assumption(
        0.3,
        0.2,
        0.5,
        "share of the winner's board alive after an even fight (simulation)",
        basis="guess (simulation combat, 2026-10-21)",
    ),
    "sim_idle_holder_factor": Assumption(
        0.6, 0.4, 1.0, "item fit multiplier for a holder that adds to no active trait"
    ),
    # --- board power from unit stats (B6), until ability values and combat exist ---
    "power_fight_seconds": Assumption(20, 15, 30, "length of a typical player combat"),
    "power_mana_per_attack": Assumption(10, 5, 10, "mana gained per attack (not in the game data)"),
    "power_ability_base": Assumption(
        {1: 250, 2: 330, 3: 420, 4: 550, 5: 750},
        description="ability damage per cast of a 1-star carry at base AD/AP, by cost "
        "(stand-in until ability values are recorded)",
    ),
    "power_ability_star": Assumption(
        {1: 1.0, 2: 1.5, 3: 2.5}, description="ability value per star relative to 1-star"
    ),
    "power_tank_ability_share": Assumption(
        0.6, 0.3, 1.0, "share of a tank's ability value counted as extra Health (shields, heals)"
    ),
    "power_resist_weight": Assumption(
        1.0, 0.7, 1.3, "how much average Armor/MR raise effective Health: hp x (1 + w x resist/100)"
    ),
    "power_attack_count_mana": Assumption(
        5,
        3,
        10,
        "a mana bar this small counts attacks (every third attack ...), not mana",
        basis="guess from Caitlyn and Master Yi texts (2026-10-21)",
        validate_by="in game: how often a 3-mana unit casts",
    ),
    "power_min_cast_seconds": Assumption(
        1.5,
        1.0,
        2.5,
        "at most one cast every this many seconds (cast time, mana lock)",
        basis="guess (2026-10-21)",
    ),
    "power_default_crit_mult": Assumption(
        1.4,
        description="crit damage multiplier when a champion record has none",
        basis="guess; CommunityDragon records usually carry critMultiplier",
    ),
    "power_min_damage_taken": Assumption(
        0.1,
        description="durability never reduces damage taken below this share (guard)",
        basis="guess; keeps effective Health finite",
    ),
    "power_aoe_targets": Assumption(
        2.0,
        1.5,
        3.0,
        "enemies an area ability (radius, cone, adjacent) hits on average",
        basis="guess (2026-10-22); ability records say only the shape",
        validate_by="damage charts after fights, per ability",
    ),
    "power_line_targets": Assumption(
        1.5,
        1.0,
        2.5,
        "enemies a line or piercing ability hits on average, after its falloff",
        basis="guess (2026-10-22); most lines lose 20-80% per enemy passed",
        validate_by="damage charts after fights, per ability",
    ),
    "power_conditional_share": Assumption(
        0.5,
        0.25,
        0.75,
        "share of casts where an ability's stated condition holds (Soraka's extra stars)",
        basis="guess (2026-10-22)",
    ),
    "power_dot_landed_share": Assumption(
        0.5,
        0.3,
        0.7,
        "share of the fight left, on average, for a damage-over-time cast to land",
        basis="casts and attacks spread evenly over the fight (2026-10-23)",
    ),
    "power_sustain_weight": Assumption(
        0.7,
        0.5,
        1.0,
        "share of ability shields and heals counted as effective Health (overheal, expiry)",
        basis="guess (2026-10-22)",
    ),
    "power_adaptor_form": Assumption(
        {"DA_Nidalee18_AP": "ad", "DA_Gromp18_AP": "ap"},
        description="Adaptor form per champion; champions not listed take the stronger form",
        basis="owner 2026-10-21/22: Nidalee is played AD, Gromp AP",
    ),
    "power_enemy_armor": Assumption(
        60,
        30,
        100,
        "average Armor of the enemy units your damage hits (physical damage x 100/(100+Armor))",
        basis="guess (2026-10-23): unit base Armor 20-70 plus trait and item Armor",
        validate_by="enemy unit panels in the owner's screenshots",
    ),
    "power_enemy_mr": Assumption(
        60,
        30,
        100,
        "average Magic Resist of the enemy units your damage hits",
        basis="guess (2026-10-23), as power_enemy_armor",
        validate_by="enemy unit panels in the owner's screenshots",
    ),
    "power_enemy_unit_health": Assumption(
        2000,
        1200,
        3500,
        "max Health of the enemy a Burn sits on (Burn deals % of max Health)",
        basis="guess (2026-10-23): 2-star 3- and 4-cost units in the late game",
    ),
    "power_enemy_tank_share": Assumption(
        0.4,
        0.25,
        0.6,
        "share of your damage that goes into enemy Tanks (Giant Slayer)",
        basis="guess (2026-10-23)",
    ),
    "power_enemy_attack_damage_share": Assumption(
        0.6,
        0.4,
        0.8,
        "share of the damage a unit takes that comes from attacks (Bramble Vest)",
        basis="guess (2026-10-23)",
    ),
    "power_upper_health_share": Assumption(
        0.5,
        0.3,
        0.7,
        "share of a fight a unit spends above half Health (Hand of Justice, Steadfast Heart)",
        basis="guess (2026-10-23)",
    ),
    "power_missing_health_share": Assumption(
        0.4,
        0.25,
        0.6,
        "average share of max Health a unit is missing during a fight (missing-Health regen)",
        basis="guess (2026-10-23)",
    ),
    "power_hits_taken_per_second": Assumption(
        1.0,
        0.5,
        2.0,
        "times a unit is hit per second (Titan's Resolve stacks on attacks and hits taken)",
        basis="guess (2026-10-23)",
    ),
    "power_targeting_enemies": Assumption(
        2,
        1,
        3,
        "enemies targeting the holder at once (Gargoyle Stoneplate)",
        basis="guess (2026-10-23); the Monolith trait model uses the same idea",
    ),
    "power_extra_precision_crit": Assumption(
        0.10,
        description="crit damage each extra Precision source adds",
        basis="item text: extra Precision grants 10% Critical Strike Damage",
    ),
    # --- board builder (best board for a level, from the engine's own rules) ---
    "build_cost_caps": Assumption(
        {7: {4: 2, 5: 0}, 8: {4: 4, 5: 1}, 9: {4: 5, 5: 3}},
        description="most 4- and 5-cost units a board can hold at a level (from shop odds)",
    ),
    "build_stars": Assumption(
        {
            7: {1: 2, 2: 2, 3: 2, 4: 1, 5: 1},
            8: {1: 2, 2: 2, 3: 2, 4: 2, 5: 1},
            9: {1: 2, 2: 2, 3: 2, 4: 2, 5: 1},
        },
        description="star level per unit cost on a finished board at a level",
        basis="owner 2026-10-22: a finished level 8 comp aims for 2-star 4-costs "
        "(luck and economy move it game to game)",
    ),
    "build_item_copies": Assumption(
        2,
        1,
        3,
        "most copies of one completed item on a built board",
        basis="owner 2026-10-23: the same item is built twice",
    ),
    "build_random_item_samples": Assumption(
        12,
        description="random item pairs averaged to value Thief's Gloves",
        basis="setting: enough pairs for a stable average, few enough to stay fast",
    ),
    "build_item_candidates": Assumption(
        4,
        description="strongest carries and tanks tried as item holders (search width)",
        basis="setting: keeps the item search fast",
    ),
    "build_item_slots": Assumption(
        (3, 3, 2), description="items for the main carry, the main tank and a second carry"
    ),
    # --- Set 18 shop (owner, 18.4b): a Wisp shows in the rightmost slot ------
    "wisp_shop_prob": Assumption(
        None,
        0.25,
        1.0,
        "chance a shop shows a Wisp (None = set data: every other shop)",
        basis="set data shop rule wisp_slot; owner's observation 18.4b",
        validate_by="count Wisp shops over many rolls in game",
    ),
    "wisp_price": Assumption(1, 0, 3, "gold paid for the cheapest Wisp when buying one to roll"),
}


def _stage_table(value: Mapping) -> dict[int, Any]:
    return {int(k): v for k, v in value.items()}


class AssumptionSet:
    """Defaults plus overrides; records which values were overridden."""

    def __init__(self, overrides: Mapping[str, Any] | None = None) -> None:
        overrides = dict(overrides or {})
        unknown = set(overrides) - set(DEFAULTS)
        if unknown:
            raise KeyError(f"unknown assumptions: {sorted(unknown)}")
        self.overrides = overrides
        self.values = {k: a.default for k, a in DEFAULTS.items()}
        self.values.update(overrides)
        for k in self.values:
            if k.endswith("_by_stage"):
                self.values[k] = _stage_table(self.values[k])

    def __getitem__(self, name: str) -> Any:
        return self.values[name]

    def with_value(self, name: str, value: Any) -> AssumptionSet:
        return AssumptionSet({**self.overrides, name: value})

    def by_stage(self, name: str, major: int) -> Any:
        table = self.values[name]
        if major in table:
            return table[major]
        return table[max(k for k in table if k <= major)] if major > 0 else table[min(table)]

    def key(self) -> tuple:
        return tuple(sorted((k, repr(v)) for k, v in self.values.items()))
