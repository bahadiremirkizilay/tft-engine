"""Run registered experiments and replay recorded ones."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tft_engine.experiments.record import ExperimentRecord, git_commit

ExperimentFn = Callable[[dict[str, Any], int], dict[str, Any]]

REGISTRY: dict[str, ExperimentFn] = {}


def register(name: str) -> Callable[[ExperimentFn], ExperimentFn]:
    def deco(fn: ExperimentFn) -> ExperimentFn:
        if name in REGISTRY:
            raise ValueError(f"experiment {name!r} already registered")
        REGISTRY[name] = fn
        return fn

    return deco


def run_experiment(
    name: str, config: dict[str, Any], seed: int, data_version: str = "none"
) -> ExperimentRecord:
    # Import for side effect: registers the built-in experiments.
    from tft_engine.experiments import examples  # noqa: F401

    if name not in REGISTRY:
        raise KeyError(f"unknown experiment {name!r}; known: {sorted(REGISTRY)}")
    t0 = time.perf_counter()
    metrics = REGISTRY[name](config, seed)
    return ExperimentRecord(
        name=name,
        config=config,
        seed=seed,
        metrics=metrics,
        data_version=data_version,
        # Resolve the commit of the engine code itself, not of the caller's folder.
        git_commit=git_commit(Path(__file__).resolve().parent),
        duration_s=round(time.perf_counter() - t0, 6),
    )


def replay(record: ExperimentRecord) -> tuple[bool, dict[str, tuple[Any, Any]]]:
    """Rerun a recorded experiment. Returns (matches, differences)."""
    fresh = run_experiment(record.name, record.config, record.seed, record.data_version)
    old, new = record.reproducible_view(), fresh.reproducible_view()
    diffs = {k: (old[k], new[k]) for k in old if old[k] != new[k]}
    return not diffs, diffs
