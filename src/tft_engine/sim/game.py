"""A simple 8-player game simulation to watch the engine play (not real TFT combat).

Real rules (from the game data): the shared pool and shop odds, gold, interest,
streaks, XP, star-ups, trait breakpoints, item recipes.
Simplified (assumptions, see ``assumptions.py`` sim_*):
  * combat: each board gets a power number (unit cost and stars, active trait
    steps, completed items) and wins with ``strength.win_prob``; the loser takes
    the set's player damage with a survivor count from the power gap;
  * rounds x-1..x-6 are player combats, x-7 is a monster round that drops one
    component; no carousel, no augments, no Wisps, no positioning;
  * every player uses the same policy: build the best board from what it owns,
    buy units that improve it or complete a star-up (shop copies included), save
    gold on an early loss streak or with Coven, level on a curve, slow roll above
    50 near a 3-star, roll down at level 8 from 4-2, roll deep when HP is low;
    items are crafted from stage 2, each on the board unit it fits best, and only
    when some unit fits (owner's feedback on the first replays, 2026-10-21).
The policy never aims at a fixed comp: the board follows the shops.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_fit import item_fit
from tft_engine.decision.strength import win_prob
from tft_engine.gamedata import load_gamedata
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.repro import make_rng
from tft_engine.rules import Rules
from tft_engine.rules.items import RecipeBook
from tft_engine.rules.traits import active_traits, trait_counts
from tft_engine.state import GameState, UnitInstance

BENCH = 9
START_HP = 100
PVE_ROUND = 7  # x-7 drops a component
STAR_POWER = {1: 1.0, 2: 1.8, 3: 3.24}  # same shape as Health per star (1/1.8/3.24)


@dataclass
class Player:
    pid: int
    state: GameState
    items: dict[str, list[str]] = field(default_factory=dict)  # unit id -> completed items
    components: list[str] = field(default_factory=list)
    board: list[str] = field(default_factory=list)  # unit ids on the board
    rolled_down: bool = False  # the level 8 roll-down is done
    alive: bool = True
    placement: int | None = None


class GameSim:
    def __init__(self, set_id: str = "set18", patch: str = "18.4", seed: int = 0, a=None):
        self.data = load_gamedata(set_id, patch)
        self.kb = load_knowledge(set_id, patch)
        self.rules = Rules(self.data)
        self.book = RecipeBook(self.kb)
        self.a = a or AssumptionSet()
        self.seed = seed
        self.rng = make_rng(seed, "sim")
        self.same_trait = bool(self.data.param("emblem_on_same_trait_counts").get())
        champs = [c for c in self.kb.champions.values() if not c.get("variant_of")]
        cp = {int(k): v for k, v in self.data.get("copies_per_champion").items()}
        self.cost = {c["id"]: c["cost"] for c in self.kb.champions.values()}
        self.pool = {c["id"]: cp[c["cost"]] for c in champs}
        self.lux_forms = sorted(
            c["id"] for c in self.kb.champions.values() if c.get("variant_of") == "DA_Lux18_Base"
        )
        self.odds = {int(k): v for k, v in self.data.get("shop_odds").items()}
        self.players = [
            Player(i, GameState(stage="1-1", gold=0, level=1, xp=0, hp=START_HP)) for i in range(8)
        ]
        self.log: list[dict[str, Any]] = []
        self._fit: dict[tuple[str, str], float] = {}
        self.unique_traits = {
            t["id"]
            for t in self.kb.traits.values()
            if max((b["min_units"] or 0 for b in t["breakpoints"]), default=0) <= 1
        }

    # --- pool and shop ------------------------------------------------------

    def _base(self, uid: str) -> str:
        return self.kb.champions[uid].get("variant_of") or uid

    def roll_shop(self, level: int) -> list[str]:
        odds = self.odds[min(level, max(self.odds))]
        shop = []
        for _ in range(int(self.data.get("shop_slots"))):
            tier = int(self.rng.choice(5, p=[x / 100 for x in odds])) + 1
            ids = [u for u in self.pool if self.cost[u] == tier and self.pool[u] > 0]
            if not ids:
                continue
            w = [self.pool[u] for u in ids]
            pick = ids[int(self.rng.choice(len(ids), p=[x / sum(w) for x in w]))]
            shop.append(pick)
        return shop

    def _take(self, uid: str) -> str:
        base = self._base(uid)
        self.pool[base] -= 1
        if base == "DA_Lux18_Base" and self.lux_forms:
            return self.lux_forms[int(self.rng.integers(len(self.lux_forms)))]
        return uid

    def _give_back(self, uid: str, star: int) -> None:
        self.pool[self._base(uid)] += {1: 1, 2: 3, 3: 9}[star]

    # --- board evaluation -----------------------------------------------------

    def fit(self, unit_id: str, item_id: str) -> float:
        key = (unit_id, item_id)
        if key not in self._fit:
            self._fit[key] = item_fit(self.kb, unit_id, item_id, self.a).score
        return self._fit[key]

    def unit_power(self, u: UnitInstance, items: list[str]) -> float:
        """Cost and stars; each item adds up to sim_item_bonus, scaled by how well it fits."""
        good = self.a["sim_item_good_fit"]
        bonus = sum(
            self.a["sim_item_bonus"] * min(1.0, max(0.2, self.fit(u.unit_id, i) / good))
            for i in items
        )
        return u.cost * STAR_POWER[u.star] * (1 + bonus)

    def board_power(self, p: Player, board: list[str]) -> tuple[float, list]:
        best: dict[str, UnitInstance] = {}
        for u in p.state.units:
            if u.unit_id in board and (u.unit_id not in best or u.star > best[u.unit_id].star):
                best[u.unit_id] = u
        power = sum(self.unit_power(u, p.items.get(u.unit_id, [])) for u in best.values())
        counts, _ = trait_counts(self.kb, list(best), None, self.same_trait)
        traits = [t for t in active_traits(self.kb, counts) if t.active]
        steps = 0
        for t in traits:
            if t.trait_id in self.unique_traits:  # one-unit traits: their power is the unit
                continue
            bps = sorted(
                {
                    b["min_units"]
                    for b in self.kb.traits[t.trait_id]["breakpoints"]
                    if b["min_units"]
                }
            )
            steps += bps.index(t.breakpoint) + 1 if t.breakpoint in bps else 1
        return power * (1 + self.a["sim_trait_bonus"] * steps), traits

    def best_board(self, p: Player) -> list[str]:
        """Greedy: add the unit that raises board power most, up to the level."""
        owned = list(dict.fromkeys(u.unit_id for u in p.state.units))
        board: list[str] = []
        while len(board) < p.state.level and len(board) < len(owned):
            cand = [u for u in owned if u not in board]
            scored = [(self.board_power(p, board + [u])[0], u) for u in cand]
            board.append(max(scored)[1])
        return board

    # --- the policy -------------------------------------------------------------

    def _value_of_buy(self, p: Player, uid: str) -> tuple[float, str]:
        """How much buying one copy helps: board gain or a pair toward a star-up."""
        before = self.board_power(p, p.board)[0]
        trial = replace(p.state, gold=p.state.gold + 10)
        trial = self.rules.buy_unit(trial, uid, self.cost[uid])
        tp = Player(p.pid, trial, p.items, p.components)
        after = self.board_power(tp, self.best_board(tp))[0]
        copies = sum(u.copies for u in p.state.units if u.unit_id == uid)
        if after > before + 1e-9:
            return after - before, f"board power {before:.1f} -> {after:.1f}"
        if copies and copies % 3:
            return 0.3 * self.cost[uid], f"pair toward a star-up ({copies} copies)"
        return 0.0, ""

    def _bench_count(self, p: Player) -> int:
        return len(p.state.units) - len(p.board)

    def _sell_weakest_bench(self, p: Player, notes: list[str]) -> None:
        bench = [u for u in p.state.units if u.unit_id not in p.board]
        if not bench:
            return
        copies = Counter(u.unit_id for u in p.state.units)
        weakest = min(bench, key=lambda u: (copies[u.unit_id] > 1, u.cost * STAR_POWER[u.star]))
        p.state = self.rules.sell_unit(p.state, weakest.unit_id, weakest.star)
        self._give_back(weakest.unit_id, weakest.star)
        notes.append(f"sold {self.kb.champions[weakest.unit_id]['name']} {weakest.star}*")

    def _econ_reserve(self, p: Player) -> int:
        """Gold to keep: the interest step already reached, up to the cap (50)."""
        s = p.state
        if s.stage.startswith("1-") or s.hp < self.a["sim_low_hp"]:
            return 0
        per10 = self.rules.param("interest_per_10_gold") or 1
        cap = self.rules.param("interest_cap") * 10 // per10
        return min(cap, (s.gold // 10) * 10)

    def _completes_star(self, p: Player, uid: str, in_shop: int = 1) -> bool:
        """Owned 1-stars plus the copies in this shop make a 2-star (may chain to 3)."""
        ones = sum(1 for u in p.state.units if u.unit_id == uid and u.star == 1)
        return ones < 3 and ones + in_shop >= 3

    def _buy_from(
        self, p: Player, shop: list[str], notes: list[str], reserve: int, econ: bool = False
    ) -> list[str]:
        left = []
        remaining = Counter(shop)
        for uid in shop:
            value, why = self._value_of_buy(p, uid)
            star_up = self._completes_star(p, uid, remaining[uid])
            remaining[uid] -= 1
            if econ and not star_up:  # saving gold: only star-ups
                left.append(uid)
                continue
            if star_up:
                value = max(value, 0.5 * self.cost[uid])
            # breaking an interest step needs a star-up or a large gain (>= 15% of board power)
            keep = reserve
            if not star_up and value < 0.15 * max(self.board_power(p, p.board)[0], 1.0):
                keep = max(reserve, self._econ_reserve(p))
            if value <= 0 or p.state.gold - self.cost[uid] < keep:
                left.append(uid)
                continue
            if star_up:
                why = "completes a star-up"
            if self._bench_count(p) >= BENCH:
                self._sell_weakest_bench(p, notes)
            got = self._take(uid)
            p.state = self.rules.buy_unit(p.state, got, self.cost[uid])
            p.board = self.best_board(p)
            notes.append(f"bought {self.kb.champions[got]['name']} ({why})")
        return left

    def _near_three_star(self, p: Player) -> str | None:
        copies = Counter()
        for u in p.state.units:
            copies[u.unit_id] += u.copies
        for uid, n in copies.most_common():
            if 6 <= n < 9 and self.cost[uid] <= 3 and uid in p.board:
                return uid
        return None

    def _items(self, p: Player, notes: list[str]) -> None:
        """Craft an item only from stage 2, on the board unit it fits best, if one fits."""
        if len(p.components) < 2 or not p.board:
            return
        if not self._reached(p.state.stage, self.a["sim_no_items_before"]):
            return
        weight = {
            u: max(x.cost * STAR_POWER[x.star] for x in p.state.units if x.unit_id == u)
            for u in p.board
        }
        while len(p.components) >= 2:
            opts = [
                o
                for o in self.book.options(p.components)
                if self.kb.items[o.item]["kind"] == "completed"
            ]
            pairs = [
                (self.fit(u, o.item) + 0.1 * weight[u], self.fit(u, o.item), o, u)
                for o in opts
                for u in p.board
                if len(p.items.get(u, [])) < 3
            ]
            if not pairs:
                break
            _, fit, best, holder = max(pairs, key=lambda x: (x[0], x[3], x[2].item))
            if fit < self.a["sim_item_min_fit"]:
                break  # nobody on the board suits these components yet: keep them
            for c in best.pair:
                p.components.remove(c)
            p.items.setdefault(holder, []).append(best.item)
            notes.append(
                f"built {self.book.name(best.item)} on {self.kb.champions[holder]['name']}"
                f" (fit {fit:.1f})"
            )

    def plan_round(self, p: Player) -> dict[str, Any]:
        """One planning phase for one player; returns what it did and why."""
        notes: list[str] = []
        a, s = self.a, p.state
        if s.stage == "1-1":  # no shop on the first round
            p.board = self.best_board(p)
            power, traits = self.board_power(p, p.board)
            return {
                "shop": [],
                "shop_costs": [],
                "notes": [],
                "rolls": 0,
                "power": round(power, 1),
                "traits": [f"{t.name} {t.count}" for t in traits],
            }
        shop = self.roll_shop(s.level)
        first_shop = list(shop)
        major = int(s.stage.split("-")[0])
        coven = trait_counts(self.kb, p.board, None, self.same_trait)[0].get("DA_18_Coven", 0)
        econ = major <= 3 and s.hp >= a["sim_lose_streak_hp"] and (s.streak <= -2 or coven >= 3)
        if econ:
            reason = "Coven" if coven >= 3 else f"loss streak {s.streak}"
            notes.append(
                f"saving gold ({reason}, HP {s.hp}): only star-ups"
                + ("; Coven rewards for losses are not modelled" if coven >= 3 else "")
            )
        # 1. level on the curve
        want = max(
            (lv for st, lv in a["sim_level_curve"].items() if self._reached(s.stage, st)), default=1
        )
        while p.state.level < min(want, int(self.data.get("max_level"))):
            try:
                p.state = self.rules.buy_xp(p.state)
            except ValueError:
                break
            if p.state.level >= want:
                notes.append(f"leveled to {p.state.level} (level curve: {want} by now)")
        # 2. spare gold above the cap: XP first, then rolls
        while p.state.gold > a["sim_excess_gold"] and p.state.level < 9 and not econ:
            before = p.state.level
            p.state = self.rules.buy_xp(p.state)
            if p.state.level > before:
                notes.append(f"leveled to {p.state.level} (gold above {a['sim_excess_gold']})")
        # 3. how much to spend on rolling
        near = self._near_three_star(p)
        rolldown = (
            not p.rolled_down and p.state.level >= 8 and self._reached(s.stage, "4-2") and not econ
        )
        if econ:
            floor, why = None, ""
        elif p.state.hp < a["sim_low_hp"] and p.state.level >= 6:
            floor, why = a["sim_deep_roll_floor"], f"HP {p.state.hp} < {a['sim_low_hp']}: roll deep"
        elif rolldown:
            floor, why = a["sim_rolldown_floor"], f"level {p.state.level} roll-down"
            p.rolled_down = True
        elif p.state.gold > a["sim_excess_gold"]:
            floor, why = a["sim_slow_roll_floor"], f"gold above {a['sim_excess_gold']}"
        elif near:
            floor = a["sim_slow_roll_floor"]
            why = f"slow roll above {floor} for {self.kb.champions[near]['name']} 3*"
        else:
            floor, why = None, ""
        # 3. buy from the shop, roll while above the floor
        shop = self._buy_from(
            p, shop, notes, reserve=0 if floor is None else min(floor, 50), econ=econ
        )
        rolls = 0
        if floor is not None:
            while p.state.gold - int(self.data.get("reroll_cost")) >= floor and rolls < 30:
                p.state = self.rules.reroll(p.state)
                shop = self._buy_from(p, self.roll_shop(p.state.level), notes, reserve=floor)
                rolls += 1
            if rolls:
                notes.append(f"rolled {rolls}x ({why})")
        p.board = self.best_board(p)
        self._items(p, notes)
        power, traits = self.board_power(p, p.board)
        return {
            "shop": [self.kb.champions[u]["name"] for u in first_shop],
            "shop_costs": [self.cost[u] for u in first_shop],
            "notes": notes,
            "rolls": rolls,
            "power": round(power, 1),
            "traits": [f"{t.name} {t.count}" for t in traits],
        }

    @staticmethod
    def _reached(stage: str, mark: str) -> bool:
        a, b = (int(x) for x in stage.split("-"))
        c, d = (int(x) for x in mark.split("-"))
        return (a, b) >= (c, d)

    # --- rounds -----------------------------------------------------------------

    def _income_pve(self, p: Player, next_stage: str) -> None:
        s = p.state
        gold = s.gold + self.rules.base_income(next_stage) + self.rules.interest(s.gold)
        level, xp = self.rules.add_xp(s.level, s.xp, self.rules.param("passive_xp_per_round"))
        p.state = replace(s, gold=gold, level=level, xp=xp, stage=next_stage)

    def _drop_component(self, p: Player) -> str:
        comp = self.book.components[int(self.rng.integers(len(self.book.components)))]
        p.components.append(comp)
        return comp

    def _combat(self, a: Player, b: Player, major: int) -> tuple[Player, int, float]:
        pa, pb = self.board_power(a, a.board)[0], self.board_power(b, b.board)[0]
        p_a = win_prob(pa, max(pb, 1e-6), self.a)
        winner, loser = (a, b) if self.rng.random() < p_a else (b, a)
        pw, pl = (pa, pb) if winner is a else (pb, pa)
        gap = max(0.0, (pw - pl) / max(pw, 1e-6))
        survivors = max(1, min(len(winner.board), round(len(winner.board) * (0.3 + gap))))
        dmg = self.rules.player_damage(min(major, 8), survivors)
        return winner, dmg, p_a

    @staticmethod
    def next_stage(stage: str) -> str:
        major, minor = (int(x) for x in stage.split("-"))
        if major == 1:
            return "2-1" if minor >= 4 else f"1-{minor + 1}"
        return f"{major + 1}-1" if minor >= PVE_ROUND else f"{major}-{minor + 1}"

    def run(self, max_rounds: int = 60) -> dict[str, Any]:
        for p in self.players:  # stage 1: two starting components and a 1-cost
            self._drop_component(p)
            uid = self._take(self.rng.choice([u for u in self.pool if self.cost[u] == 1]))
            p.state = self.rules.buy_unit(replace(p.state, gold=1), uid, 1)
            p.board = self.best_board(p)
        stage = "1-1"
        for _ in range(max_rounds):
            alive = [p for p in self.players if p.alive]
            if len(alive) <= 1:
                break
            major, minor = (int(x) for x in stage.split("-"))
            rec = {"stage": stage, "players": {}}
            for p in alive:
                p.state = replace(p.state, stage=stage)
                rec["players"][p.pid] = self.plan_round(p)
            pve = major == 1 or minor == PVE_ROUND
            nxt = self.next_stage(stage)
            if pve:
                for p in alive:
                    comp = self._drop_component(p)
                    rec["players"][p.pid]["combat"] = f"monster round: got {self.book.name(comp)}"
                    self._income_pve(p, nxt)
            else:
                order = [alive[i] for i in self.rng.permutation(len(alive))]
                pairs = [(order[i], order[(i + 1) % len(order)]) for i in range(0, len(order), 2)]
                for a, b in pairs:
                    if a is b:
                        continue
                    winner, dmg, p_a = self._combat(a, b, major)
                    loser = b if winner is a else a
                    for x, y, pw in ((a, b, p_a), (b, a, 1 - p_a)):
                        won = x is winner
                        text = (
                            f"vs P{y.pid}: {'won' if won else 'lost'} "
                            f"(win chance {pw:.0%}{'' if won else f', -{dmg} HP'})"
                        )
                        rec["players"][x.pid]["combat"] = text
                    loser.state = replace(loser.state, hp=max(0, loser.state.hp - dmg))
                    for x in (a, b):
                        x.state = self.rules.end_round(x.state, x is winner, nxt)
                for p in alive:
                    if p.state.stage != nxt:  # odd one out this round
                        p.state = self.rules.end_round(p.state, True, nxt)
            for p in alive:
                info = rec["players"][p.pid]
                info.update(
                    gold=p.state.gold,
                    level=p.state.level,
                    hp=p.state.hp,
                    streak=p.state.streak,
                    board=self._board_view(p),
                    bench=len(p.state.units) - len(p.board),
                    components=[self.book.name(c) for c in p.components],
                )
            out = [p for p in alive if p.state.hp <= 0]
            for p in out:
                p.alive = False
                p.placement = sum(1 for q in self.players if q.alive) + 1
                self._return_units(p)
            self.log.append(rec)
            stage = nxt
        for p in self.players:
            if p.alive:
                p.placement = 1
        return {
            "seed": self.seed,
            "placements": {p.pid: p.placement for p in self.players},
            "rounds": self.log,
        }

    def _board_view(self, p: Player) -> list[dict[str, Any]]:
        out = []
        for uid in p.board:
            star = max(u.star for u in p.state.units if u.unit_id == uid)
            out.append(
                {
                    "name": self.kb.champions[uid]["name"],
                    "cost": self.cost[uid],
                    "star": star,
                    "items": [self.book.name(i) for i in p.items.get(uid, [])],
                }
            )
        return out

    def _return_units(self, p: Player) -> None:
        for u in p.state.units:
            self._give_back(u.unit_id, u.star)
        p.state = replace(p.state, units=())


def simulate_game(seed: int = 0, set_id: str = "set18", patch: str = "18.4") -> dict[str, Any]:
    return GameSim(set_id, patch, seed).run()
