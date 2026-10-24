"""Audit log and catalogue bootstrap data.

* :class:`AuditLog` - a small technical service that records the system
  operations the POS performed, useful for the report's screenshots and for
  post-hoc debugging.
* :func:`build_default_catalog` / :func:`build_default_inventory` - the demo
  stock of the small supermarket, kept in one place so the UI, the tests and
  the report all describe the same shop.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from ..domain.catalog import ProductCatalog, ProductSpecification
from ..domain.inventory import InventoryService

__all__ = [
    "AuditEntry",
    "AuditLog",
    "DEFAULT_PRODUCTS",
    "build_default_catalog",
    "build_default_inventory",
    "seed_store",
]


@dataclass(frozen=True)
class AuditEntry:
    """One line of the audit trail."""

    when: datetime
    operation: str
    detail: str
    outcome: str = "ok"

    def __str__(self) -> str:
        return (f"{self.when:%H:%M:%S}  {self.operation:<20} "
                f"{self.outcome:<8} {self.detail}")


class AuditLog:
    """An append-only, in-memory log of system operations."""

    def __init__(self, limit: int = 1000):
        self._entries: list[AuditEntry] = []
        self._limit = int(limit)

    def record(self, operation: str, detail: str = "", outcome: str = "ok") -> None:
        self._entries.append(
            AuditEntry(datetime.now(), operation, detail, outcome)
        )
        if len(self._entries) > self._limit:
            del self._entries[0:len(self._entries) - self._limit]

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    def recent(self, limit: int = 20) -> list[AuditEntry]:
        return self._entries[-limit:][::-1]

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# The demo shop
# ---------------------------------------------------------------------------
# (item id, description, price, tax rate, opening stock)
DEFAULT_PRODUCTS: tuple[tuple[str, str, str, str, int], ...] = (
    ("1001", "ObjectBurger  Veggie Burger", "4.50", "0.06", 24),
    ("1002", "Whole Milk 1L", "2.20", "0.06", 40),
    ("1003", "Sliced Bread 500g", "3.10", "0.06", 18),
    ("1004", "Free-range Eggs (12)", "4.90", "0.06", 15),
    ("1005", "Arabica Coffee Beans 250g", "8.80", "0.06", 12),
    ("1006", "Green Tea 20 bags", "3.60", "0.06", 30),
    ("1007", "Sparkling Water 6x500ml", "5.40", "0.06", 20),
    ("1008", "Dark Chocolate 100g", "2.80", "0.06", 36),
    ("1009", "Kitchen Towel 2-pack", "1.90", "0.06", 25),
    ("1010", "Dish Soap 500ml", "2.40", "0.06", 22),
    ("1011", "Ballpoint Pen (blue)", "1.20", "0.06", 50),
    ("1012", "A4 Notebook 80 pages", "2.60", "0.06", 28),
)


def build_default_catalog() -> ProductCatalog:
    """Build the demo product catalog."""
    catalog = ProductCatalog()
    for item_id, description, price, tax_rate, _stock in DEFAULT_PRODUCTS:
        catalog.add_specification(
            ProductSpecification(item_id, description, price, tax_rate)
        )
    return catalog


def build_default_inventory() -> InventoryService:
    """Build the demo stock levels."""
    inventory = InventoryService()
    for item_id, _description, _price, _tax, stock in DEFAULT_PRODUCTS:
        inventory.set_level(item_id, stock)
    return inventory


def describe_products(catalog: ProductCatalog) -> str:
    """A human-readable catalogue listing (used by the README and the UI)."""
    lines = [f"{'ID':<6} {'Description':<30} {'Price':>8}  {'Tax':>5}"]
    lines.append("-" * 54)
    for spec in catalog.all_specifications():
        lines.append(f"{str(spec.item_id):<6} {spec.description:<30} "
                     f"{str(spec.price):>8}  {spec.tax_rate:>5}")
    return "\n".join(lines)


def seed_store():
    """Convenience: return (catalog, inventory) for the demo shop."""
    return build_default_catalog(), build_default_inventory()


def load_products(path) -> ProductCatalog:
    """Load a catalogue from a JSON file of product records."""
    catalog = ProductCatalog()
    data = json.loads(open(path, encoding="utf-8").read())
    for record in data:
        catalog.add_specification(
            ProductSpecification(
                record["itemId"],
                record["description"],
                record["price"],
                record.get("taxRate", "0.00"),
            )
        )
    return catalog
