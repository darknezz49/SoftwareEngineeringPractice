"""Receipt: a report of a completed sale.

Per the book's Guideline *"Report Objects - Include 'Receipt' in the Model?"*,
a receipt is a **report** of a sale and its payment; putting it in the
conceptual domain model would duplicate information.  So ``Receipt`` is a
*report object* built on demand from a completed ``Sale`` rather than a
persistent conceptual class of the domain.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .money import Money

__all__ = ["ReceiptLine", "Receipt"]


@dataclass(frozen=True)
class ReceiptLine:
    """One printed line of a receipt."""

    description: str
    quantity: int
    unit_price: Money
    subtotal: Money

    def __str__(self) -> str:
        return (f"{self.quantity:>3} x {self.description:<20} "
                f"{str(self.unit_price):>8}  {str(self.subtotal):>9}")


class Receipt:
    """An immutable printed record of a sale or a return."""

    def __init__(self, title: str, store_name: str, transaction_id: str,
                 when: datetime, lines: list[ReceiptLine], total: Money,
                 cashier_name: str = "", extra: list[str] | None = None):
        self._title = title
        self._store_name = store_name
        self._transaction_id = transaction_id
        self._when = when
        self._lines = list(lines)
        self._total = total
        self._cashier_name = cashier_name
        self._extra = list(extra or [])

    # -- accessors -------------------------------------------------------
    @property
    def title(self) -> str:
        return self._title

    @property
    def store_name(self) -> str:
        return self._store_name

    @property
    def transaction_id(self) -> str:
        return self._transaction_id

    @property
    def when(self) -> datetime:
        return self._when

    @property
    def lines(self) -> tuple[ReceiptLine, ...]:
        return tuple(self._lines)

    @property
    def total(self) -> Money:
        return self._total

    @property
    def cashier_name(self) -> str:
        return self._cashier_name

    @property
    def extra(self) -> tuple[str, ...]:
        return tuple(self._extra)

    # -- rendering -------------------------------------------------------
    def to_text(self, width: int = 46) -> str:
        """Render a plain-text receipt (as it would print on a till roll)."""
        rule = "-" * width
        out = [
            self._store_name.center(width),
            self._title.center(width),
            rule,
            f"Receipt : {self._transaction_id}",
            f"Date    : {self._when:%Y-%m-%d %H:%M:%S}",
        ]
        if self._cashier_name:
            out.append(f"Cashier : {self._cashier_name}")
        out.append(rule)
        for line in self._lines:
            out.append(str(line))
        out.append(rule)
        out.append(f"{'TOTAL':<32}{str(self._total):>14}")
        for item in self._extra:
            out.append(item)
        out.append(rule)
        out.append("Thank you for shopping with us!".center(width))
        return "\n".join(out)

    def __str__(self) -> str:
        return self.to_text()

    def __repr__(self) -> str:
        return (f"Receipt({self._transaction_id!r}, "
                f"{len(self._lines)} lines, total={str(self._total)!r})")
