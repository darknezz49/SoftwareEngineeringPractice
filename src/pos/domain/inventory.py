"""Inventory (stock-on-hand) service.

The Process Sale and Handle Returns use cases both say the system
"updates inventory".  Stock-on-hand is not a concept of the conceptual domain
model (nobody counts the shelf in a class diagram), so it lives in a small
technical/domain service rather than in ``ProductSpecification``:

* keeping it out of ``ProductSpecification`` avoids mixing the *description* of
  a product with its *current stock level* (High Cohesion, Protected
  Variations - the stock-keeping strategy can change without touching the
  description class).
"""
from __future__ import annotations

from .items import ItemID

__all__ = ["InventoryService", "InsufficientStockError", "UnknownItemError"]


class UnknownItemError(KeyError):
    """Raised when an item id is not stocked at all."""


class InsufficientStockError(ValueError):
    """Raised when a sale asks for more units than are on hand."""

    def __init__(self, item_id: ItemID, requested: int, available: int):
        super().__init__(
            f"insufficient stock for {item_id}: "
            f"requested {requested}, available {available}"
        )
        self.item_id = item_id
        self.requested = requested
        self.available = available


class InventoryService:
    """Tracks units on hand per :class:`ItemID`."""

    def __init__(self, levels: dict[str, int] | None = None):
        self._levels: dict[ItemID, int] = {}
        for key, qty in (levels or {}).items():
            self._levels[ItemID(key)] = int(qty)

    # -- setup ----------------------------------------------------------
    def set_level(self, item_id: ItemID | str, quantity: int) -> None:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        self._levels[key] = int(quantity)

    def restock(self, item_id: ItemID | str, quantity: int) -> int:
        """Add ``quantity`` units (used by returns of resellable goods)."""
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        if key not in self._levels:
            raise UnknownItemError(str(key))
        self._levels[key] += int(quantity)
        return self._levels[key]

    # -- queries --------------------------------------------------------
    def get_level(self, item_id: ItemID | str) -> int:
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        if key not in self._levels:
            raise UnknownItemError(str(key))
        return self._levels[key]

    def is_available(self, item_id: ItemID | str, quantity: int) -> bool:
        try:
            return self.get_level(item_id) >= int(quantity)
        except UnknownItemError:
            return False

    def on_hand(self) -> dict[str, int]:
        return {str(k): v for k, v in sorted(
            self._levels.items(), key=lambda kv: str(kv[0]))}

    # -- mutations ------------------------------------------------------
    def remove(self, item_id: ItemID | str, quantity: int) -> int:
        """Take ``quantity`` units out of stock (a sale)."""
        key = item_id if isinstance(item_id, ItemID) else ItemID(item_id)
        if key not in self._levels:
            raise UnknownItemError(str(key))
        qty = int(quantity)
        if self._levels[key] < qty:
            raise InsufficientStockError(key, qty, self._levels[key])
        self._levels[key] -= qty
        return self._levels[key]
