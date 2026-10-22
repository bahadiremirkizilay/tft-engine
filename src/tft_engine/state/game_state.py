"""The player's own state, economy subset (M1a).

Opponents and the shared pool are kept out of this object on purpose: what
we know about them is uncertain and lives in ``PoolBelief``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from typing import Any

# copies that make a unit of each star; the only copy in the code (scenario, sim use it)
COPIES_PER_STAR = {1: 1, 2: 3, 3: 9}
_OPTIONAL_DEFAULTS: dict[str, Any] = {"free_rerolls": 0, "augments": (), "event_counts": ()}


@dataclass(frozen=True)
class UnitInstance:
    unit_id: str
    cost: int
    star: int = 1

    def __post_init__(self) -> None:
        if self.star not in COPIES_PER_STAR:
            raise ValueError(f"{self.unit_id}: star must be 1, 2 or 3")
        if not 1 <= self.cost <= 5:
            raise ValueError(f"{self.unit_id}: cost must be 1..5")

    @property
    def copies(self) -> int:
        """Pool copies this unit removed from the shared pool."""
        return COPIES_PER_STAR[self.star]


@dataclass(frozen=True)
class GameState:
    stage: str  # e.g. "3-2"
    gold: int
    level: int
    xp: int  # xp towards the next level
    hp: int
    streak: int = 0  # +n = n wins in a row, -n = n losses in a row
    units: tuple[UnitInstance, ...] = field(default_factory=tuple)
    free_rerolls: int = 0  # shop rerolls that cost no gold (from augments)
    augments: tuple[str, ...] = ()  # ids of augments picked so far
    event_counts: tuple[tuple[str, int], ...] = ()  # (event id, times fired), sorted

    def __post_init__(self) -> None:
        if self.gold < 0:
            raise ValueError("gold cannot be negative")
        if self.free_rerolls < 0:
            raise ValueError("free_rerolls cannot be negative")
        if self.level < 1 or self.xp < 0 or self.hp < 0:
            raise ValueError("level must be >= 1, xp and hp >= 0")
        parts = self.stage.split("-")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ValueError(f"stage must look like '3-2', got {self.stage!r}")

    @property
    def stage_round(self) -> tuple[int, int]:
        a, b = self.stage.split("-")
        return int(a), int(b)

    def copies_owned(self, unit_id: str) -> int:
        return sum(u.copies for u in self.units if u.unit_id == unit_id)

    def fired(self, event_id: str) -> int:
        return dict(self.event_counts).get(event_id, 0)

    def with_fired(self, event_id: str) -> GameState:
        counts = dict(self.event_counts)
        counts[event_id] = counts.get(event_id, 0) + 1
        return replace(self, event_counts=tuple(sorted(counts.items())))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["units"] = [asdict(u) for u in self.units]
        # Fields added in B3 are left out at their defaults, so older states keep
        # their JSON and hash.
        for name, default in _OPTIONAL_DEFAULTS.items():
            if getattr(self, name) == default:
                del d[name]
        if "augments" in d:
            d["augments"] = list(self.augments)
        if "event_counts" in d:
            d["event_counts"] = [list(x) for x in self.event_counts]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GameState:
        d = dict(d)
        d["units"] = tuple(UnitInstance(**u) for u in d.get("units", []))
        d["augments"] = tuple(d.get("augments", ()))
        d["event_counts"] = tuple(sorted((str(k), int(n)) for k, n in d.get("event_counts", ())))
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def state_hash(self) -> str:
        """Order-independent hash: the same board in a different order hashes equally."""
        d = self.to_dict()
        d["units"] = sorted(d["units"], key=lambda u: (u["unit_id"], u["star"], u["cost"]))
        blob = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]
