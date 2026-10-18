"""Built-in example experiment.

This is a toy used only to test the experiment pipeline (seeding, recording,
replay). It contains no TFT mechanics and its numbers mean nothing about TFT.
"""

from __future__ import annotations

from typing import Any

from tft_engine.experiments.runner import register
from tft_engine.repro import make_rng


@register("toy_dice_mean")
def toy_dice_mean(config: dict[str, Any], seed: int) -> dict[str, Any]:
    """Estimate the mean of an n-sided die by sampling, with a 95% interval."""
    sides = int(config.get("sides", 6))
    samples = int(config.get("samples", 10_000))
    rng = make_rng(seed, "toy_dice_mean", "rolls")
    rolls = rng.integers(1, sides + 1, size=samples)
    mean = float(rolls.mean())
    half_width = 1.96 * float(rolls.std(ddof=1)) / samples**0.5
    return {
        "mean": round(mean, 10),
        "ci95_low": round(mean - half_width, 10),
        "ci95_high": round(mean + half_width, 10),
        "true_mean": (sides + 1) / 2,
        "label": "toy, not TFT",
    }
