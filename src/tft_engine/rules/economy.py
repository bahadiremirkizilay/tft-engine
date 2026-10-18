"""Economy transitions: income, interest, streaks, XP, buying and rolling.

``Rules`` reads every number from ``GameData``. A scenario may override a
parameter (for example a value not yet verified); every parameter actually
read is recorded in ``used`` together with its trust status, so each result
can say what it relied on.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from tft_engine.gamedata import GameData, Param
from tft_engine.state import GameState, UnitInstance


@dataclass
class Rules:
    data: GameData
    overrides: Mapping[str, Any] = field(default_factory=dict)
    used: dict[str, str] = field(default_factory=dict)  # param name -> status

    def param(self, name: str) -> Any:
        if name in self.overrides:
            self.used[name] = "assumption"
            return self.overrides[name]
        p: Param = self.data.param(name)
        value = p.get()  # raises UnknownMechanicError for unknown values
        self.used[name] = p.status
        return value

    # --- gold -----------------------------------------------------------

    def interest(self, gold: int) -> int:
        per10 = self.param("interest_per_10_gold")
        cap = self.param("interest_cap")
        return min((gold // 10) * per10, cap)

    def streak_bonus(self, streak: int) -> int:
        """streak_gold format: [[min_streak_length, gold], ...], ascending."""
        length = abs(streak)
        bonus = 0
        for min_len, gold in self.param("streak_gold"):
            if length >= min_len:
                bonus = gold
        return bonus

    def base_income(self, stage: str) -> int:
        """base_income format: {"default": g, "by_stage": {"1-2": g, ...}}."""
        table = self.param("base_income")
        return table.get("by_stage", {}).get(stage, table["default"])

    @staticmethod
    def next_streak(streak: int, won: bool) -> int:
        if won:
            return streak + 1 if streak > 0 else 1
        return streak - 1 if streak < 0 else -1

    def round_income(self, state: GameState, won: bool, next_stage: str) -> int:
        """Gold gained after a player-combat round.

        Timing assumption (not verified): the streak bonus uses the streak after this
        round's result, base income uses the stage that starts next, and interest uses
        the gold held after combat. Win and loss streaks pay the same bonus.
        """
        income = self.base_income(next_stage) + self.interest(state.gold)
        income += self.streak_bonus(self.next_streak(state.streak, won))
        if won:
            income += self.param("pvp_win_gold")
        return income

    def end_round(self, state: GameState, won: bool, next_stage: str) -> GameState:
        """Apply income, passive XP and streak update for one combat round."""
        gold = state.gold + self.round_income(state, won, next_stage)
        streak = self.next_streak(state.streak, won)
        level, xp = self.add_xp(state.level, state.xp, self.param("passive_xp_per_round"))
        return replace(state, gold=gold, streak=streak, level=level, xp=xp, stage=next_stage)

    # --- xp and levels ----------------------------------------------------

    def add_xp(self, level: int, xp: int, gained: int) -> tuple[int, int]:
        """xp_to_next_level format: {"2": xp needed to go from 2 to 3, ...}."""
        table = self.param("xp_to_next_level")
        max_level = self.param("max_level")
        xp += gained
        while level < max_level:
            need = table[str(level)]
            if xp < need:
                break
            xp -= need
            level += 1
        if level >= max_level:
            xp = 0
        return level, xp

    def buy_xp(self, state: GameState) -> GameState:
        cost = self.param("xp_purchase")
        if state.gold < cost["gold"]:
            raise ValueError("not enough gold to buy XP")
        level, xp = self.add_xp(state.level, state.xp, cost["xp"])
        return replace(state, gold=state.gold - cost["gold"], level=level, xp=xp)

    # --- shop actions -----------------------------------------------------

    def reroll(self, state: GameState) -> GameState:
        cost = self.param("reroll_cost")
        if state.gold < cost:
            raise ValueError("not enough gold to reroll")
        return replace(state, gold=state.gold - cost)

    def buy_unit(self, state: GameState, unit_id: str, cost: int) -> GameState:
        """Buy one 1-star copy and combine 3 equal copies into the next star."""
        if state.gold < cost:
            raise ValueError("not enough gold to buy unit")
        units = list(state.units) + [UnitInstance(unit_id, cost, 1)]
        for star in (1, 2):
            same = [u for u in units if u.unit_id == unit_id and u.star == star]
            if len(same) >= 3:
                for u in same[:3]:
                    units.remove(u)
                units.append(UnitInstance(unit_id, cost, star + 1))
        return replace(state, gold=state.gold - cost, units=tuple(units))
