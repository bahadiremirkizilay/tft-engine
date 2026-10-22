"""Build the strongest board the engine can find for a level, from its own rules.

No comp templates and no site data: the search only knows
  * board value = sum of unit power (cost x star factor, plus fitting items)
    times (1 + sim_trait_bonus x active trait steps); one-unit traits add no step;
  * which units a level can field (build_cost_caps) and at which star (build_stars);
  * emblems: the holder must not have the trait (game rule checked by the owner).
Search: greedy fill from several seeds, then swaps of board units with any
other unit while the value rises. Items go to the main carry, main tank and a
second carry by the rule-based item fit. Everything here is an assumption-class
result; it shows what the engine believes, not what is optimal in the game.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.board_power import board_power
from tft_engine.decision.item_fit import item_fit, profile
from tft_engine.gamedata import load_gamedata
from tft_engine.rules.board_stats import BoardStats
from tft_engine.rules.items import emblem_trait
from tft_engine.rules.traits import active_traits, trait_counts


@dataclass
class BuiltBoard:
    level: int
    units: list[tuple[str, int]]  # (champion id, star)
    emblem_holders: dict[str, list[str]]  # holder -> emblem item ids
    items: dict[str, list[str]] = field(default_factory=dict)  # holder -> completed items
    value: float = 0.0
    traits: list[Any] = field(default_factory=list)  # ActiveTrait, active ones
    notes: list[str] = field(default_factory=list)


class BoardBuilder:
    def __init__(
        self, kb, a: AssumptionSet | None = None, emblem_same_trait: bool = False, data=None
    ):
        self.kb = kb
        self.a = a or AssumptionSet()
        self.same = emblem_same_trait
        self.data = data or load_gamedata(kb.set_id, kb.patch)
        self.stats = BoardStats(kb, self.data)
        # unit weight per star: the set's Health multipliers (star_multipliers.hp)
        self.star_power = dict(enumerate(self.data.get("star_multipliers")["hp"], start=1))
        self.unique = {
            t["id"]
            for t in kb.traits.values()
            if max((b["min_units"] or 0 for b in t["breakpoints"]), default=0) <= 1
        }
        # one Lux at most; the base Lux has no trait of its own, so only forms are candidates
        self.candidates = [
            c["id"] for c in kb.champions.values() if c["id"] != "DA_Lux18_Base" and c.get("traits")
        ]
        self.completed = [
            i["id"] for i in kb.items.values() if i["kind"] == "completed" and i["family"] == "DA"
        ]
        self._fit: dict[tuple[str, str], float] = {}

    # --- evaluation ------------------------------------------------------------

    def fit(self, unit: str, item: str) -> float:
        if (unit, item) not in self._fit:
            self._fit[(unit, item)] = item_fit(self.kb, unit, item, self.a).score
        return self._fit[(unit, item)]

    def star(self, unit: str, level: int) -> int:
        return self.a["build_stars"][level][self.kb.champions[unit]["cost"]]

    def steps(self, counts: dict[str, int]) -> tuple[int, list]:
        traits = [t for t in active_traits(self.kb, counts) if t.active]
        total = 0
        for t in traits:
            if t.trait_id in self.unique:
                continue
            bps = sorted(
                {
                    b["min_units"]
                    for b in self.kb.traits[t.trait_id]["breakpoints"]
                    if b["min_units"]
                }
            )
            total += bps.index(t.breakpoint) + 1 if t.breakpoint in bps else 1
        return total, traits

    def value(self, units: list[str], level: int, emblems: dict[str, list[str]], items=None):
        """Board power from unit stats with traits and items (decision/board_power.py)."""
        bp = board_power(
            self.stats, [(u, self.star(u, level)) for u in units], items, emblems, self.a
        )
        return bp.power, list(bp.traits)

    # --- constraints -------------------------------------------------------------

    def allowed(self, units: list[str], level: int) -> bool:
        caps = self.a["build_cost_caps"][level]
        costs = [self.kb.champions[u]["cost"] for u in units]
        if any(costs.count(c) > n for c, n in caps.items()):
            return False
        lux = [u for u in units if self.kb.champions[u].get("variant_of") == "DA_Lux18_Base"]
        return len(lux) <= 1 and len(set(units)) == len(units)

    def best_holders(self, units: list[str], emblem_ids: list[str], level: int):
        """Put each emblem on the unit (without its trait) that gives the best value."""
        holders: dict[str, list[str]] = {}
        for e in emblem_ids:
            trait = emblem_trait(self.kb, e)
            options = [u for u in units if trait not in self.kb.champions[u]["traits"]]
            if not options:
                continue
            best = max(
                options,
                key=lambda u: (
                    self.value(units, level, {**holders, u: holders.get(u, []) + [e]})[0],
                    u,
                ),
            )
            holders.setdefault(best, []).append(e)
        return holders

    def score(self, units: list[str], level: int, emblem_ids: list[str]) -> float:
        return self.value(units, level, self.best_holders(units, emblem_ids, level))[0]

    # --- search ----------------------------------------------------------------------

    def _greedy(self, seed: list[str], level: int, emblem_ids: list[str]) -> list[str]:
        board = [u for u in seed if u in self.candidates][:level]
        while len(board) < level:
            options = [
                u for u in self.candidates if u not in board and self.allowed(board + [u], level)
            ]
            if not options:
                break
            board.append(
                max(options, key=lambda u: (self.score(board + [u], level, emblem_ids), u))
            )
        return board

    def _improve(self, board: list[str], level: int, emblem_ids: list[str]) -> list[str]:
        best = self.score(board, level, emblem_ids)
        for _ in range(30):
            move = None
            for i in range(len(board)):
                for u in self.candidates:
                    if u in board:
                        continue
                    trial = board[:i] + [u] + board[i + 1 :]
                    if not self.allowed(trial, level):
                        continue
                    v = self.score(trial, level, emblem_ids)
                    if v > best + 1e-9:
                        best, move = v, trial
            if move is None:
                break
            board = move
        return board

    def build(self, level: int, emblem_ids: list[str] = ()) -> BuiltBoard:
        emblem_ids = list(emblem_ids)
        seeds: list[list[str]] = [[]]
        for e in emblem_ids:  # a seed made of the emblem trait's own units, dearest first
            t = emblem_trait(self.kb, e)
            seeds.append(
                sorted(
                    (u for u in self.candidates if t in self.kb.champions[u]["traits"]),
                    key=lambda u: -self.kb.champions[u]["cost"],
                )
            )
        best_board, best_value = None, -1.0
        for seed in seeds:
            board = self._improve(self._greedy(seed, level, emblem_ids), level, emblem_ids)
            v = self.score(board, level, emblem_ids)
            if v > best_value:
                best_board, best_value = board, v
        holders = self.best_holders(best_board, emblem_ids, level)
        items, notes = self.assign_items(best_board, level, holders)
        value, traits = self.value(best_board, level, holders, items)
        units = sorted(
            ((u, self.star(u, level)) for u in best_board),
            key=lambda x: (-self.kb.champions[x[0]]["cost"], x[0]),
        )
        return BuiltBoard(level, units, holders, items, round(value, 1), traits, notes)

    # --- an emblem pool (one of each, use what helps) ------------------------------

    def _step_of(self, tid: str, n: int) -> int:
        if tid in self.unique:
            return 0
        bps = sorted({b["min_units"] for b in self.kb.traits[tid]["breakpoints"] if b["min_units"]})
        return sum(1 for b in bps if b <= n)

    def pool_value(self, units: list[str], level: int, pool: list[str]):
        """Board value when emblems from the pool are added where they raise a trait step.

        Returns (value, chosen emblems). Each emblem needs a holder without its trait
        and every unit holds at most 3 items (emblems included).
        """
        counts, _ = trait_counts(self.kb, units, None, self.same)
        power = sum(
            self.kb.champions[u]["cost"] * self.star_power[self.star(u, level)] for u in units
        )
        steps = sum(self._step_of(t, n) for t, n in counts.items())
        slots = 3 * len(units)
        used: dict[str, int] = {}
        chosen: list[str] = []
        by_trait = {e: emblem_trait(self.kb, e) for e in pool}
        while len(chosen) < slots:
            best, gain = None, 0
            for e in pool:
                t = by_trait[e]
                if e in chosen or t is None:
                    continue
                holders = sum(1 for u in units if t not in self.kb.champions[u]["traits"])
                if used.get(t, 0) >= holders:
                    continue
                n = counts.get(t, 0) + used.get(t, 0)
                g = self._step_of(t, n + 1) - self._step_of(t, n)
                if g > gain:
                    best, gain = e, g
            if best is None:
                # an emblem one short of the next step only pays with a second one
                break
            chosen.append(best)
            used[by_trait[best]] = used.get(by_trait[best], 0) + 1
            steps += gain
        return power * (1 + self.a["sim_trait_bonus"] * steps), chosen

    def place_emblems(self, units: list[str], level: int, chosen: list[str]):
        """Holders for chosen emblems: units without the trait, cheapest first, max 3 each."""
        weight = {
            u: self.kb.champions[u]["cost"] * self.star_power[self.star(u, level)] for u in units
        }
        holders: dict[str, list[str]] = {}
        dropped = []
        for e in chosen:
            t = emblem_trait(self.kb, e)
            options = [
                u
                for u in units
                if t not in self.kb.champions[u]["traits"]
                and len(holders.get(u, [])) < 3
                and not any(emblem_trait(self.kb, x) == t for x in holders.get(u, []))
            ]
            if not options:
                dropped.append(e)
                continue
            holder = min(options, key=lambda u: (weight[u], u))  # keep carries' slots for items
            holders.setdefault(holder, []).append(e)
        return holders, dropped

    def build_with_pool(self, level: int, pool: list[str]) -> BuiltBoard:
        def score(board):
            return self.pool_value(board, level, pool)[0]

        board: list[str] = []
        while len(board) < level:
            options = [
                u for u in self.candidates if u not in board and self.allowed(board + [u], level)
            ]
            if not options:
                break
            board.append(max(options, key=lambda u: (score(board + [u]), u)))
        best = score(board)
        for _ in range(30):
            move = None
            for i in range(len(board)):
                for u in self.candidates:
                    if u in board:
                        continue
                    trial = board[:i] + [u] + board[i + 1 :]
                    if not self.allowed(trial, level):
                        continue
                    v = score(trial)
                    if v > best + 1e-9:
                        best, move = v, trial
            if move is None:
                break
            board = move
        _, chosen = self.pool_value(board, level, pool)
        holders, dropped = self.place_emblems(board, level, chosen)
        items, notes = self.assign_items(board, level, holders)
        if dropped:
            notes.append(f"{len(dropped)} chosen emblems had no free holder")
        value, traits = self.value(board, level, holders, items)
        units = sorted(
            ((u, self.star(u, level)) for u in board),
            key=lambda x: (-self.kb.champions[x[0]]["cost"], x[0]),
        )
        return BuiltBoard(level, units, holders, items, round(value, 1), traits, notes)

    # --- items ------------------------------------------------------------------------

    def assign_items(self, board: list[str], level: int, holders: dict[str, list[str]]):
        slots = self.a["build_item_slots"]
        weight = {
            u: self.kb.champions[u]["cost"] * self.star_power[self.star(u, level)] for u in board
        }
        carries = sorted(
            (u for u in board if "tank" not in profile(self.kb, u).tags),
            key=lambda u: (-weight[u], u),
        )
        tanks = sorted(
            (u for u in board if "tank" in profile(self.kb, u).tags), key=lambda u: (-weight[u], u)
        )
        plan = []
        if carries:
            plan.append((carries[0], slots[0], "main carry"))
        if tanks:
            plan.append((tanks[0], slots[1], "main tank"))
        if len(carries) > 1:
            plan.append((carries[1], slots[2], "second carry"))
        items: dict[str, list[str]] = {}
        notes = []
        for unit, n, role in plan:
            room = n - len(holders.get(unit, []))  # an emblem takes an item slot
            ranked = sorted(self.completed, key=lambda i: (-self.fit(unit, i), i))
            chosen: list[str] = []
            for i in ranked:
                if len(chosen) >= room:
                    break
                if chosen.count(i) == 0 or (chosen.count(i) == 1 and self.fit(unit, i) >= 6):
                    chosen.append(i)
            items[unit] = chosen
            notes.append(f"{role}: {self.kb.champions[unit]['name']}")
        return items, notes
