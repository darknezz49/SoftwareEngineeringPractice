"""The Handle Returns use case's transaction object.

A ``ReturnTransaction`` mirrors the structure of the process-sale
``Sale`` - the book's "比着葫芦画瓢" (model the second use case after the first):
same transaction + line-item shape, but the money flows the other way and the
item can be flagged as damaged so that it is *not* put back on the shelf.
"""
from __future__ import annotations

import itertools
from datetime import datetime
from enum import Enum

from .items import ItemID, ReturnLineItem
from .money import Money

__all__ = [
    "ReturnTransaction",
    "ReturnState",
    "ReturnAuthorizationError",
    "EmptyReturnError",
]

_return_sequence = itertools.count(1)


class ReturnState(Enum):
    """Lifecycle of a return."""

    OPEN = "open"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class EmptyReturnError(ValueError):
    """Raised when a refund is attempted with nothing to return."""


class ReturnAuthorizationError(RuntimeError):
    """Raised when a return is not permitted by policy."""


class ReturnTransaction:
    """A return of goods by a customer, producing a refund."""

    def __init__(self, original_sale=None, cashier=None, store=None,
                 customer=None, reason: str = "",
                 when: datetime | None = None, return_id: str | None = None):
        self._id = return_id or f"R{next(_return_sequence):06d}"
        self._time = when or datetime.now()
        self._original_sale = original_sale
        self._cashier = cashier
        self._store = store
        self._customer = customer or getattr(original_sale, "customer", None)
        self._reason = str(reason).strip()
        self._line_items: list[ReturnLineItem] = []
        self._state = ReturnState.OPEN
        self._refund = Money.zero()

    # -- identity --------------------------------------------------------
    @property
    def id(self) -> str:
        return self._id

    @property
    def time(self) -> datetime:
        return self._time

    @property
    def original_sale(self):
        return self._original_sale

    @property
    def cashier(self):
        return self._cashier

    @property
    def store(self):
        return self._store

    @property
    def customer(self):
        return self._customer

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def state(self) -> ReturnState:
        return self._state

    @property
    def refund(self) -> Money:
        return self._refund

    # -- line items (Creator) --------------------------------------------
    @property
    def line_items(self) -> tuple[ReturnLineItem, ...]:
        return tuple(self._line_items)

    def make_line_item(self, specification, quantity: int = 1,
                       resellable: bool = True) -> ReturnLineItem:
        """Create and add a return line.  ``ReturnTransaction`` is the Creator."""
        if self._state is not ReturnState.OPEN:
            raise ReturnAuthorizationError(
                f"cannot modify a return in state {self._state.value}"
            )
        line_item = ReturnLineItem(specification, quantity, resellable)
        self._line_items.append(line_item)
        return line_item

    def remove_line_item(self, item_id: ItemID | str) -> bool:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        before = len(self._line_items)
        self._line_items = [li for li in self._line_items if li.item_id != key]
        return len(self._line_items) != before

    def find_line_item(self, item_id: ItemID | str) -> ReturnLineItem | None:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        for li in self._line_items:
            if li.item_id == key:
                return li
        return None

    def is_empty(self) -> bool:
        return not self._line_items

    def item_count(self) -> int:
        return sum(li.quantity for li in self._line_items)

    # -- money (Information Expert) --------------------------------------
    def get_refund_total(self) -> Money:
        """Information Expert: only the return knows its returned lines."""
        total = Money.zero()
        for line_item in self._line_items:
            total = total + line_item.get_subtotal()
        return total

    def resellable_lines(self) -> tuple[ReturnLineItem, ...]:
        return tuple(li for li in self._line_items if li.resellable)

    def damaged_lines(self) -> tuple[ReturnLineItem, ...]:
        return tuple(li for li in self._line_items if not li.resellable)

    # -- completion ------------------------------------------------------
    def authorize_refund(self, method: str = "cash") -> Money:
        """Declare the refund payable and close the return.

        Policy enforced in the domain, not the UI: a return must not be empty,
        must still be open, and may not exceed what was originally paid when
        the original sale is known.
        """
        if self._state is not ReturnState.OPEN:
            raise ReturnAuthorizationError(
                f"return {self._id} is already {self._state.value}"
            )
        if self.is_empty():
            raise EmptyReturnError(
                f"return {self._id} has no line items to refund"
            )

        refund = self.get_refund_total()

        if self._original_sale is not None:
            original_total = self._original_sale.get_total()
            if refund > original_total:
                raise ReturnAuthorizationError(
                    f"refund {refund} exceeds the original sale total "
                    f"{original_total}"
                )

        self._refund = refund
        self._state = ReturnState.REFUNDED
        self._refund_method = method
        return refund

    @property
    def refund_method(self) -> str:
        return getattr(self, "_refund_method", "")

    def cancel(self) -> None:
        if self._state is ReturnState.REFUNDED:
            raise ReturnAuthorizationError("a refunded return cannot be cancelled")
        self._state = ReturnState.CANCELLED

    def __str__(self) -> str:
        return (f"Return {self._id} ({len(self._line_items)} lines, "
                f"refund {self.get_refund_total()})")

    def __repr__(self) -> str:
        return (f"ReturnTransaction({self._id!r}, "
                f"state={self._state.value}, "
                f"refund={str(self.get_refund_total())!r})")
