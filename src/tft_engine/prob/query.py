"""The roll-down question and the buying policy both solvers share."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    """Copies of one champion to buy.

    share: the part of its shop appearances that count, for champions whose
    form is picked at random in the shop (Set 18 Lux: 1 / number of forms while
    the player owns none; once one is owned, every Lux shows in that form, so
    another form has share 0). It applies until the first copy is bought in the
    roll-down, then 1.
    """

    unit_id: str
    copies_needed: int
    share: float = 1.0

    def __post_init__(self) -> None:
        if self.copies_needed < 0:
            raise ValueError("copies_needed must be >= 0")
        if not 0.0 <= self.share <= 1.0:
            raise ValueError("share must be in [0, 1]")


@dataclass(frozen=True)
class RollQuery:
    """Roll at a fixed level until every target is bought or gold runs low.

    Policy (identical in the exact solver and the sampler):
      1. Look at the shop. The first shop is free if ``first_shop_free``
         (it is already on screen); every later shop costs ``roll_cost``,
         except that the first ``free_rolls`` rolls cost nothing (free
         rerolls from augments are always used first).
      2. Buy target copies that appear, in the order of ``targets``, while
         copies are still needed and gold covers the unit cost.
      3. If every target is complete, stop: success.
      4. Otherwise roll again only if gold after paying ``roll_cost`` stays
         at or above ``gold_floor``; else stop: failure.
    """

    level: int
    gold: int
    targets: tuple[Target, ...]
    roll_cost: int
    gold_floor: int = 0
    first_shop_free: bool = True
    max_shops: int = 200  # safety cap; never reached with sane inputs
    free_rolls: int = 0

    def __post_init__(self) -> None:
        if self.gold < 0 or self.roll_cost <= 0 or self.gold_floor < 0:
            raise ValueError("gold and gold_floor must be >= 0, roll_cost > 0")
        if self.free_rolls < 0:
            raise ValueError("free_rolls must be >= 0")

    def price(self, free_left: int) -> int:
        """Gold paid for the next roll."""
        return 0 if free_left > 0 else self.roll_cost
        if not self.targets:
            raise ValueError("at least one target is required")
        ids = [t.unit_id for t in self.targets]
        if len(set(ids)) != len(ids):
            raise ValueError("targets must be distinct units")
