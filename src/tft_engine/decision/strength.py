"""Board strength and win chance: a configurable heuristic (assumption class).

This is a placeholder for M4 (board strength from data) and M5/M6
(opponents, combat). Its job in P1 is to be explicit and easy to vary, so the
sensitivity report can show how much decisions depend on it.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.state import UnitInstance


def unit_power(u: UnitInstance, a: AssumptionSet) -> float:
    star = {1: 1.0, 2: a["star_mult_2"], 3: a["star_mult_3"]}[u.star]
    return (u.cost ** a["unit_power_cost_exp"]) * star


def best_star(units: Iterable[UnitInstance], unit_id: str) -> int:
    return max((u.star for u in units if u.unit_id == unit_id), default=0)


def comp_complete(units: tuple[UnitInstance, ...], comp_units: tuple[UnitInstance, ...]) -> bool:
    return all(best_star(units, cu.unit_id) >= cu.star for cu in comp_units)


def board_strength(
    units: tuple[UnitInstance, ...],
    level: int,
    comps: Iterable[tuple[UnitInstance, ...]],
    a: AssumptionSet,
) -> float:
    """Sum of the strongest `level` distinct units, plus a bonus for a finished comp."""
    best: dict[str, float] = {}
    for u in units:
        best[u.unit_id] = max(best.get(u.unit_id, 0.0), unit_power(u, a))
    s = sum(sorted(best.values(), reverse=True)[:level])
    if any(comp_complete(units, c) for c in comps):
        s *= 1 + a["comp_complete_bonus"]
    return s


def opponent_strength_prior(major: int, a: AssumptionSet) -> float:
    level = a.by_stage("opp_level_by_stage", major)
    power = a.by_stage("opp_unit_power_by_stage", major)
    return level * power * a["opp_strength_scale"]


def win_prob(me: float, opp: float, a: AssumptionSet) -> float:
    if opp <= 0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-a["win_prob_slope"] * (me / opp - 1.0)))


def lobby_win_prob(
    me: float, observed: list[float], alive: int, major: int, a: AssumptionSet
) -> float:
    """Average win chance against a uniformly drawn living opponent."""
    prior = opponent_strength_prior(major, a)
    opps = list(observed) + [prior] * (alive - len(observed))
    return sum(win_prob(me, o, a) for o in opps) / len(opps)
