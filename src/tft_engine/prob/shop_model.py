"""Shop models.

A shop model answers two questions: how many champion slots shop number i
has (a probability distribution, ``slot_probs``), and with what probability
each slot rolls each cost tier at a level. Given the tier, a slot picks a
champion in proportion to the copies left in the pool
(``IndependentShopModel``). That last step is the commonly assumed model; it
is not confirmed by Riot and is tested against observed shops in M1b.

Other models (set-specific rules) implement the same interface, so the exact
solver and the sampler work with any of them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from tft_engine.gamedata import GameData


class ShopModel(Protocol):
    name: str
    assumptions: tuple[str, ...]
    period: int  # slot_probs(i) == slot_probs(i + period) for all i

    def slot_probs(self, shop_index: int) -> tuple[tuple[float, int], ...]: ...

    def tier_probs(self, level: int) -> tuple[float, float, float, float, float]: ...


@dataclass(frozen=True)
class IndependentShopModel:
    """Every slot is drawn independently from the pool as it stands at the shop.

    wisp_prob: chance that a shop shows a Wisp in its rightmost slot, leaving one
    champion slot fewer (Set 18). Owner (18.4b): after a Wisp is bought, the
    champion under it shows at once and the later shops of that round have all
    slots, so a player who buys a Wisp rolls with ``wisp_prob = 0`` (see
    ``decision.evaluate``).
    """

    odds_pct: Mapping[int, tuple[float, ...]]
    slots: int = 5
    wisp_prob: float = 0.0
    name: str = "independent"

    def __post_init__(self) -> None:
        for level, row in self.odds_pct.items():
            if len(row) != 5 or abs(sum(row) - 100) > 1e-6:
                raise ValueError(f"odds for level {level} must be 5 values summing to 100")
        if not 0.0 <= self.wisp_prob <= 1.0:
            raise ValueError("wisp_prob must be between 0 and 1")

    @property
    def assumptions(self) -> tuple[str, ...]:
        a = [
            "slots are drawn independently from the pool at the time of the shop",
            "within a cost tier, a champion is picked in proportion to its copies left",
            "no bad luck protection",
            "slots are drawn with replacement: when few copies are left, one shop can show "
            "more copies than exist; purchases are capped at the copies left (to check in M1b)",
            "Inferno and Riftbeast change only the first shop after combat, which a roll-down "
            "takes as already on screen, so they are not modelled here",
        ]
        if self.wisp_prob > 0:
            a.append(
                f"each shop shows a Wisp with probability {self.wisp_prob:g}, leaving "
                f"{self.slots - 1} champion slots (frequency not measured)"
            )
        return tuple(a)

    @property
    def period(self) -> int:
        return 1

    def slot_probs(self, shop_index: int) -> tuple[tuple[float, int], ...]:
        q = self.wisp_prob
        out = ((1.0 - q, self.slots), (q, self.slots - 1))
        return tuple((p, s) for p, s in out if p > 0)

    def tier_probs(self, level: int) -> tuple[float, float, float, float, float]:
        try:
            row = self.odds_pct[level]
        except KeyError:
            raise ValueError(f"no shop odds for level {level}") from None
        return tuple(x / 100 for x in row)  # type: ignore[return-value]

    @classmethod
    def from_gamedata(
        cls,
        data: GameData,
        wisp_prob: float | None = None,
        active_traits: Mapping[str, int] | None = None,
        wisp_bought: bool = False,
    ) -> IndependentShopModel:
        """Shop model for a set and patch.

        wisp_prob=None follows the set's ``wisp_slot`` rule: a Wisp in every other
        shop (probability 0.5), or in every shop when ``active_traits`` meet the
        rule's ``every_shop_with`` trait level. ``wisp_bought`` means the player
        bought this round's Wisp, so every shop has all its champion slots.
        """
        rule = data.shop_rules.get("wisp_slot")
        rule_value = rule.value if rule is not None and rule.value is not None else {}
        has_wisps = bool(rule_value.get("occupies_champion_slot"))
        if wisp_prob is None:
            wisp_prob = 0.5 if rule_value.get("every_other_shop") else 1.0
            every = rule_value.get("every_shop_with")
            if every and (active_traits or {}).get(every["trait"], 0) >= every["min_units"]:
                wisp_prob = 1.0
        if not has_wisps or wisp_bought:
            wisp_prob = 0.0
        odds = {int(k): tuple(v) for k, v in data.get("shop_odds").items()}
        if wisp_bought:
            name = "independent+wisp_bought"
        else:
            name = "independent+wisp" if wisp_prob > 0 else "independent"
        return cls(odds, data.get("shop_slots"), wisp_prob, name)
