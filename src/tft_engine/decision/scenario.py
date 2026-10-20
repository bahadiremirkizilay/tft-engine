"""A hand-written game situation for P1 (JSON in, validated objects out).

Opponent information is split as in plan section 8.3:
  observed_opponents: boards seen on screen (a lower bound on copies taken);
  contest_prior: assumed extra copies held by unseen boards or benches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tft_engine.decision.effects import Effect
from tft_engine.state import GameState, UnitInstance

_STAR_COPIES = {1: 1, 2: 3, 3: 9}


@dataclass(frozen=True)
class Comp:
    """A target board: each unit at the star level wanted."""

    name: str
    units: tuple[UnitInstance, ...]

    def needs(self, state: GameState) -> list[tuple[str, int, int]]:
        """(unit_id, cost, copies still needed) for units not yet complete."""
        out = []
        for u in self.units:
            missing = _STAR_COPIES[u.star] - state.copies_owned(u.unit_id)
            if missing > 0:
                out.append((u.unit_id, u.cost, missing))
        return out


@dataclass(frozen=True)
class ObservedOpponent:
    player: str
    units: tuple[UnitInstance, ...]
    seen_at: str  # stage when the board was seen


@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    set_id: str
    patch: str
    state: GameState
    comps: tuple[Comp, ...]
    current_comp: str
    observed_opponents: tuple[ObservedOpponent, ...] = ()
    contest_prior: dict[str, tuple[tuple[float, int], ...]] = field(default_factory=dict)
    opponents_alive: int = 7
    augment_offers: tuple[Effect, ...] = ()
    active_traits: dict[str, int] = field(default_factory=dict)  # trait id -> active units
    assumptions: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    expected: dict[str, Any] | None = None  # for obvious scenarios: {"best_in": [...]}
    expert_choice: str | None = None  # the player's own label, when given

    def __post_init__(self) -> None:
        names = [c.name for c in self.comps]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.id}: comp names must be unique")
        if self.current_comp not in names:
            raise ValueError(f"{self.id}: current_comp {self.current_comp!r} is not a comp")
        if not 1 <= self.opponents_alive <= 7:
            raise ValueError(f"{self.id}: opponents_alive must be 1..7")
        if len(self.observed_opponents) > self.opponents_alive:
            raise ValueError(f"{self.id}: more observed opponents than alive")
        costs: dict[str, int] = {}
        every = list(self.state.units)
        for c in self.comps:
            every += c.units
        for o in self.observed_opponents:
            every += o.units
        every += [u for e in self.augment_offers for u in e.units]
        for u in every:
            if costs.setdefault(u.unit_id, u.cost) != u.cost:
                raise ValueError(f"{self.id}: unit {u.unit_id} appears with two costs")
        for uid, dist in self.contest_prior.items():
            if uid not in costs:
                raise ValueError(f"{self.id}: contest_prior names unknown unit {uid}")
            if abs(sum(w for w, _ in dist) - 1) > 1e-9 or any(n < 0 for _, n in dist):
                raise ValueError(f"{self.id}: contest_prior for {uid} must be a distribution")

    @property
    def unit_costs(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for u in self.state.units:
            out[u.unit_id] = u.cost
        for c in self.comps:
            for u in c.units:
                out[u.unit_id] = u.cost
        for o in self.observed_opponents:
            for u in o.units:
                out[u.unit_id] = u.cost
        return out

    def comp(self, name: str) -> Comp:
        return next(c for c in self.comps if c.name == name)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Scenario:
        def units(xs):
            return tuple(UnitInstance(**u) for u in xs)

        return cls(
            id=d["id"],
            description=d.get("description", ""),
            set_id=d["set"],
            patch=d["patch"],
            state=GameState.from_dict(d["state"]),
            comps=tuple(Comp(c["name"], units(c["units"])) for c in d["comps"]),
            current_comp=d["current_comp"],
            observed_opponents=tuple(
                ObservedOpponent(o["player"], units(o["units"]), o["seen_at"])
                for o in d.get("observed_opponents", [])
            ),
            contest_prior={
                k: tuple((float(w), int(n)) for w, n in v)
                for k, v in d.get("contest_prior", {}).items()
            },
            opponents_alive=d.get("opponents_alive", 7),
            augment_offers=tuple(Effect.from_dict(e) for e in d.get("augment_offers", [])),
            active_traits={k: int(v) for k, v in d.get("active_traits", {}).items()},
            assumptions=d.get("assumptions", {}),
            seed=d.get("seed", 0),
            expected=d.get("expected"),
            expert_choice=d.get("expert_choice"),
        )


def load_scenario(path: str | Path) -> Scenario:
    return Scenario.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
