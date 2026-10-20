"""Augment offers for P1: one shape for hand-written effects and real augments.

Every offer becomes an ``AugmentOffer``: a ``ModifierSet`` (rule changes and
events, see ``rules/modifiers.py``) plus the units it hands over. Two sources:

* ``Effect``: a hand-written effect in a scenario (synthetic test offers). Its
  flat fields map to events: gold_now / xp_now / free_rerolls happen ``now``,
  gold_per_round happens at every ``round_start``.
* ``AugmentRef``: a real augment id; its model comes from
  ``curated/effects/augments.json`` and its numbers from the augment record.

Trait, combat and special effects are listed as "not evaluated"; the engine
never claims to have weighed them. Parts of a real augment the model cannot
value (units, items, components) are listed in the offer's notes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tft_engine.gamedata import STATUSES, UnknownMechanicError
from tft_engine.rules.modifiers import Event, ModifierSet, build
from tft_engine.state import UnitInstance

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
class AugmentOffer:
    id: str
    type: str  # an EFFECT_TYPES value, or a model category for real augments
    evaluable: bool
    modifiers: ModifierSet = ModifierSet()
    units: tuple[UnitInstance, ...] = ()
    notes: tuple[str, ...] = ()
    augment_id: str | None = None  # a real augment (kept in GameState.augments)


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

    def to_offer(self) -> AugmentOffer:
        if not self.evaluable:
            return AugmentOffer(self.id, self.type, False)
        now = tuple(
            (action, n)
            for action, n in (
                ("gain_gold", self.gold_now),
                ("gain_xp", self.xp_now),
                ("gain_free_rerolls", self.free_rerolls),
            )
            if n
        )
        events = []
        if now:
            events.append(Event(f"{self.id}:now", self.id, "now", now, status=self.status))
        if self.gold_per_round:
            events.append(
                Event(
                    f"{self.id}:round",
                    self.id,
                    "round_start",
                    (("gain_gold", self.gold_per_round),),
                    status=self.status,
                )
            )
        notes = []
        if self.components:
            notes.append(f"{self.components} component(s) not valued until B4")
        return AugmentOffer(
            self.id,
            self.type,
            True,
            ModifierSet(events=tuple(events)),
            self.units,
            tuple(notes),
        )


@dataclass(frozen=True)
class AugmentRef:
    """A real augment offered in a scenario: {"augment": "DA_LevelUp"}."""

    id: str
    units: tuple[UnitInstance, ...] = ()  # real augments name no fixed units


def parse_offer(d: dict[str, Any]) -> Effect | AugmentRef:
    if "augment" in d:
        extra = set(d) - {"augment"}
        if extra:
            raise ValueError(f"augment offer {d['augment']}: unknown fields {sorted(extra)}")
        return AugmentRef(d["augment"])
    return Effect.from_dict(d)


def augment_offer(augment_id: str, kb) -> AugmentOffer:
    """Offer for a real augment from its curated model (``kb`` is a KnowledgeBase)."""
    if augment_id not in kb.augments:
        raise KeyError(f"augment {augment_id} is not in {kb.set_id} {kb.patch}")
    record = kb.augments[augment_id]
    label = f"{augment_id} ({record.get('name', '')})"
    model = kb.augment_models.get(augment_id)
    if model is None:
        return AugmentOffer(
            label, "other", False, notes=("no model for this augment",), augment_id=augment_id
        )
    if model["model_status"] == "text_only":
        return AugmentOffer(
            label, model["category"], False, notes=(model.get("note", ""),), augment_id=augment_id
        )
    try:
        mods = build(augment_id, model, record.get("effects", {}), "community_extracted")
    except UnknownMechanicError as e:
        return AugmentOffer(label, model["category"], False, notes=(str(e),), augment_id=augment_id)
    notes = (model["note"],) if model.get("note") and model["model_status"] == "partial" else ()
    return AugmentOffer(label, model["category"], True, mods, notes=notes, augment_id=augment_id)
