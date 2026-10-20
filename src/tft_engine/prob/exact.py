"""Exact roll-down probabilities by dynamic programming.

State: (shop index mod period, gold, copies still needed, copies left of each
target, copies left in each target's tier, free rolls left). Each shop's target hits follow a
multinomial over {target 1, ..., target m, anything else}; every outcome is
enumerated, so the result is exact for the shop model and policy given.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
from itertools import combinations_with_replacement

from tft_engine.prob.query import RollQuery
from tft_engine.prob.shop_model import ShopModel
from tft_engine.state import PoolBelief, PoolState


@dataclass(frozen=True)
class RollResult:
    p_success: float
    gold_left: dict[int, float]  # unconditional distribution of gold left
    expected_rolls: float
    method: str  # "exact" or "monte_carlo"
    model: str
    assumptions: tuple[str, ...]
    pool_basis: str
    start_gold: int
    p_success_ci95: tuple[float, float] | None = None  # sampler only
    n_samples: int | None = None
    extra: dict = field(default_factory=dict)
    joint: dict[tuple[bool, int], float] = field(default_factory=dict)  # (success, gold) -> p

    @property
    def expected_gold_left(self) -> float:
        return sum(g * p for g, p in self.gold_left.items())

    @property
    def expected_gold_spent(self) -> float:
        return self.start_gold - self.expected_gold_left


def _outcomes(slots: int, probs: tuple[float, ...]):
    """Yield (counts per category, probability) for a multinomial draw."""
    k = len(probs)
    for combo in combinations_with_replacement(range(k), slots):
        counts = [0] * k
        for c in combo:
            counts[c] += 1
        coef = math.factorial(slots)
        pr = 1.0
        for c, n in enumerate(counts):
            coef //= math.factorial(n)
            if n:
                pr *= probs[c] ** n
        if pr > 0:
            yield counts, coef * pr


def _solve_one(query: RollQuery, pool: PoolState, model: ShopModel):
    ids = [t.unit_id for t in query.targets]
    costs = tuple(pool.cost_of(u) for u in ids)
    tiers = sorted(set(costs))
    tier_pos = {c: i for i, c in enumerate(tiers)}
    tier_probs = model.tier_probs(query.level)
    period = model.period
    need0 = tuple(t.copies_needed for t in query.targets)
    shares = tuple(t.share for t in query.targets)

    @cache
    def f(idx: int, gold: int, needs: tuple, ks: tuple, ts: tuple, depth: int, free: int):
        """Return (dist over (success, gold) -> prob, expected future rolls)."""
        price = query.price(free)
        probs = []
        for j, c in enumerate(costs):
            t = ts[tier_pos[c]]
            # a form-specific target (Lux) matches only part of its copies until one is bought
            share = shares[j] if needs[j] == need0[j] else 1.0
            probs.append(tier_probs[c - 1] * ks[j] / t * share if t > 0 else 0.0)
        probs.append(max(0.0, 1.0 - sum(probs)))
        dist: dict = defaultdict(float)
        exp_rolls = 0.0
        outcomes = [
            (counts, ps * pr)
            for ps, slots in model.slot_probs(idx)
            for counts, pr in _outcomes(slots, tuple(probs))
        ]
        for counts, pr in outcomes:
            g, nd, kk, tt = gold, list(needs), list(ks), list(ts)
            for j in range(len(ids)):
                b = min(counts[j], nd[j], g // costs[j], kk[j])
                if b:
                    g -= b * costs[j]
                    nd[j] -= b
                    kk[j] -= b
                    tt[tier_pos[costs[j]]] -= b
            if not any(nd):
                dist[(True, g)] += pr
            elif g - price >= query.gold_floor and depth < query.max_shops:
                sub, sub_rolls = f(
                    (idx + 1) % period,
                    g - price,
                    tuple(nd),
                    tuple(kk),
                    tuple(tt),
                    depth + 1,
                    max(0, free - 1),
                )
                for key, q in sub.items():
                    dist[key] += pr * q
                exp_rolls += pr * (1 + sub_rolls)
            else:
                dist[(False, g)] += pr
        return dict(dist), exp_rolls

    needs = tuple(t.copies_needed for t in query.targets)
    ks = tuple(pool.remaining(u) for u in ids)
    ts = tuple(pool.tier_remaining[c - 1] for c in tiers)
    if not any(needs):
        return {(True, query.gold): 1.0}, 0.0
    free = query.free_rolls
    if query.first_shop_free:
        return f(0, query.gold, needs, ks, ts, 0, free)
    price = query.price(free)
    if query.gold - price < query.gold_floor:
        return {(False, query.gold): 1.0}, 0.0
    dist, rolls = f(0, query.gold - price, needs, ks, ts, 0, max(0, free - 1))
    return dist, rolls + 1


def roll_down_exact(query: RollQuery, belief: PoolBelief, model: ShopModel) -> RollResult:
    total: dict = defaultdict(float)
    exp_rolls = 0.0
    for w, pool in belief.states:
        dist, rolls = _solve_one(query, pool, model)
        for key, p in dist.items():
            total[key] += w * p
        exp_rolls += w * rolls
    p_success = sum(p for (ok, _), p in total.items() if ok)
    gold_left: dict[int, float] = defaultdict(float)
    for (_, g), p in total.items():
        gold_left[g] += p
    return RollResult(
        p_success=p_success,
        gold_left=dict(sorted(gold_left.items())),
        expected_rolls=exp_rolls,
        method="exact",
        model=model.name,
        assumptions=model.assumptions,
        pool_basis=belief.basis,
        start_gold=query.gold,
        joint=dict(total),
    )
