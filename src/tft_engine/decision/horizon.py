"""Look a few player-combat rounds ahead by enumerating win/loss sequences.

The board is held fixed after the decision (no more buying), passive XP and
income follow the economy rules, and each round is won with the lobby win
chance of the current board. Assumptions: every round is a player combat
(carousel and monster rounds are skipped), stages have 7 rounds.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.strength import board_strength, lobby_win_prob, opponent_strength_prior
from tft_engine.rules import Rules
from tft_engine.state import GameState, UnitInstance


def next_stage(stage: str) -> str:
    major, minor = (int(x) for x in stage.split("-"))
    return f"{major + 1}-1" if minor >= 7 else f"{major}-{minor + 1}"


@dataclass(frozen=True)
class HorizonResult:
    p_win_first: float
    exp_gold_end: float
    exp_gold_excess_end: float  # part of the gold above the interest cap
    exp_level_end: float
    exp_hp_lost: float
    p_elim: float
    exp_strength_ratio_end: float  # own strength / typical opponent strength
    exp_future_loss_per_round: float  # HP lost per round after the horizon, if the board stays


def simulate(
    state: GameState,
    rules: Rules,
    comps: list[tuple[UnitInstance, ...]],
    observed: list[float],
    alive: int,
    a: AssumptionSet,
    extra_income: int = 0,
) -> HorizonResult:
    rounds = a["horizon_rounds"]
    acc = {
        "gold": 0.0,
        "level": 0.0,
        "hp": 0.0,
        "elim": 0.0,
        "ratio": 0.0,
        "future": 0.0,
        "excess": 0.0,
    }
    first = {}
    cap_gold = rules.param("interest_cap") * 10 // rules.param("interest_per_10_gold")

    def strength(s: GameState) -> float:
        return board_strength(s.units, s.level, comps, a)

    def finish(s: GameState, p: float, hp_lost: int, elim: bool) -> None:
        major = s.stage_round[0]
        acc["gold"] += p * s.gold
        acc["excess"] += p * max(0, s.gold - cap_gold)
        acc["level"] += p * s.level
        acc["hp"] += p * hp_lost
        acc["elim"] += p * elim
        if elim:
            return
        me = strength(s)
        acc["ratio"] += p * me / opponent_strength_prior(major, a)
        pw = lobby_win_prob(me, observed, alive, major, a)
        acc["future"] += p * (1 - pw) * a.by_stage("damage_by_stage", major) * a["damage_scale"]

    def step(s: GameState, p: float, r: int, hp_lost: int) -> None:
        if r == rounds:
            finish(s, p, hp_lost, False)
            return
        major = s.stage_round[0]
        pw = lobby_win_prob(strength(s), observed, alive, major, a)
        if r == 0:
            first["p"] = pw
        nxt = next_stage(s.stage)
        won = rules.end_round(s, True, nxt)
        step(replace(won, gold=won.gold + extra_income), p * pw, r + 1, hp_lost)
        dmg = round(a.by_stage("damage_by_stage", major) * a["damage_scale"])
        hp = s.hp - dmg
        if hp <= 0:
            finish(s, p * (1 - pw), hp_lost + s.hp, True)
            return
        lost = rules.end_round(replace(s, hp=hp), False, nxt)
        step(replace(lost, gold=lost.gold + extra_income), p * (1 - pw), r + 1, hp_lost + dmg)

    step(state, 1.0, 0, 0)
    return HorizonResult(
        p_win_first=first.get("p", 0.0),
        exp_gold_end=acc["gold"],
        exp_gold_excess_end=acc["excess"],
        exp_level_end=acc["level"],
        exp_hp_lost=acc["hp"],
        p_elim=acc["elim"],
        exp_strength_ratio_end=acc["ratio"],
        exp_future_loss_per_round=acc["future"],
    )
