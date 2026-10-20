"""Monte Carlo roll-down, vectorized over trials.

Draws every slot explicitly (cost tier, then a champion in proportion to the
copies left), so it shares no code with the exact solver. Agreement between
the two is the main check that both are implemented correctly.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np

from tft_engine.prob.exact import RollResult
from tft_engine.prob.query import RollQuery
from tft_engine.prob.shop_model import ShopModel
from tft_engine.repro import make_rng
from tft_engine.state import PoolBelief


def wilson_ci(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def roll_down_sample(
    query: RollQuery,
    belief: PoolBelief,
    model: ShopModel,
    n: int = 100_000,
    seed: int = 0,
    stream: str = "roll_down",
) -> RollResult:
    rng = make_rng(seed, stream)
    m = len(query.targets)
    ids = [t.unit_id for t in query.targets]

    # Assign each trial a pool state from the belief.
    weights = np.array([w for w, _ in belief.states])
    which = rng.choice(len(belief.states), size=n, p=weights / weights.sum())
    costs = np.array([belief.states[0][1].cost_of(u) for u in ids])
    k = np.zeros((n, m), dtype=np.int64)
    tiers = np.zeros((n, 5), dtype=np.int64)
    for s_idx, (_, pool) in enumerate(belief.states):
        mask = which == s_idx
        k[mask] = [pool.remaining(u) for u in ids]
        tiers[mask] = pool.tier_remaining

    need = np.tile([t.copies_needed for t in query.targets], (n, 1)).astype(np.int64)
    need0 = need.copy()
    shares = np.array([t.share for t in query.targets])
    gold = np.full(n, query.gold, dtype=np.int64)
    rolls = np.zeros(n, dtype=np.int64)
    free = np.full(n, query.free_rolls, dtype=np.int64)
    active = need.sum(axis=1) > 0
    success = ~active

    def pay(sel: np.ndarray) -> None:
        """Roll once for the trials in ``sel`` (indices): a free roll first, else gold."""
        price = np.where(free[sel] > 0, 0, query.roll_cost)
        gold[sel] -= price
        free[sel] = np.maximum(0, free[sel] - 1)
        rolls[sel] += 1

    if not query.first_shop_free:
        price0 = np.where(free > 0, 0, query.roll_cost)
        can = active & (gold - price0 >= query.gold_floor)
        pay(np.flatnonzero(can))
        active &= can

    cum_odds = np.cumsum(model.tier_probs(query.level))
    shop_idx = 0
    while active.any():
        if shop_idx >= query.max_shops:
            break
        idx = np.flatnonzero(active)
        hits = np.zeros((idx.size, m), dtype=np.int64)
        dist = model.slot_probs(shop_idx)
        slot_p = np.array([p for p, _ in dist])
        slot_n = np.array([s for _, s in dist])
        n_slots = slot_n[rng.choice(len(dist), size=idx.size, p=slot_p / slot_p.sum())]
        # until a copy is bought, a form-specific target matches only its share
        share_now = np.where(need[idx] == need0[idx], shares, 1.0)
        for slot in range(int(slot_n.max())):
            open_slot = n_slots > slot
            tier = np.searchsorted(cum_odds, rng.random(idx.size), side="right")  # 0..4
            tier = np.minimum(tier, 4)
            u = rng.random(idx.size) * tiers[idx, tier]
            form = rng.random(idx.size)
            offset = np.zeros(idx.size)
            for j in range(m):
                in_tier = tier == costs[j] - 1
                hit = in_tier & (u >= offset) & (u < offset + k[idx, j])
                hits[:, j] += hit & open_slot & (form < share_now[:, j])
                offset = np.where(in_tier, offset + k[idx, j], offset)
        g = gold[idx]
        for j in range(m):
            cap = np.minimum(g // costs[j], k[idx, j])  # affordable and still in the pool
            b = np.minimum(np.minimum(hits[:, j], need[idx, j]), cap)
            g -= b * costs[j]
            need[idx, j] -= b
            k[idx, j] -= b
            tiers[idx, costs[j] - 1] -= b
        gold[idx] = g
        done = need[idx].sum(axis=1) == 0
        success[idx[done]] = True
        price = np.where(free[idx] > 0, 0, query.roll_cost)
        cont = ~done & (g - price >= query.gold_floor)
        pay(idx[cont])
        new_active = np.zeros(n, dtype=bool)
        new_active[idx[cont]] = True
        active = new_active
        shop_idx += 1

    s = int(success.sum())
    counts = Counter(gold.tolist())
    joint = Counter(zip(success.tolist(), gold.tolist(), strict=True))
    return RollResult(
        p_success=s / n,
        gold_left={g: c / n for g, c in sorted(counts.items())},
        expected_rolls=float(rolls.mean()),
        method="monte_carlo",
        model=model.name,
        assumptions=model.assumptions,
        pool_basis=belief.basis,
        start_gold=query.gold,
        p_success_ci95=wilson_ci(s, n),
        n_samples=n,
        extra={"seed": seed, "stream": stream},
        joint={key: c / n for key, c in joint.items()},
    )
