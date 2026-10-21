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
        0.06, 0.03, 0.10, "board power bonus per active trait breakpoint step (simulation)"
    ),
    "sim_item_bonus": Assumption(0.12, 0.06, 0.2, "power bonus per completed item on a unit"),
    "sim_level_curve": Assumption(
        {"2-1": 4, "2-5": 5, "3-2": 6, "3-5": 7, "4-2": 8, "5-2": 9},
        description="stage at which the simulated player levels to at least this level",
    ),
    "sim_slow_roll_floor": Assumption(50, 30, 50, "slow roll stays above this gold"),
    "sim_low_hp": Assumption(40, 25, 55, "below this HP the simulated player rolls deep"),
    "sim_deep_roll_floor": Assumption(10, 0, 20, "gold kept when rolling deep"),
    # --- Set 18 shop (owner, 18.4b): a Wisp shows in the rightmost slot ------
    "wisp_shop_prob": Assumption(
        None, 0.25, 1.0, "chance a shop shows a Wisp (None = set data: every other shop)"
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
