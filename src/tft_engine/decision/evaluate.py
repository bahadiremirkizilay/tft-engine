"""P1: compare candidate decisions for one hand-written situation.

Candidates (plan section 11, P1):
  A  roll at the current level for the current comp, down to a gold floor;
  B  buy XP until the next level, keep the rest;
  C  keep gold, do nothing;
  D  roll for another comp (one candidate per alternative comp).
Augment offers are ranked separately: each offer is applied, then the best
of A-D is taken under it.

Every number carries a trust class (plan section 8.5): "exact" numbers come
from the shop and economy rules (and are only as good as the game data they
use); "assumption" numbers depend on the heuristic in strength.py and the
values in assumptions.py. The score is always an assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import product
from typing import Any

from tft_engine.decision.assumptions import DEFAULTS, AssumptionSet
from tft_engine.decision.horizon import simulate
from tft_engine.decision.scenario import Comp, Scenario
from tft_engine.decision.strength import board_strength
from tft_engine.gamedata import GameData, load_gamedata
from tft_engine.prob import (
    IndependentShopModel,
    RollQuery,
    RollResult,
    Target,
    roll_down_exact,
    roll_down_sample,
)
from tft_engine.repro import derive_seed
from tft_engine.rules import Rules
from tft_engine.state import GameState, PoolBelief, PoolState, UnitInstance

EXACT, ASSUMPTION = "exact", "assumption"
MAX_BELIEF_STATES = 64
MC_SAMPLES = 20_000


@dataclass(frozen=True)
class Metric:
    value: float
    trust: str
    note: str = ""


@dataclass
class CandidateResult:
    key: str
    label: str
    available: bool
    reason: str = ""
    metrics: dict[str, Metric] = field(default_factory=dict)
    score: float = float("-inf")
    roll: RollResult | None = None


@dataclass
class Evaluation:
    scenario_id: str
    candidates: list[CandidateResult]
    data_status: dict[str, str]
    shop_model: str
    shop_assumptions: tuple[str, ...]
    unreviewed_patches: list[str]
    notes: list[str] = field(default_factory=list)

    @property
    def ranked(self) -> list[CandidateResult]:
        return sorted(
            (c for c in self.candidates if c.available), key=lambda c: c.score, reverse=True
        )

    @property
    def best(self) -> CandidateResult:
        return self.ranked[0]

    def by_key(self, key: str) -> CandidateResult:
        return next(c for c in self.candidates if c.key == key)


@dataclass(frozen=True)
class SensitivityRow:
    name: str
    description: str
    low: Any
    high: Any
    best_low: str
    best_high: str
    flips: bool
    regret: float  # worst score lost (HP-equivalent) by keeping the default choice


@dataclass(frozen=True)
class AugmentRow:
    offer_id: str
    type: str
    evaluated: bool
    best_candidate: str = ""
    score: float = float("-inf")
    notes: tuple[str, ...] = ()


def _upgrade(units: tuple[UnitInstance, ...], comp: Comp) -> tuple[UnitInstance, ...]:
    """Board after every unit of `comp` reached its target star."""
    wanted = {u.unit_id: u for u in comp.units}
    keep = [u for u in units if u.unit_id not in wanted]
    for uid, cu in wanted.items():
        owned = max((u.star for u in units if u.unit_id == uid), default=0)
        keep.append(UnitInstance(uid, cu.cost, max(owned, cu.star)))
    return tuple(keep)


class Evaluator:
    def __init__(self, scenario: Scenario, data: GameData | None = None) -> None:
        self.sc = scenario
        self.data = data or load_gamedata(scenario.set_id, scenario.patch)
        self.base = AssumptionSet(scenario.assumptions)
        self._roll_cache: dict = {}
        cp = self.data.get("copies_per_champion")
        cc = self.data.get("champions_per_cost")
        self.cp = {int(k): v for k, v in cp.items()}
        self.cc = {int(k): v for k, v in cc.items()}
        self.comp_units = [c.units for c in scenario.comps]

    # --- pool ------------------------------------------------------------

    def belief(self, state: GameState, tracked: dict[str, int], a: AssumptionSet) -> PoolBelief:
        """Copies left, from own units, observed boards, depletion and contest priors."""
        sc = self.sc
        taken = dict.fromkeys(tracked, 0)
        untracked = dict.fromkeys(range(1, 6), 0)
        holders = [u for u in state.units] + [u for o in sc.observed_opponents for u in o.units]
        for u in holders:
            if u.unit_id in taken:
                taken[u.unit_id] += u.copies
            else:
                untracked[u.cost] += u.copies
        major = state.stage_round[0]
        fracs = a.by_stage("tier_taken_frac_by_stage", major)
        for c in range(1, 6):
            n_tracked = sum(1 for cost in tracked.values() if cost == c)
            other_total = self.cp[c] * (self.cc[c] - n_tracked)
            unseen = round(fracs[c - 1] * a["pool_depletion_scale"] * other_total)
            untracked[c] = min(other_total, untracked[c] + unseen)
        options = []
        for uid in tracked:
            dist = sc.contest_prior.get(uid, ((1.0, 0),))
            options.append([(w, uid, n) for w, n in dist])
        combos = list(product(*options)) if options else [()]
        if len(combos) > MAX_BELIEF_STATES:
            raise ValueError(f"contest prior has {len(combos)} combinations (max 64)")
        states = []
        for combo in combos:
            w, extra = 1.0, dict(taken)
            for wi, uid, n in combo:
                w *= wi
                cap = self.cp[tracked[uid]]
                extra[uid] = min(cap, extra[uid] + n)
            pool = PoolState.build(self.cp, self.cc, tracked, extra, untracked)
            states.append((w, pool))
        basis = "observed" if sc.observed_opponents else "own board"
        if sc.contest_prior:
            basis += "+prior"
        return PoolBelief.mixture(states, basis + "+depletion assumption")

    def model(self, a: AssumptionSet) -> IndependentShopModel:
        return IndependentShopModel.from_gamedata(self.data, wisp_takes_slot=a["wisp_takes_slot"])

    def roll(self, state: GameState, comp: Comp, a: AssumptionSet) -> RollResult | None:
        needs = comp.needs(state)
        if not needs:
            return None
        targets = tuple(Target(uid, n) for uid, _, n in needs)
        tracked = {uid: cost for uid, cost, _ in needs}
        query = RollQuery(
            level=state.level,
            gold=state.gold,
            targets=targets,
            roll_cost=self.data.get("reroll_cost"),
            gold_floor=a["roll_floor"],
        )
        model = self.model(a)
        key = (
            query,
            state.state_hash(),
            model.name,
            a["pool_depletion_scale"],
            repr(a["tier_taken_frac_by_stage"]),
        )
        if key not in self._roll_cache:
            belief = self.belief(state, tracked, a)
            if len(targets) <= 3 and sum(t.copies_needed for t in targets) <= 9:
                res = roll_down_exact(query, belief, model)
            else:
                seed = derive_seed(self.sc.seed, "p1", comp.name)
                res = roll_down_sample(query, belief, model, n=MC_SAMPLES, seed=seed)
            self._roll_cache[key] = res
        return self._roll_cache[key]

    # --- evaluation ------------------------------------------------------

    def _observed_strengths(self, a: AssumptionSet) -> list[float]:
        return [
            board_strength(o.units, len(o.units), self.comp_units, a)
            for o in self.sc.observed_opponents
        ]

    def _score(self, h, a: AssumptionSet) -> float:
        return (
            -h.exp_hp_lost
            - a["elim_penalty_hp"] * h.p_elim
            + a["gold_value_hp"] * (h.exp_gold_end - h.exp_gold_excess_end)
            + a["excess_gold_value_hp"] * h.exp_gold_excess_end
            + a["level_value_hp"] * h.exp_level_end
            - a["future_rounds"] * h.exp_future_loss_per_round
        )

    def _outcome(self, branches, rules, a, extra_income) -> tuple[dict[str, float], float]:
        """Average horizon results over (probability, state) branches."""
        obs = self._observed_strengths(a)
        keys = ("p_win_first", "exp_gold_end", "exp_level_end", "exp_hp_lost", "p_elim")
        keys += ("exp_strength_ratio_end", "exp_future_loss_per_round")
        tot = dict.fromkeys(keys, 0.0)
        score = 0.0
        strength_now = 0.0
        for p, st in branches:
            h = simulate(st, rules, self.comp_units, obs, self.sc.opponents_alive, a, extra_income)
            for k in keys:
                tot[k] += p * getattr(h, k)
            score += p * self._score(h, a)
            strength_now += p * board_strength(st.units, st.level, self.comp_units, a)
        tot["strength_now"] = strength_now
        return tot, score

    def _metrics(self, tot: dict[str, float], gold_now: float) -> dict[str, Metric]:
        note = "depends on strength heuristic and opponent prior"
        return {
            "gold_after_action": Metric(gold_now, EXACT, "expected; from shop/economy rules"),
            "strength_now": Metric(tot["strength_now"], ASSUMPTION, "heuristic board strength"),
            "p_win_next": Metric(tot["p_win_first"], ASSUMPTION, note),
            "exp_hp_lost": Metric(tot["exp_hp_lost"], ASSUMPTION, note),
            "p_elim": Metric(tot["p_elim"], ASSUMPTION, note),
            "exp_gold_end": Metric(tot["exp_gold_end"], ASSUMPTION, "income depends on wins"),
            "exp_level_end": Metric(tot["exp_level_end"], ASSUMPTION, "passive XP over horizon"),
            "future_hp_loss_per_round": Metric(
                tot["exp_future_loss_per_round"], ASSUMPTION, "after the horizon, board unchanged"
            ),
        }

    def _roll_candidate(self, key, label, state, comp, rules, a, extra_income):
        res = self.roll(state, comp, a)
        if res is None:
            return CandidateResult(key, label, False, "nothing left to buy for this comp")
        hit_units = _upgrade(state.units, comp)
        branches = []
        for (ok, g), p in res.joint.items():
            units = hit_units if ok else state.units
            branches.append((p, replace(state, gold=g, units=units)))
        tot, score = self._outcome(branches, rules, a, extra_income)
        m = self._metrics(tot, res.expected_gold_left)
        ci = res.p_success_ci95
        m["p_hit"] = Metric(
            res.p_success,
            EXACT,
            f"{res.method}" + (f", 95% CI {ci[0]:.3f}-{ci[1]:.3f}" if ci else ""),
        )
        m["exp_rolls"] = Metric(res.expected_rolls, EXACT, res.method)
        return CandidateResult(key, label, True, metrics=m, score=score, roll=res)

    def evaluate(
        self, a: AssumptionSet | None = None, state: GameState | None = None, extra_income: int = 0
    ) -> Evaluation:
        a = a or self.base
        state = state or self.sc.state
        rules = Rules(self.data)
        cands: list[CandidateResult] = []
        current = self.sc.comp(self.sc.current_comp)

        cands.append(
            self._roll_candidate(
                "A",
                f"roll for {current.name} at level {state.level}",
                state,
                current,
                rules,
                a,
                extra_income,
            )
        )

        lvl = state
        while lvl.level == state.level:
            try:
                lvl = rules.buy_xp(lvl)
            except ValueError:
                break
        if lvl.level > state.level:
            tot, score = self._outcome([(1.0, lvl)], rules, a, extra_income)
            m = self._metrics(tot, lvl.gold)
            m["levels_gained"] = Metric(lvl.level - state.level, EXACT)
            cands.append(CandidateResult("B", f"buy XP to level {lvl.level}", True, "", m, score))
        else:
            cands.append(CandidateResult("B", "buy XP", False, "not enough gold to level"))

        tot, score = self._outcome([(1.0, state)], rules, a, extra_income)
        cands.append(
            CandidateResult("C", "keep gold", True, "", self._metrics(tot, state.gold), score)
        )

        for c in self.sc.comps:
            if c.name == current.name:
                continue
            cands.append(
                self._roll_candidate(
                    f"D:{c.name}", f"pivot: roll for {c.name}", state, c, rules, a, extra_income
                )
            )

        statuses = dict(rules.used)
        for name in ("shop_odds", "copies_per_champion", "champions_per_cost", "reroll_cost"):
            statuses[name] = self.data.param(name).status
        model = self.model(a)
        return Evaluation(
            scenario_id=self.sc.id,
            candidates=cands,
            data_status=statuses,
            shop_model=model.name,
            shop_assumptions=model.assumptions,
            unreviewed_patches=list(self.data.unreviewed_patches),
        )

    # --- sensitivity and augments ---------------------------------------

    def sensitivity(self, base_eval: Evaluation | None = None) -> list[SensitivityRow]:
        base_eval = base_eval or self.evaluate()
        default_best = base_eval.best.key
        rows = []
        for name, spec in DEFAULTS.items():
            if not spec.varied:
                continue
            bests, regret = [], 0.0
            for value in (spec.low, spec.high):
                ev = self.evaluate(self.base.with_value(name, value))
                best = ev.best
                bests.append(best.key)
                kept = next((c for c in ev.ranked if c.key == default_best), None)
                lost = best.score - kept.score if kept else float("inf")
                regret = max(regret, lost)
            rows.append(
                SensitivityRow(
                    name,
                    spec.description,
                    spec.low,
                    spec.high,
                    bests[0],
                    bests[1],
                    bests[0] != default_best or bests[1] != default_best,
                    regret,
                )
            )
        rows.sort(key=lambda r: (r.flips, r.regret), reverse=True)
        return rows

    def augments(self) -> list[AugmentRow]:
        rows = []
        rules = Rules(self.data)
        for e in self.sc.augment_offers:
            if not e.evaluable:
                rows.append(
                    AugmentRow(e.id, e.type, False, notes=(f"{e.type} effects are not evaluated",))
                )
                continue
            st, notes = e.apply(self.sc.state, rules)
            ev = self.evaluate(state=st, extra_income=e.gold_per_round)
            rows.append(AugmentRow(e.id, e.type, True, ev.best.key, ev.best.score, tuple(notes)))
        rows.sort(key=lambda r: (r.evaluated, r.score), reverse=True)
        return rows
