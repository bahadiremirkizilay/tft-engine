"""The player's own state, economy subset (M1a).

Opponents and the shared pool are kept out of this object on purpose: what
we know about them is uncertain and lives in ``PoolBelief``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

_COPIES_PER_STAR = {1: 1, 2: 3, 3: 9}


@dataclass(frozen=True)
class UnitInstance:
    unit_id: str
    cost: int
    star: int = 1

    def __post_init__(self) -> None:
        if self.star not in _COPIES_PER_STAR:
            raise ValueError(f"{self.unit_id}: star must be 1, 2 or 3")
        if not 1 <= self.cost <= 5:
            raise ValueError(f"{self.unit_id}: cost must be 1..5")

    @property
    def copies(self) -> int:
        """Pool copies this unit removed from the shared pool."""
        return _COPIES_PER_STAR[self.star]


@dataclass(frozen=True)
class GameState:
    stage: str  # e.g. "3-2"
    gold: int
    level: int
    xp: int  # xp towards the next level
    hp: int
    streak: int = 0  # +n = n wins in a row, -n = n losses in a row
    units: tuple[UnitInstance, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.gold < 0:
            raise ValueError("gold cannot be negative")
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

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["units"] = [asdict(u) for u in self.units]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GameState:
        d = dict(d)
        d["units"] = tuple(UnitInstance(**u) for u in d.get("units", []))
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def state_hash(self) -> str:
        """Order-independent hash: the same board in a different order hashes equally."""
        d = self.to_dict()
        d["units"] = sorted(d["units"], key=lambda u: (u["unit_id"], u["star"], u["cost"]))
        blob = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]
