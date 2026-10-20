"""One interface for augments, items and similar things (plan section 8.4).

P1 evaluates only what can be applied mechanically: economy effects (gold,
XP, free rerolls, income per round) and resources (units). Components are
recorded but not valued until M4. Trait, combat and special effects are
listed as "not evaluated"; the engine never claims to have weighed them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from tft_engine.gamedata import STATUSES
from tft_engine.state import GameState, UnitInstance

EFFECT_TYPES = ("economy", "resource", "trait", "combat", "special")
_FIELDS = {
    "id",
    "type",
    "source",
    "status",
    "text",
    "gold_now",
    "xp_now",
    "gold_per_round",
    "free_rerolls",
    "units",
    "components",
}


def combine(units: tuple[UnitInstance, ...]) -> tuple[UnitInstance, ...]:
    """Merge three equal copies into the next star, as the game does."""
    out = list(units)
    changed = True
    while changed:
        changed = False
        for star in (1, 2):
            for uid in sorted({u.unit_id for u in out}):
                same = [u for u in out if u.unit_id == uid and u.star == star]
                if len(same) >= 3:
                    for u in same[:3]:
                        out.remove(u)
                    out.append(UnitInstance(uid, same[0].cost, star + 1))
                    changed = True
    return tuple(out)


@dataclass(frozen=True)
class Effect:
    id: str
    type: str
    source: str
    status: str
    text: str = ""
    gold_now: int = 0
    xp_now: int = 0
    gold_per_round: int = 0  # extra income each round over the horizon
    free_rerolls: int = 0
    units: tuple[UnitInstance, ...] = ()
    components: int = 0

    def __post_init__(self) -> None:
        if self.type not in EFFECT_TYPES:
            raise ValueError(f"{self.id}: type must be one of {EFFECT_TYPES}")
        if self.status not in STATUSES:
            raise ValueError(f"{self.id}: status must be one of {STATUSES}")
        if not self.source.strip():
            raise ValueError(f"{self.id}: effect needs a source")
        mechanical = (
            self.gold_now or self.xp_now or self.gold_per_round or self.free_rerolls or self.units
        )
        if self.type in ("trait", "combat", "special") and mechanical:
            raise ValueError(f"{self.id}: only economy/resource effects carry mechanical fields")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Effect:
        extra = set(d) - _FIELDS
        if extra:
            raise ValueError(f"effect {d.get('id')}: unknown fields {sorted(extra)}")
        d = dict(d)
        d["units"] = tuple(UnitInstance(**u) for u in d.get("units", []))
        return cls(**d)

    @property
    def evaluable(self) -> bool:
        return self.type in ("economy", "resource")

    def apply(self, state: GameState, rules) -> tuple[GameState, list[str]]:
        """Apply the mechanical part now. Returns the new state and caveats."""
        notes: list[str] = []
        gold = state.gold + self.gold_now
        if self.free_rerolls:
            gold += self.free_rerolls * rules.param("reroll_cost")
            notes.append("free rerolls counted as their gold value (approximation)")
        level, xp = state.level, state.xp
        if self.xp_now:
            level, xp = rules.add_xp(level, xp, self.xp_now)
        units = combine(state.units + self.units)
        if self.components:
            notes.append(f"{self.components} component(s) not valued until M4")
        if self.gold_per_round:
            notes.append("income per round applied over the horizon only")
        return replace(state, gold=gold, level=level, xp=xp, units=units), notes

    def strength_modifier(self, units: tuple[UnitInstance, ...]) -> float:
        """Combat effect on board strength. P1 does not model it."""
        return 1.0
