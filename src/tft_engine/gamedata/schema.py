"""Provenance-tagged game parameters.

Every number the engine uses comes wrapped in a ``Param`` that says where it
came from and how much we trust it. A value we do not know is stored as
``status="unknown"`` with ``value=None``; asking for it raises
``UnknownMechanicError`` instead of silently using a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Ordered from most to least trusted.
STATUSES = (
    "verified",  # read from an official Riot source or the in-game tooltip
    "observed",  # measured from our own recorded games
    "community_extracted",  # extracted from game files by a community tool
    "third_party_unverified",  # taken from a third-party site, not yet checked
    "unverified",  # widely assumed, not yet checked for this set/patch
    "synthetic",  # made-up values for tests only, never real TFT
    "unknown",  # not known; using it is an error
)


class SchemaError(ValueError):
    """Game data file is malformed or lacks provenance."""


class UnknownMechanicError(LookupError):
    """A rule needs a parameter whose value is unknown."""


@dataclass(frozen=True)
class Param:
    name: str
    value: Any
    status: str
    source: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise SchemaError(f"{self.name}: unknown status {self.status!r}")
        if not self.source.strip():
            raise SchemaError(f"{self.name}: every parameter needs a source")
        if (self.status == "unknown") != (self.value is None):
            raise SchemaError(f"{self.name}: value must be null exactly when status is 'unknown'")

    def get(self) -> Any:
        if self.status == "unknown":
            raise UnknownMechanicError(
                f"parameter {self.name!r} is unknown ({self.source}); "
                "verify it and add it to the data file, or pass an explicit override"
            )
        return self.value

    @property
    def is_known(self) -> bool:
        return self.status != "unknown"

    @classmethod
    def from_dict(cls, name: str, d: Any) -> Param:
        if not isinstance(d, dict) or not {"value", "status", "source"} <= d.keys():
            raise SchemaError(f"{name}: expected an object with value, status and source")
        extra = set(d) - {"value", "status", "source", "note"}
        if extra:
            raise SchemaError(f"{name}: unexpected fields {sorted(extra)}")
        return cls(name, d["value"], d["status"], d["source"], d.get("note", ""))

    def to_dict(self) -> dict[str, Any]:
        d = {"value": self.value, "status": self.status, "source": self.source}
        if self.note:
            d["note"] = self.note
        return d
