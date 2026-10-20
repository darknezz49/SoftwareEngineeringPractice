"""Item identifiers and the transaction line items.

``ItemID`` is a conceptual "data type" class; ``SalesLineItem`` and
``ReturnLineItem`` are the line items of a transaction.  A line item is an
**Information Expert** for its own subtotal because it knows its quantity and
its product specification.
"""
from __future__ import annotations

from .money import Money

__all__ = ["ItemID", "SalesLineItem", "ReturnLineItem"]


class ItemID:
    """The barcode / UPC that identifies a kind of product."""

    __slots__ = ("_value",)

    def __init__(self, value: str):
        value = str(value).strip()
        if not value:
            raise ValueError("ItemID must not be empty")
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ItemID) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ItemID({self._value!r})"


class SalesLineItem:
    """One line of a :class:`~pos.domain.sale.Sale`: a quantity of a product.

    Information Expert: it knows ``quantity`` and its
    :class:`~pos.domain.catalog.ProductSpecification`, therefore it - not
    ``Sale`` - computes the subtotal (GRASP *Information Expert*).
    """

    __slots__ = ("_specification", "_quantity")

    def __init__(self, specification, quantity: int = 1):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._specification = specification
        self._quantity = int(quantity)

    @property
    def specification(self):
        return self._specification

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def item_id(self) -> ItemID:
        return self._specification.item_id

    @property
    def description(self) -> str:
        return self._specification.description

    @property
    def unit_price(self) -> Money:
        return self._specification.price

    def get_subtotal(self) -> Money:
        """Information Expert: quantity x unit price."""
        return self._specification.price * self._quantity

    def increase_quantity(self, delta: int = 1) -> None:
        if self._quantity + delta <= 0:
            raise ValueError("quantity must remain positive")
        self._quantity += delta

    def __str__(self) -> str:
        return (
            f"{self._quantity} x {self._specification.description} "
            f"@ {self._specification.price} = {self.get_subtotal()}"
        )

    def __repr__(self) -> str:
        return (
            f"SalesLineItem({self._specification.item_id!r}, "
            f"qty={self._quantity})"
        )


class ReturnLineItem:
    """One line of a :class:`~pos.domain.returns.ReturnTransaction`.

    Records how many units of a sold product the customer brings back and
    whether the item is resellable (a returned, undamaged item goes back on
    the shelf; a damaged one does not).
    """

    __slots__ = ("_specification", "_quantity", "_resellable")

    def __init__(self, specification, quantity: int = 1,
                 resellable: bool = True):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._specification = specification
        self._quantity = int(quantity)
        self._resellable = bool(resellable)

    @property
    def specification(self):
        return self._specification

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def item_id(self) -> ItemID:
        return self._specification.item_id

    @property
    def description(self) -> str:
        return self._specification.description

    @property
    def unit_price(self) -> Money:
        return self._specification.price

    @property
    def resellable(self) -> bool:
        return self._resellable

    def set_resellable(self, value: bool) -> None:
        self._resellable = bool(value)

    def increase_quantity(self, delta: int = 1) -> None:
        if self._quantity + delta <= 0:
            raise ValueError("quantity must remain positive")
        self._quantity += delta

    def get_subtotal(self) -> Money:
        """The amount refunded for this line (Information Expert)."""
        return self._specification.price * self._quantity

    def __str__(self) -> str:
        flag = "" if self._resellable else " (damaged, not resellable)"
        return (
            f"{self._quantity} x {self._specification.description} "
            f"@ {self._specification.price} = {self.get_subtotal()}{flag}"
        )

    def __repr__(self) -> str:
        return (
            f"ReturnLineItem({self._specification.item_id!r}, "
            f"qty={self._quantity}, resellable={self._resellable})"
        )
