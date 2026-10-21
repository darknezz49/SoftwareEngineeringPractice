"""The ``Sale`` aggregate and its state machine.

``Sale`` is the central **Creator**: it creates and aggregates its own
``SalesLineItem`` instances (GRASP *Creator*), and it is the **Information
Expert** for the sale total (``get_total``) because it holds the line items.

A sale moves through an explicit little state machine, which keeps the
"make payment only once, and only for a non-empty sale" business rule in the
domain instead of in the UI.
"""
from __future__ import annotations

import itertools
from datetime import datetime
from enum import Enum

from .items import ItemID, SalesLineItem
from .money import Money
from .payment import Payment

__all__ = ["Sale", "SaleState", "EmptySaleError", "SaleStateError"]

_sale_sequence = itertools.count(1)


class SaleState(Enum):
    """Lifecycle of a sale."""

    OPEN = "open"           # items are being entered
    PAID = "paid"           # payment authorised, sale complete
    VOIDED = "voided"       # cancelled before payment


class EmptySaleError(ValueError):
    """Raised when payment is attempted on a sale with no line items."""


class SaleStateError(RuntimeError):
    """Raised when an operation is illegal in the current sale state."""


class Sale:
    """A sale: the transaction that records the purchase of goods."""

    def __init__(self, cashier=None, store=None, customer=None,
                 when: datetime | None = None, sale_id: str | None = None):
        self._id = sale_id or f"S{next(_sale_sequence):06d}"
        self._time = when or datetime.now()
        self._cashier = cashier
        self._store = store
        self._customer = customer
        self._line_items: list[SalesLineItem] = []
        self._payments: list[Payment] = []
        self._state = SaleState.OPEN

    # -- identity -------------------------------------------------------
    @property
    def id(self) -> str:
        return self._id

    @property
    def time(self) -> datetime:
        return self._time

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
    def state(self) -> SaleState:
        return self._state

    @property
    def is_complete(self) -> bool:
        return self._state is SaleState.PAID

    # -- line items (Creator) -------------------------------------------
    @property
    def line_items(self) -> tuple[SalesLineItem, ...]:
        return tuple(self._line_items)

    def make_line_item(self, specification, quantity: int = 1) -> SalesLineItem:
        """Create and add a line item.  The ``Sale`` is the Creator.

        (GRASP *Creator*: ``Sale`` aggregates ``SalesLineItem``, so `Sale` is
        the right object to create it - see the book's Figure 17.13.)
        """
        if self._state is not SaleState.OPEN:
            raise SaleStateError(
                f"cannot add items to a sale in state {self._state.value}"
            )
        line_item = SalesLineItem(specification, quantity)
        self._line_items.append(line_item)
        return line_item

    def remove_line_item(self, item_id: ItemID | str) -> bool:
        """Remove every line for ``item_id``; return True if something went."""
        if self._state is not SaleState.OPEN:
            raise SaleStateError(
                f"cannot modify a sale in state {self._state.value}"
            )
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        before = len(self._line_items)
        self._line_items = [li for li in self._line_items
                            if li.item_id != key]
        return len(self._line_items) != before

    def find_line_item(self, item_id: ItemID | str) -> SalesLineItem | None:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        for li in self._line_items:
            if li.item_id == key:
                return li
        return None

    def is_empty(self) -> bool:
        return not self._line_items

    def item_count(self) -> int:
        return sum(li.quantity for li in self._line_items)

    # -- totals (Information Expert) -------------------------------------
    def get_total(self) -> Money:
        """Information Expert: ``Sale`` knows all its line items' subtotals."""
        total = Money.zero()
        for line_item in self._line_items:
            total = total + line_item.get_subtotal()
        return total

    # -- payment ---------------------------------------------------------
    @property
    def payments(self) -> tuple[Payment, ...]:
        return tuple(self._payments)

    def make_payment(self, payment: Payment) -> Payment:
        """Authorise and attach a payment, completing the sale.

        Business rule enforced here (not in the UI): the sale must not be
        empty, must still be open, and the payment must cover the total.
        """
        if self._state is not SaleState.OPEN:
            raise SaleStateError(
                f"sale {self._id} is already {self._state.value}"
            )
        if self.is_empty():
            raise EmptySaleError(
                f"sale {self._id} has no line items to pay for"
            )
        total = self.get_total()
        if payment.amount < total:
            raise ValueError(
                f"payment {payment.amount} does not cover the total {total}"
            )

        payment.authorize()
        self._payments.append(payment)
        self._state = SaleState.PAID
        return payment

    def get_amount_paid(self) -> Money:
        total = Money.zero()
        for payment in self._payments:
            total = total + payment.amount
        return total

    def get_change_due(self) -> Money:
        change = Money.zero()
        for payment in self._payments:
            change_from_payment = getattr(payment, "change", None)
            if change_from_payment is not None:
                change = change + change_from_payment
        return change

    def void(self) -> None:
        """Cancel the sale before payment."""
        if self._state is SaleState.PAID:
            raise SaleStateError("a paid sale cannot be voided; use a return")
        self._state = SaleState.VOIDED

    def __str__(self) -> str:
        return f"Sale {self._id} ({len(self._line_items)} lines, {self.get_total()})"

    def __repr__(self) -> str:
        return (f"Sale({self._id!r}, state={self._state.value}, "
                f"total={str(self.get_total())!r})")
