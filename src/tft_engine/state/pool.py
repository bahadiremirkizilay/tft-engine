"""Shared champion pool: exact state and a belief (distribution) over states.

The shop only cares about, per cost tier, how many copies are left in total
and how many of those belong to the units we are looking for. ``PoolState``
stores exactly that. ``PoolBelief`` is a weighted list of pool states: what we
use when opponents' benches, sells or pivots are not fully known.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PoolState:
    tier_remaining: tuple[int, int, int, int, int]  # copies left per cost 1..5
    unit_remaining: tuple[tuple[str, int, int], ...]  # (unit_id, cost, copies left), sorted

    def __post_init__(self) -> None:
        if len(self.tier_remaining) != 5 or any(n < 0 for n in self.tier_remaining):
            raise ValueError("tier_remaining needs 5 non-negative counts")
        per_tier = [0] * 5
        for uid, cost, left in self.unit_remaining:
            if not 1 <= cost <= 5 or left < 0:
                raise ValueError(f"{uid}: bad cost or count")
            per_tier[cost - 1] += left
        for c in range(5):
            if per_tier[c] > self.tier_remaining[c]:
                raise ValueError(f"tracked units exceed tier {c + 1} total")

    @classmethod
    def build(
        cls,
        copies_per_champion: Mapping[int, int],
        champions_per_cost: Mapping[int, int],
        tracked: Mapping[str, int],
        taken: Mapping[str, int] | None = None,
        taken_untracked: Mapping[int, int] | None = None,
    ) -> PoolState:
        """Start from a full pool and remove copies that are known to be taken.

        tracked: unit_id -> cost, for the units the question is about.
        taken: unit_id -> copies held by anyone (you or seen opponents).
        taken_untracked: cost -> copies of other units held by anyone.
        """
        taken = dict(taken or {})
        taken_untracked = dict(taken_untracked or {})
        tiers = [copies_per_champion[c] * champions_per_cost[c] for c in range(1, 6)]
        units = []
        for uid, cost in sorted(tracked.items()):
            gone = taken.pop(uid, 0)
            left = copies_per_champion[cost] - gone
            if left < 0:
                raise ValueError(f"{uid}: more copies taken than exist")
            units.append((uid, cost, left))
            tiers[cost - 1] -= gone
        if taken:
            raise ValueError(f"taken lists untracked units {sorted(taken)}; use taken_untracked")
        for cost, gone in taken_untracked.items():
            tiers[cost - 1] -= gone
        if any(t < 0 for t in tiers):
            raise ValueError("more copies taken than the pool holds")
        return cls(tuple(tiers), tuple(units))

    def remaining(self, unit_id: str) -> int:
        for uid, _, left in self.unit_remaining:
            if uid == unit_id:
                return left
        raise KeyError(unit_id)

    def cost_of(self, unit_id: str) -> int:
        for uid, cost, _ in self.unit_remaining:
            if uid == unit_id:
                return cost
        raise KeyError(unit_id)

    def take(self, unit_id: str, n: int = 1) -> PoolState:
        units, tiers = [], list(self.tier_remaining)
        for uid, cost, left in self.unit_remaining:
            if uid == unit_id:
                if n > left:
                    raise ValueError(f"cannot take {n} {uid}, only {left} left")
                left -= n
                tiers[cost - 1] -= n
            units.append((uid, cost, left))
        return PoolState(tuple(tiers), tuple(units))


@dataclass(frozen=True)
class PoolBelief:
    """A probability distribution over pool states, with a note on its basis."""

    states: tuple[tuple[float, PoolState], ...]
    basis: str = "exact"  # e.g. "exact", "observed", "prior", "observed+prior"

    def __post_init__(self) -> None:
        total = sum(w for w, _ in self.states)
        if not self.states or any(w < 0 for w, _ in self.states):
            raise ValueError("belief needs at least one state and non-negative weights")
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(f"weights must sum to 1, got {total}")

    @classmethod
    def certain(cls, state: PoolState, basis: str = "exact") -> PoolBelief:
        return cls(((1.0, state),), basis)

    @classmethod
    def mixture(cls, weighted: Iterable[tuple[float, PoolState]], basis: str) -> PoolBelief:
        items = [(float(w), s) for w, s in weighted if w > 0]
        total = sum(w for w, _ in items)
        if total <= 0:
            raise ValueError("mixture has no positive weight")
        return cls(tuple((w / total, s) for w, s in items), basis)
