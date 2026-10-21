"""Which items suit a champion, by explainable rules (assumption class).

A champion's profile comes from the game data:
  * ``ad`` when its ability text scales with Attack Damage (the %i:scaleAD% icon),
    ``ap`` when it scales only with Ability Power (%i:scaleAP% and no AD icon);
  * ``frontline`` for range <= 2, ``backline`` otherwise;
  * from its role (game data or the curated role table): ``tank`` or ``utility``
    (Specialist) instead of ``ad``/``ap``, and ``marksman`` added for Marksmen.
Each item stat then scores by the weights in ``assumptions.item_fit_weights``,
scaled by how large the stat is compared with the typical (median) value among
completed items, between 0.5x and 2x. ``mana_effect`` stands for an effect text
that gives Mana (Spear of Shojin, Protector's Vow ...).
This is a rule of thumb that says why; it is not a statistic of what players
build (meta statistics are kept separately, plan rule 10).
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from tft_engine.decision.assumptions import AssumptionSet

FRONTLINE_MAX_RANGE = 2
SCALE_MIN, SCALE_MAX = 0.5, 2.0
_MANA_EFFECT = re.compile(r"\bmana\b", re.IGNORECASE)


def _item_stats(item) -> dict[str, float] | None:
    stats = item.get("stats")
    if stats is None:
        return None
    out = dict(stats)
    if _MANA_EFFECT.search(item.get("effect_text") or ""):
        out["mana_effect"] = 1.0
    return out


def _typical(kb, family: str = "DA") -> dict[str, float]:
    """Median of each stat among completed items of the family (non-zero values)."""
    values: dict[str, list[float]] = {}
    for i in kb.items.values():
        if i["kind"] != "completed" or i["family"] != family:
            continue
        for k, v in (_item_stats(i) or {}).items():
            if v:
                values.setdefault(k, []).append(abs(v))
    return {k: statistics.median(v) for k, v in values.items()}


@dataclass(frozen=True)
class Profile:
    champion: str
    tags: tuple[str, ...]  # "ad" or "ap", then "frontline" or "backline"
    role: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Fit:
    item: str
    score: float
    reasons: tuple[str, ...]
    trust: str = "assumption"


def profile(kb, champion_id: str) -> Profile:
    c = kb.champions[champion_id]
    text = c["ability"].get("text") or ""
    role = c.get("role")
    reasons = []
    r = (role or "").lower()
    if "tank" in r:
        tags = ["tank"]
        reasons.append(f"role {role}: tank")
    elif "specialist" in r:
        tags = ["utility"]
        reasons.append(f"role {role}: utility, wants more casts")
    elif "scaleAD" in text:
        tags = ["ad"]
        reasons.append("ability scales with Attack Damage")
    elif "scaleAP" in text:
        tags = ["ap"]
        reasons.append("ability scales with Ability Power only")
    else:
        tags = []
        reasons.append("ability scaling not shown in its text")
    if "marksman" in r:
        tags.append("marksman")
        reasons.append(f"role {role}: damage from attacks")
    rng = c["stats"].get("range") or 0
    if rng <= FRONTLINE_MAX_RANGE:
        tags.append("frontline")
        reasons.append(f"range {rng:g}: frontline")
    else:
        tags.append("backline")
        reasons.append(f"range {rng:g}: backline")
    return Profile(champion_id, tuple(tags), role, tuple(reasons))


def item_fit(kb, champion_id: str, item_id: str, a: AssumptionSet) -> Fit:
    weights = a["item_fit_weights"]
    prof = profile(kb, champion_id)
    stats = _item_stats(kb.items[item_id])
    if stats is None:
        return Fit(item_id, 0.0, ("no stat record for this item",))
    typical = _typical(kb)
    score, reasons = 0.0, []
    for tag in prof.tags:
        for stat, value in stats.items():
            w = weights.get(tag, {}).get(stat, 0)
            if not w:
                continue
            ref = typical.get(stat) or abs(value) or 1.0
            scale = min(SCALE_MAX, max(SCALE_MIN, abs(value) / ref))
            score += w * scale
            reasons.append(f"{stat} {w * scale:+.1f} ({tag})")
    return Fit(item_id, round(score, 2), tuple(reasons))


def best_items(kb, champion_id: str, a: AssumptionSet, item_ids, top: int = 8) -> list[Fit]:
    fits = [item_fit(kb, champion_id, i, a) for i in item_ids]
    fits.sort(key=lambda f: (-f.score, kb.items[f.item]["name"]))
    return fits[:top]
