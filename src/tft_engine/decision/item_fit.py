"""Which items suit a champion, by explainable rules (assumption class).

A champion's profile comes from the game data:
  * ``ad`` when its ability text scales with Attack Damage (the %i:scaleAD% icon),
    ``ap`` when it scales only with Ability Power (%i:scaleAP% and no AD icon);
  * ``frontline`` for range <= 2, ``backline`` otherwise;
  * ``tank`` instead of ``ad``/``ap`` when its role is a tank (game data or the
    curated role table); roles are missing for most Set 18 champions.
Each item stat then scores by the weights in ``assumptions.item_fit_weights``.
This is a rule of thumb that says why; it is not a statistic of what players
build (meta statistics are kept separately, plan rule 10).
"""

from __future__ import annotations

from dataclasses import dataclass

from tft_engine.decision.assumptions import AssumptionSet

FRONTLINE_MAX_RANGE = 2


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
    if role and "tank" in role.lower():
        tags = ["tank"]
        reasons.append(f"role {role}: tank")
    elif "scaleAD" in text:
        tags = ["ad"]
        reasons.append("ability scales with Attack Damage")
    elif "scaleAP" in text:
        tags = ["ap"]
        reasons.append("ability scales with Ability Power only")
    else:
        tags = []
        reasons.append("ability scaling not shown in its text")
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
    stats = kb.items[item_id].get("stats")
    if stats is None:
        return Fit(item_id, 0.0, ("no stat record for this item",))
    score, reasons = 0.0, []
    for tag in prof.tags:
        for stat in stats:
            w = weights.get(tag, {}).get(stat, 0)
            if w:
                score += w
                reasons.append(f"{stat} {'+' if w > 0 else ''}{w} ({tag})")
    return Fit(item_id, score, tuple(reasons))


def best_items(kb, champion_id: str, a: AssumptionSet, item_ids, top: int = 8) -> list[Fit]:
    fits = [item_fit(kb, champion_id, i, a) for i in item_ids]
    fits.sort(key=lambda f: (-f.score, kb.items[f.item]["name"]))
    return fits[:top]
