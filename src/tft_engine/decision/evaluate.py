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
from functools import lru_cache
from itertools import product
from typing import Any

from tft_engine.decision.assumptions import DEFAULTS, AssumptionSet
from tft_engine.decision.effects import AugmentOffer, AugmentRef, augment_offer, combine
from tft_engine.decision.horizon import simulate
from tft_engine.decision.scenario import Comp, Scenario
from tft_engine.decision.strength import board_strength
from tft_engine.gamedata import GameData, SchemaError, load_gamedata
from tft_engine.gamedata.entities import load_knowledge
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
from tft_engine.rules.modifiers import ModifierSet
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


@lru_cache(maxsize=8)
def _knowledge(set_id: str, patch: str):
    """The patch's knowledge base, or None for sets without one (synthetic test sets)."""
    try:
        return load_knowledge(set_id, patch)
    except (SchemaError, FileNotFoundError):
        return None


@lru_cache(maxsize=8)
def _champion_forms(set_id: str, patch: str) -> dict[str, tuple[str, int]]:
    """Champion id -> (base id, number of forms) for champions with shop forms (Lux)."""
    kb = _knowledge(set_id, patch)
    if kb is None:
        return {}
    by_base: dict[str, list[str]] = {}
    for c in kb.champions.values():
        if c.get("variant_of"):
            by_base.setdefault(c["variant_of"], []).append(c["id"])
    return {cid: (base, len(ids)) for base, ids in by_base.items() for cid in ids}


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
        # augments already picked keep changing the rules for every candidate
        self.owned = ModifierSet()
        self.owned_notes: list[str] = []
        for aid in scenario.state.augments:
            offer = self.offer(AugmentRef(aid))
            if offer.evaluable:
                self.owned = self.owned.merged(offer.modifiers)
            self.owned_notes += [f"owned {offer.id}: {n}" for n in offer.notes]

    def offer(self, e) -> AugmentOffer:
        """An offer (hand-written Effect or real augment) in the common shape."""
        if isinstance(e, AugmentRef):
            kb = _knowledge(self.sc.set_id, self.sc.patch)
            if kb is None:
                raise ValueError(f"{e.id}: real augments need the set's knowledge base")
            return augment_offer(e.id, kb)
        return e.to_offer()

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

    def model(self, a: AssumptionSet, wisp_bought: bool = False) -> IndependentShopModel:
        return IndependentShopModel.from_gamedata(
            self.data,
            wisp_prob=a["wisp_shop_prob"],
            active_traits=self.sc.active_traits,
            wisp_bought=wisp_bought,
        )

    def _share(self, unit_id: str, state: GameState) -> float:
        """Part of a champion's shop appearances that count (Lux forms, see Target)."""
        forms = _champion_forms(self.sc.set_id, self.sc.patch)
        if unit_id not in forms:
            return 1.0
        base, n = forms[unit_id]
        owned = {u.unit_id for u in state.units if forms.get(u.unit_id, ("",))[0] == base}
        if not owned:
            return 1.0 / n
        # an owned form locks the form every later copy shows in (owner, 18.4b)
        return 1.0 if unit_id in owned else 0.0

    def roll(
        self,
        state: GameState,
        comp: Comp,
        a: AssumptionSet,
        rules: Rules | None = None,
        wisp_bought: bool = False,
    ) -> RollResult | None:
        needs = comp.needs(state)
        if not needs:
            return None
        rules = rules or Rules(self.data)
        targets = tuple(Target(uid, n, self._share(uid, state)) for uid, _, n in needs)
        tracked = {uid: cost for uid, cost, _ in needs}
        query = RollQuery(
            level=state.level,
            gold=state.gold,
            targets=targets,
            roll_cost=rules.param("reroll_cost"),
            gold_floor=a["roll_floor"],
            free_rolls=state.free_rerolls,
        )
        model = self.model(a, wisp_bought)
        key = (
            query,
            state.state_hash(),
            model.name,
            model.wisp_prob,
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

    def _score(self, h, a: AssumptionSet, rules: Rules) -> float:
        """HP-equivalent score. Free rerolls left at the horizon end count as their gold price."""
        free = h.exp_free_rerolls_end
        free_gold = free * rules.param("reroll_cost") if free else 0.0
        return (
            -h.exp_hp_lost
            + a["gold_value_hp"] * free_gold
            - a["elim_penalty_hp"] * h.p_elim
            + a["gold_value_hp"] * (h.exp_gold_end - h.exp_gold_excess_end)
            + a["excess_gold_value_hp"] * h.exp_gold_excess_end
            + a["level_value_hp"] * h.exp_level_end
            - a["future_rounds"] * h.exp_future_loss_per_round
        )

    def _outcome(self, branches, rules, a) -> tuple[dict[str, float], float]:
        """Average horizon results over (probability, state) branches."""
        obs = self._observed_strengths(a)
        keys = ("p_win_first", "exp_gold_end", "exp_level_end", "exp_hp_lost", "p_elim")
        keys += ("exp_strength_ratio_end", "exp_future_loss_per_round")
        tot = dict.fromkeys(keys, 0.0)
        score = 0.0
        strength_now = 0.0
        for p, st in branches:
            h = simulate(st, rules, self.comp_units, obs, self.sc.opponents_alive, a)
            for k in keys:
                tot[k] += p * getattr(h, k)
            score += p * self._score(h, a, rules)
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

    def _roll_candidate(self, key, label, state, comp, rules, a):
        """Roll candidate; when shops can show a Wisp, also try buying one first."""
        best = self._roll_policy(key, label, state, comp, rules, a, False)
        price = a["wisp_price"]
        if self.model(a).wisp_prob > 0 and best.available and state.gold >= price:
            paid = rules.fire("wisp_bought", replace(state, gold=state.gold - price))
            buy = self._roll_policy(
                key, f"{label}, buying a Wisp first", paid, comp, rules, a, True
            )
            if buy.available and buy.score > best.score:
                best = buy
        return best

    def _roll_policy(self, key, label, state, comp, rules, a, wisp_bought):
        res = self.roll(state, comp, a, rules, wisp_bought)
        if res is None:
            return CandidateResult(key, label, False, "nothing left to buy for this comp")
        hit_units = _upgrade(state.units, comp)
        branches = []
        for (ok, g), p in res.joint.items():
            units = hit_units if ok else state.units
            # free rerolls are used first; any left after the roll-down are dropped
            branches.append((p, replace(state, gold=g, units=units, free_rerolls=0)))
        tot, score = self._outcome(branches, rules, a)
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
        self,
        a: AssumptionSet | None = None,
        state: GameState | None = None,
        modifiers: ModifierSet | None = None,
    ) -> Evaluation:
        """Compare candidates; ``modifiers`` are rule changes on top of the owned augments."""
        a = a or self.base
        state = state or self.sc.state
        rules = Rules(self.data, modifiers=self.owned.merged(modifiers or ModifierSet()))
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
            )
        )

        lvl = state
        while lvl.level == state.level:
            try:
                lvl = rules.buy_xp(lvl)
            except ValueError:
                break
        if lvl.level > state.level:
            tot, score = self._outcome([(1.0, lvl)], rules, a)
            m = self._metrics(tot, lvl.gold)
            m["levels_gained"] = Metric(lvl.level - state.level, EXACT)
            cands.append(CandidateResult("B", f"buy XP to level {lvl.level}", True, "", m, score))
        else:
            cands.append(CandidateResult("B", "buy XP", False, "not enough gold to level"))

        tot, score = self._outcome([(1.0, state)], rules, a)
        cands.append(
            CandidateResult("C", "keep gold", True, "", self._metrics(tot, state.gold), score)
        )

        for c in self.sc.comps:
            if c.name == current.name:
                continue
            cands.append(
                self._roll_candidate(f"D:{c.name}", f"pivot: roll for {c.name}", state, c, rules, a)
            )

        statuses = dict(rules.used)
        for name in ("shop_odds", "copies_per_champion", "champions_per_cost", "reroll_cost"):
            statuses[name] = self.data.param(name).status
        model = self.model(a)
        notes = [f"{p} changed by {', '.join(ids)}" for p, ids in sorted(rules.applied.items())]
        return Evaluation(
            scenario_id=self.sc.id,
            candidates=cands,
            data_status=statuses,
            shop_model=model.name,
            shop_assumptions=model.assumptions,
            unreviewed_patches=list(self.data.unreviewed_patches),
            notes=notes + self.owned_notes + rules.notes,
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
        """Rank the offers: each one is picked, then the best candidate is taken under it."""
        rows = []
        for e in self.sc.augment_offers:
            offer = self.offer(e)
            if not offer.evaluable:
                why = offer.notes or (f"{offer.type} effects are not evaluated",)
                rows.append(AugmentRow(offer.id, offer.type, False, notes=tuple(why)))
                continue
            rules = Rules(self.data, modifiers=self.owned.merged(offer.modifiers))
            st = self.sc.state
            if offer.augment_id:
                st = replace(st, augments=st.augments + (offer.augment_id,))
            st = rules.fire("now", replace(st, units=combine(st.units + offer.units)))
            ev = self.evaluate(state=st, modifiers=offer.modifiers)
            notes = tuple(offer.notes) + tuple(n for n in ev.notes if n not in offer.notes)
            rows.append(AugmentRow(offer.id, offer.type, True, ev.best.key, ev.best.score, notes))
        rows.sort(key=lambda r: (r.evaluated, r.score), reverse=True)
        return rows
