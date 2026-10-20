"""Modifiers and events: one way for augments, Wisps and traits to change the rules.

A ``Modifier`` changes a rule parameter for as long as it is active, for
example "buying XP costs 1 less" (``xp_purchase.gold`` add -1) or "max
interest is 10" (``interest_cap`` set 10). Modifiers are applied in a fixed
order (set, then add, then mul, then min/max; ties by priority, then id), so
the result never depends on the order they were picked in.

An ``Event`` does something when a trigger happens, for example "gain 1 free
reroll at the start of every round". Actions come from a small fixed library
(``ACTIONS``); anything else cannot be modelled and stays text only.

Numbers come from the game data, not from this module: augment models refer to
an augment's effect values (see ``resolve``), so a patch override of the value
reaches every rule that uses it.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from tft_engine.gamedata import STATUSES, UnknownMechanicError

OPS = ("set", "add", "mul", "min", "max")
_OP_ORDER = {"set": 0, "add": 1, "mul": 2, "min": 3, "max": 3}

TRIGGERS = (
    "now",  # once, when the effect is gained
    "round_start",  # start of every player-combat round after the current one
    "after_combat_win",
    "after_combat_loss",
    "stage_start",  # the first round of a new stage
    "level_up",  # every level gained
    "buy_xp",  # every XP purchase
    "wisp_bought",
)
ACTIONS = (
    "gain_gold",
    "gain_xp",
    "gain_free_rerolls",
    "gain_hp",
    "set_streak",
    "gain_unit",  # recorded, not valued until B4
    "gain_component",  # recorded, not valued until B4
    "gain_item",  # recorded, not valued until B4
)
VALUED_ACTIONS = ("gain_gold", "gain_xp", "gain_free_rerolls", "gain_hp", "set_streak")


def _check_common(kind: str, d_id: str, status: str, source: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"{kind} {d_id}: status must be one of {STATUSES}")
    if not str(source).strip():
        raise ValueError(f"{kind} {d_id}: needs a source")


@dataclass(frozen=True)
class Modifier:
    """Changes one rule parameter (or one key of a table parameter)."""

    id: str
    source: str  # the augment, Wisp or trait it comes from
    target: str  # "interest_cap" or "xp_purchase.gold"
    op: str
    value: Any
    status: str = "unverified"
    priority: int = 0

    def __post_init__(self) -> None:
        if self.op not in OPS:
            raise ValueError(f"modifier {self.id}: op must be one of {OPS}")
        _check_common("modifier", self.id, self.status, self.source)
        if self.value is None:
            raise UnknownMechanicError(f"modifier {self.id}: value is unknown")

    @property
    def param(self) -> str:
        return self.target.split(".", 1)[0]

    @property
    def sort_key(self) -> tuple:
        return (_OP_ORDER[self.op], self.priority, self.id)

    def _apply_scalar(self, current: Any) -> Any:
        if self.op == "set":
            return self.value
        if self.op == "add":
            return current + self.value
        if self.op == "mul":
            return current * self.value
        if self.op == "min":
            return min(current, self.value)
        return max(current, self.value)

    def apply(self, value: Any) -> Any:
        parts = self.target.split(".")[1:]
        if not parts:
            return self._apply_scalar(value)
        out = copy.deepcopy(value)
        cur = out
        for p in parts[:-1]:
            cur = cur[p]
        cur[parts[-1]] = self._apply_scalar(cur[parts[-1]])
        return out


@dataclass(frozen=True)
class Condition:
    """When an event fires. Empty means always."""

    from_stage: str | None = None  # inclusive, e.g. "3-1"
    until_stage: str | None = None  # inclusive
    min_level: int | None = None
    level: int | None = None  # exactly this level (for "when you reach level 9")

    @staticmethod
    def _stage_key(stage: str) -> tuple[int, int]:
        a, b = stage.split("-")
        return int(a), int(b)

    def holds(self, stage: str, level: int) -> bool:
        s = self._stage_key(stage)
        if self.from_stage and s < self._stage_key(self.from_stage):
            return False
        if self.until_stage and s > self._stage_key(self.until_stage):
            return False
        if self.min_level is not None and level < self.min_level:
            return False
        return self.level is None or level == self.level


@dataclass(frozen=True)
class Event:
    """Does ``do`` (action -> amount) when ``on`` happens and ``when`` holds."""

    id: str
    source: str
    on: str
    do: tuple[tuple[str, Any], ...]
    when: Condition = field(default_factory=Condition)
    limit: int | None = None  # fires at most this many times
    status: str = "unverified"

    def __post_init__(self) -> None:
        if self.on not in TRIGGERS:
            raise ValueError(f"event {self.id}: on must be one of {TRIGGERS}")
        _check_common("event", self.id, self.status, self.source)
        for action, amount in self.do:
            if action not in ACTIONS:
                raise ValueError(f"event {self.id}: action must be one of {ACTIONS}")
            if amount is None:
                raise UnknownMechanicError(f"event {self.id}: {action} amount is unknown")
        if self.limit is not None and self.limit < 1:
            raise ValueError(f"event {self.id}: limit must be >= 1")


@dataclass(frozen=True)
class ModifierSet:
    modifiers: tuple[Modifier, ...] = ()
    events: tuple[Event, ...] = ()

    def __post_init__(self) -> None:
        ids = [m.id for m in self.modifiers] + [e.id for e in self.events]
        if len(set(ids)) != len(ids):
            raise ValueError("modifier and event ids must be unique")
        object.__setattr__(
            self, "modifiers", tuple(sorted(self.modifiers, key=lambda m: m.sort_key))
        )

    def __bool__(self) -> bool:
        return bool(self.modifiers or self.events)

    def merged(self, other: ModifierSet) -> ModifierSet:
        return ModifierSet(self.modifiers + other.modifiers, self.events + other.events)

    def apply(self, name: str, value: Any) -> tuple[Any, tuple[str, ...]]:
        """Value of parameter ``name`` with every modifier on it, and their ids."""
        applied = []
        for m in self.modifiers:
            if m.param == name:
                value = m.apply(value)
                applied.append(m.id)
        return value, tuple(applied)

    def firing(
        self, trigger: str, stage: str, level: int, counts: Mapping[str, int]
    ) -> list[Event]:
        """Events that fire now, in id order, respecting their limits."""
        out = []
        for e in sorted(self.events, key=lambda e: e.id):
            if e.on != trigger or not e.when.holds(stage, level):
                continue
            if e.limit is not None and counts.get(e.id, 0) >= e.limit:
                continue
            out.append(e)
        return out


# --- building models from data ---------------------------------------------


def resolve(value: Any, effects: Mapping[str, Any], where: str) -> Any:
    """Turn a model value into a number.

    A plain number is used as is (it must come with a source in the model).
    ``{"effect": "InstantXP"}`` reads the augment's effect value, optionally
    with ``"scale"`` (for example -1 for "costs N less").
    """
    if not isinstance(value, Mapping):
        return value
    name = value.get("effect")
    if name is None:
        raise ValueError(f"{where}: value must be a number or {{'effect': name}}")
    if name not in effects or effects[name] is None:
        raise UnknownMechanicError(f"{where}: effect value {name!r} is not in the game data")
    v = effects[name]
    scale = value.get("scale", 1)
    out = v * scale
    return int(out) if isinstance(out, float) and out.is_integer() else out


def build(
    source: str,
    model: Mapping[str, Any],
    effects: Mapping[str, Any],
    status: str,
) -> ModifierSet:
    """ModifierSet for one augment (or Wisp) model from its curated record."""
    mods = []
    for i, m in enumerate(model.get("modifiers", [])):
        where = f"{source} modifier {i}"
        mods.append(
            Modifier(
                id=f"{source}:{m['target']}:{i}",
                source=source,
                target=m["target"],
                op=m["op"],
                value=resolve(m["value"], effects, where),
                status=status,
                priority=m.get("priority", 0),
            )
        )
    events = []
    for i, e in enumerate(model.get("events", [])):
        where = f"{source} event {i}"
        do = tuple((a, resolve(v, effects, f"{where} {a}")) for a, v in sorted(e["do"].items()))
        events.append(
            Event(
                id=f"{source}:{e['on']}:{i}",
                source=source,
                on=e["on"],
                do=do,
                when=Condition(**e.get("when", {})),
                limit=e.get("limit"),
                status=status,
            )
        )
    return ModifierSet(tuple(mods), tuple(events))


def combine_sets(sets: Iterable[ModifierSet]) -> ModifierSet:
    out = ModifierSet()
    for s in sets:
        out = out.merged(s)
    return out
