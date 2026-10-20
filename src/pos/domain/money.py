"""Monetary values for the POS system.

A tiny value object wrapping :class:`decimal.Decimal` so that money is never
represented with binary floating point (a classic POS defect).  ``Money`` is
immutable and supports the arithmetic the domain needs.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

__all__ = ["Money", "CENT"]

CENT = Decimal("0.01")


class Money:
    """An immutable amount of money in a single currency."""

    __slots__ = ("_amount",)

    def __init__(self, amount: Decimal | int | str | "Money" = 0):
        if isinstance(amount, Money):
            self._amount = amount._amount
        elif isinstance(amount, Decimal):
            self._amount = amount
        else:
            # int/str are both exact; float is deliberately rejected.
            if isinstance(amount, float):
                raise TypeError(
                    "Money(float) is not allowed - use a str or Decimal "
                    "to avoid binary rounding errors"
                )
            self._amount = Decimal(amount)
        self._amount = self._amount.quantize(CENT, rounding=ROUND_HALF_UP)

    # -- construction helpers -------------------------------------------
    @classmethod
    def zero(cls) -> "Money":
        return cls(Decimal("0"))

    # -- arithmetic -----------------------------------------------------
    def __add__(self, other: "Money") -> "Money":
        return Money(self._amount + other._amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self._amount - other._amount)

    def __mul__(self, factor: int | Decimal) -> "Money":
        return Money(self._amount * Decimal(factor))

    __rmul__ = __mul__

    def __neg__(self) -> "Money":
        return Money(-self._amount)

    def __abs__(self) -> "Money":
        return Money(abs(self._amount))

    # -- comparison -----------------------------------------------------
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Money) and self._amount == other._amount

    def __lt__(self, other: "Money") -> bool:
        return self._amount < other._amount

    def __le__(self, other: "Money") -> bool:
        return self._amount <= other._amount

    def __gt__(self, other: "Money") -> bool:
        return self._amount > other._amount

    def __ge__(self, other: "Money") -> bool:
        return self._amount >= other._amount

    def __hash__(self) -> int:
        return hash(self._amount)

    def is_zero(self) -> bool:
        return self._amount == 0

    def is_negative(self) -> bool:
        return self._amount < 0

    # -- rendering ------------------------------------------------------
    @property
    def amount(self) -> Decimal:
        return self._amount

    def __str__(self) -> str:
        return f"{self._amount:.2f}"

    def __repr__(self) -> str:
        return f"Money('{self._amount:.2f}')"
