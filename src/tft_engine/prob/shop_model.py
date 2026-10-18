"""Shop models.

A shop model answers two questions: how many champion slots shop number i
has, and with what probability each slot rolls each cost tier at a level.
Given the tier, a slot picks a champion in proportion to the copies left in
the pool (``IndependentShopModel``). That last step is the commonly assumed
model; it is not confirmed by Riot and is tested against observed shops in M1b.

Other models (bad luck protection, set-specific rules) implement the same
interface, so the exact solver and the sampler work with any of them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from tft_engine.gamedata import GameData


class ShopModel(Protocol):
    name: str
    assumptions: tuple[str, ...]
    period: int  # champion_slots(i) == champion_slots(i + period) for all i

    def champion_slots(self, shop_index: int) -> int: ...

    def tier_probs(self, level: int) -> tuple[float, float, float, float, float]: ...


@dataclass(frozen=True)
class IndependentShopModel:
    """Every slot is drawn independently from the pool as it stands at the shop.

    wisp_takes_slot: if True, every other shop (indices 1, 3, 5...) has one
    champion slot fewer. This is the unverified Set 18 Wisp variant.
    """

    odds_pct: Mapping[int, tuple[float, ...]]
    slots: int = 5
    wisp_takes_slot: bool = False
    name: str = "independent"

    def __post_init__(self) -> None:
        for level, row in self.odds_pct.items():
            if len(row) != 5 or abs(sum(row) - 100) > 1e-6:
                raise ValueError(f"odds for level {level} must be 5 values summing to 100")

    @property
    def assumptions(self) -> tuple[str, ...]:
        a = [
            "slots are drawn independently from the pool at the time of the shop",
            "within a cost tier, a champion is picked in proportion to its copies left",
            "no bad luck protection",
            "slots are drawn with replacement: when few copies are left, one shop can show "
            "more copies than exist; purchases are capped at the copies left (to check in M1b)",
        ]
        if self.wisp_takes_slot:
            a.append("a Wisp takes one champion slot in every other shop (not checked in-game)")
        return tuple(a)

    @property
    def period(self) -> int:
        return 2 if self.wisp_takes_slot else 1

    def champion_slots(self, shop_index: int) -> int:
        if self.wisp_takes_slot and shop_index % 2 == 1:
            return self.slots - 1
        return self.slots

    def tier_probs(self, level: int) -> tuple[float, float, float, float, float]:
        try:
            row = self.odds_pct[level]
        except KeyError:
            raise ValueError(f"no shop odds for level {level}") from None
        return tuple(x / 100 for x in row)  # type: ignore[return-value]

    @classmethod
    def from_gamedata(
        cls, data: GameData, wisp_takes_slot: bool | None = None
    ) -> IndependentShopModel:
        """wisp_takes_slot=None follows the set's `wisp_slot` rule when it has one."""
        if wisp_takes_slot is None:
            wisp_takes_slot = False
            rule = data.shop_rules.get("wisp_slot")
            if rule is not None and rule.value is not None:
                wisp_takes_slot = bool(rule.value.get("occupies_champion_slot"))
        odds = {int(k): tuple(v) for k, v in data.get("shop_odds").items()}
        name = "independent+wisp_slot" if wisp_takes_slot else "independent"
        return cls(odds, data.get("shop_slots"), wisp_takes_slot, name)
