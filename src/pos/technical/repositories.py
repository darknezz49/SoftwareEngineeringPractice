"""In-memory repositories for completed sales and returns.

The Handle Returns use case has to answer *"was this item bought here, and if
so, when and for how much?"* - so completed sales must be looked up.  A tiny
repository hides that storage detail from the domain (Information Expert for
lookup, and a seam where a real database could be plugged in later without
touching the domain).
"""
from __future__ import annotations

from ..domain.returns import ReturnTransaction
from ..domain.sale import Sale

__all__ = ["SaleRepository", "ReturnRepository"]


class SaleRepository:
    """Stores completed sales and finds them by transaction id."""

    def __init__(self):
        self._sales: dict[str, Sale] = {}
        self._order: list[str] = []

    def add(self, sale: Sale) -> None:
        if sale.id not in self._sales:
            self._order.append(sale.id)
        self._sales[sale.id] = sale

    def get(self, sale_id: str) -> Sale | None:
        return self._sales.get(str(sale_id).strip().upper()) or \
            self._sales.get(str(sale_id).strip())

    def all_sales(self) -> list[Sale]:
        return [self._sales[sid] for sid in self._order]

    def recent(self, limit: int = 10) -> list[Sale]:
        return self.all_sales()[-limit:][::-1]

    def find_by_item(self, item_id: str) -> list[Sale]:
        """Every sale that contains ``item_id`` (used by Handle Returns)."""
        key = str(item_id).strip()
        return [s for s in self.all_sales()
                if any(str(li.item_id) == key for li in s.line_items)]

    def total_revenue(self):
        total = None
        for sale in self.all_sales():
            total = sale.get_total() if total is None else total + sale.get_total()
        return total

    def __len__(self) -> int:
        return len(self._sales)

    def __contains__(self, sale_id: object) -> bool:
        return str(sale_id) in self._sales


class ReturnRepository:
    """Stores completed return transactions."""

    def __init__(self):
        self._returns: dict[str, ReturnTransaction] = {}
        self._order: list[str] = []

    def add(self, transaction: ReturnTransaction) -> None:
        if transaction.id not in self._returns:
            self._order.append(transaction.id)
        self._returns[transaction.id] = transaction

    def get(self, return_id: str) -> ReturnTransaction | None:
        return self._returns.get(str(return_id).strip())

    def all_returns(self) -> list[ReturnTransaction]:
        return [self._returns[rid] for rid in self._order]

    def recent(self, limit: int = 10) -> list[ReturnTransaction]:
        return self.all_returns()[-limit:][::-1]

    def total_refunded(self):
        total = None
        for transaction in self.all_returns():
            amount = transaction.refund
            total = amount if total is None else total + amount
        return total

    def __len__(self) -> int:
        return len(self._returns)
