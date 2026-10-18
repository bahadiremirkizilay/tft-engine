"""Deterministic seed handling.

Every random stream in the engine is derived from one base seed plus a name,
so that adding a new stream never shifts the numbers of an existing one.
This is what later makes common random numbers (CRN) comparisons possible:
two candidate decisions evaluated with the same stream name see the same shops.
"""

from __future__ import annotations

import hashlib

import numpy as np

_MASK_64 = (1 << 64) - 1


def derive_seed(base_seed: int, *names: str | int) -> int:
    """Return a stable 64-bit seed for the stream identified by ``names``.

    Uses SHA-256 rather than Python's ``hash`` so the result is the same on
    every machine, Python version and process.
    """
    if base_seed < 0:
        raise ValueError("base_seed must be non-negative")
    h = hashlib.sha256(str(base_seed).encode())
    for name in names:
        h.update(b"\x1f")
        h.update(str(name).encode())
    return int.from_bytes(h.digest()[:8], "little") & _MASK_64


def make_rng(base_seed: int, *names: str | int) -> np.random.Generator:
    """Return an independent NumPy generator for the named stream."""
    return np.random.Generator(np.random.PCG64(derive_seed(base_seed, *names)))
