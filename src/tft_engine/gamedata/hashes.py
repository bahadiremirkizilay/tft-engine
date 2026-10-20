"""Resolve CommunityDragon's hashed names.

Game files store some names (trait variables, tags) as a 32-bit hash shown as
``{xxxxxxxx}``. CommunityDragon uses FNV-1a over the lower-cased name for
these. We never guess a name: a hash is resolved only when a candidate name
(for example a ``@Placeholder@`` from the description text) hashes to exactly
that value. Unresolved hashes are kept as they are and reported.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_FNV_OFFSET = 0x811C9DC5
_FNV_PRIME = 0x01000193
_HASHED = re.compile(r"^\{([0-9a-f]{8})\}$")
_PLACEHOLDER = re.compile(r"@([A-Za-z0-9_]+)(?:\*[0-9.]+)?@")


def fnv1a_32(name: str) -> int:
    h = _FNV_OFFSET
    for byte in name.lower().encode("utf-8"):
        h ^= byte
        h = (h * _FNV_PRIME) & 0xFFFFFFFF
    return h


def hash_key(name: str) -> str:
    """The way CommunityDragon prints a hashed name, e.g. '{da2472a7}'."""
    return "{" + f"{fnv1a_32(name):08x}" + "}"


def is_hashed(key: str) -> bool:
    return bool(_HASHED.match(key))


def placeholders(text: str) -> list[str]:
    """Variable names used in a description, e.g. '@BrawlerTeamHealth@'."""
    return sorted(set(_PLACEHOLDER.findall(text or "")))


class HashResolver:
    """Maps hashed keys back to names, from candidate names only."""

    def __init__(self, known: dict[str, str] | None = None) -> None:
        self._names: dict[str, str] = {}
        for key, name in (known or {}).items():
            if hash_key(name) != key:
                raise ValueError(f"known name {name!r} does not hash to {key}")
            self._names[key] = name

    def add_candidates(self, names: Iterable[str]) -> None:
        for name in names:
            self._names.setdefault(hash_key(name), name)

    def resolve(self, key: str) -> str | None:
        """Name for a hashed key, or None. Non-hashed keys are returned unchanged."""
        if not is_hashed(key):
            return key
        return self._names.get(key)

    def resolve_mapping(self, values: dict[str, object]) -> tuple[dict[str, object], list[str]]:
        """Rename resolvable keys; return (mapping, unresolved hashed keys)."""
        out: dict[str, object] = {}
        unresolved: list[str] = []
        for key, value in values.items():
            name = self.resolve(key)
            if name is None:
                unresolved.append(key)
                out[key] = value
            else:
                out[name] = value
        return out, sorted(unresolved)
