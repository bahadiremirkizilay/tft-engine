"""Economy transitions: income, interest, streaks, XP, buying and rolling.

``Rules`` reads every number from ``GameData``. A scenario may override a
parameter (for example a value not yet verified); every parameter actually
read is recorded in ``used`` together with its trust status, so each result
can say what it relied on.

Augments and similar effects change the rules through ``modifiers`` (a
``ModifierSet``): parameter modifiers are applied on every read (their ids are
recorded in ``applied``), and events fire from the transitions below
(``end_round``, ``buy_xp``, ``gain_xp``) or from ``fire``. Effects that cannot be
valued yet (units, components, items) are listed in ``notes``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from tft_engine.gamedata import GameData, Param
from tft_engine.rules.modifiers import ModifierSet
from tft_engine.state import GameState, UnitInstance

_MAX_EVENT_DEPTH = 8  # events that trigger events (level up -> XP -> level up ...)


@dataclass
class Rules:
    data: GameData
    overrides: Mapping[str, Any] = field(default_factory=dict)
    modifiers: ModifierSet = field(default_factory=ModifierSet)
    used: dict[str, str] = field(default_factory=dict)  # param name -> status
    applied: dict[str, tuple[str, ...]] = field(default_factory=dict)  # param -> modifier ids
    notes: list[str] = field(default_factory=list)

    def param(self, name: str) -> Any:
        if name in self.overrides:
            self.used[name] = "assumption"
            value = self.overrides[name]
        else:
            p: Param = self.data.param(name)
            value = p.get()  # raises UnknownMechanicError for unknown values
            self.used[name] = p.status
        if self.modifiers:
            value, ids = self.modifiers.apply(name, value)
            if ids:
                self.applied[name] = ids
        return value

    # --- events -----------------------------------------------------------

    def fire(
        self, trigger: str, state: GameState, level: int | None = None, depth: int = 0
    ) -> GameState:
        """Apply every event for ``trigger`` that holds now; ``level`` for level-up events."""
        if not self.modifiers.events:
            return state
        if depth > _MAX_EVENT_DEPTH:
            raise RuntimeError(f"events keep triggering each other ({trigger})")
        lvl = state.level if level is None else level
        counts = dict(state.event_counts)
        for e in self.modifiers.firing(trigger, state.stage, lvl, counts):
            for action, amount in e.do:
                state = self._act(action, amount, state, e.source, depth)
            state = state.with_fired(e.id)
        return state

    def _act(self, action: str, amount: Any, state: GameState, source: str, depth: int):
        if action == "gain_gold":
            return replace(state, gold=max(0, state.gold + amount))
        if action == "gain_xp":
            return self.gain_xp(state, amount, depth + 1)
        if action == "gain_free_rerolls":
            return replace(state, free_rerolls=state.free_rerolls + amount)
        if action == "gain_hp":
            return replace(state, hp=state.hp + amount)
        if action == "set_streak":
            return replace(state, streak=amount)
        note = f"{source}: {action} ({amount}) not valued until B4"
        if note not in self.notes:
            self.notes.append(note)
        return state

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
        """Apply income, passive XP and streak update for one combat round.

        Event order: after-combat events, then income and streak, then passive XP
        (level-up events), then the next round starts (stage-start events when the
        stage changes, then round-start events).
        """
        state = self.fire("after_combat_win" if won else "after_combat_loss", state)
        gold = state.gold + self.round_income(state, won, next_stage)
        streak = self.next_streak(state.streak, won)
        state = replace(state, gold=gold, streak=streak)
        state = self.gain_xp(state, self.param("passive_xp_per_round"))
        new_stage = next_stage.split("-")[0] != state.stage.split("-")[0]
        state = replace(state, stage=next_stage)
        if new_stage:
            state = self.fire("stage_start", state)
        return self.fire("round_start", state)

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

    def gain_xp(self, state: GameState, gained: int, depth: int = 0) -> GameState:
        """Add XP and fire a level-up event for every level gained."""
        old = state.level
        level, xp = self.add_xp(state.level, state.xp, gained)
        state = replace(state, level=level, xp=xp)
        for lvl in range(old + 1, level + 1):
            state = self.fire("level_up", state, level=lvl, depth=depth)
        return state

    def buy_xp(self, state: GameState) -> GameState:
        cost = self.param("xp_purchase")
        if state.gold < cost["gold"]:
            raise ValueError("not enough gold to buy XP")
        state = replace(state, gold=state.gold - cost["gold"])
        state = self.gain_xp(state, cost["xp"])
        return self.fire("buy_xp", state)

    # --- selling and damage ----------------------------------------------

    def sell_value(self, cost: int, star: int) -> int:
        """sell_value format: {"<cost>": [1-star, 2-star, 3-star gold]}."""
        table = self.param("sell_value")
        try:
            return table[str(cost)][star - 1]
        except (KeyError, IndexError):
            raise ValueError(f"no sell value for a {star}-star {cost}-cost unit") from None

    def sell_unit(self, state: GameState, unit_id: str, star: int = 1) -> GameState:
        """Sell one owned unit of this star level."""
        units = list(state.units)
        for u in units:
            if u.unit_id == unit_id and u.star == star:
                units.remove(u)
                gold = state.gold + self.sell_value(u.cost, star)
                return replace(state, gold=gold, units=tuple(units))
        raise ValueError(f"no {star}-star {unit_id} to sell")

    def player_damage(self, stage: int, surviving_enemy_units: int) -> int:
        """Damage taken after losing a player combat in this stage.

        player_damage format: {"stage_damage": {"<stage>": dmg}, "per_surviving_unit": n}.
        """
        table = self.param("player_damage")
        try:
            base = table["stage_damage"][str(stage)]
        except KeyError:
            raise ValueError(f"no stage damage for stage {stage}") from None
        return base + table["per_surviving_unit"] * surviving_enemy_units

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
