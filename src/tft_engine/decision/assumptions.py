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
    "damage_by_stage": Assumption(
        {1: 0, 2: 4, 3: 7, 4: 10, 5: 13, 6: 16, 7: 19},
        description="HP lost per lost round by stage (Set 18 values unknown)",
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
    "wisp_takes_slot": Assumption(
        None, False, True, "a Wisp takes a champion slot (None = follow set data)"
    ),
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
