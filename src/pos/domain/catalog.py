"""Product description and catalog.

``ProductSpecification`` is the *Description* class of the domain model: it
records the description and price of a *kind* of product, independent of
whether any physical ``Item`` of that kind currently exists.  A
``ProductCatalog`` is the information expert for looking a specification up by
``ItemID``.
"""
from __future__ import annotations

from .items import ItemID
from .money import Money

__all__ = ["ProductSpecification", "ProductCatalog"]


class ProductSpecification:
    """Description of a product: id, description, unit price, tax rate.

    Description class (formerly the *Item-Descriptor* pattern).  It never
    carries a serial number, because it does not represent a physical instance.
    """

    __slots__ = ("_item_id", "_description", "_price", "_tax_rate")

    def __init__(self, item_id: ItemID | str, description: str,
                 price: Money | str | int, tax_rate: str = "0.00"):
        self._item_id = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        if not str(description).strip():
            raise ValueError("description must not be empty")
        self._description = str(description).strip()
        self._price = price if isinstance(price, Money) else Money(price)
        if self._price.is_negative():
            raise ValueError("price must not be negative")
        self._tax_rate = str(tax_rate)

    @property
    def item_id(self) -> ItemID:
        return self._item_id

    @property
    def description(self) -> str:
        return self._description

    @property
    def price(self) -> Money:
        return self._price

    @property
    def tax_rate(self) -> str:
        return self._tax_rate

    def set_price(self, price: Money | str) -> None:
        self._price = price if isinstance(price, Money) else Money(price)

    def __str__(self) -> str:
        return f"{self._item_id} - {self._description} ({self._price})"

    def __repr__(self) -> str:
        return (
            f"ProductSpecification({self._item_id!r}, "
            f"{self._description!r}, {str(self._price)!r})"
        )


class ProductCatalog:
    """The catalog of product specifications, keyed by :class:`ItemID`.

    Information Expert for translating an ``ItemID`` into a
    ``ProductSpecification`` - the very responsibility the book assigns to
    ``ProductCatalog`` in the NextGen POS case study.
    """

    def __init__(self):
        self._specifications: dict[ItemID, ProductSpecification] = {}

    # -- queries --------------------------------------------------------
    def get_specification(self, item_id: ItemID | str) -> ProductSpecification | None:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        return self._specifications.get(key)

    def contains(self, item_id: ItemID | str) -> bool:
        return self.get_specification(item_id) is not None

    def all_specifications(self) -> list[ProductSpecification]:
        return sorted(self._specifications.values(),
                      key=lambda s: str(s.item_id))

    def __len__(self) -> int:
        return len(self._specifications)

    # -- maintenance ----------------------------------------------------
    def add_specification(self, spec: ProductSpecification) -> None:
        self._specifications[spec.item_id] = spec

    def remove_specification(self, item_id: ItemID | str) -> None:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        self._specifications.pop(key, None)
