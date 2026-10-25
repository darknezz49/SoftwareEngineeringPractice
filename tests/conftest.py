"""Shared test fixtures."""
from __future__ import annotations

import os
import sys

import pytest

# Make ``src`` importable without installing the package.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from pos.application import build_application  # noqa: E402
from pos.domain import (  # noqa: E402
    Cashier,
    Money,
    ProductCatalog,
    ProductSpecification,
    Store,
)


@pytest.fixture()
def catalog() -> ProductCatalog:
    """A tiny three-product catalogue."""
    catalog = ProductCatalog()
    catalog.add_specification(ProductSpecification("1001", "Veggie Burger", "4.50"))
    catalog.add_specification(ProductSpecification("1002", "Whole Milk 1L", "2.20"))
    catalog.add_specification(ProductSpecification("1005", "Coffee Beans 250g", "8.80"))
    return catalog


@pytest.fixture()
def app():
    """A fully wired application using the default demo shop."""
    return build_application(gateway_kind="simulated")


@pytest.fixture()
def small_app(catalog):
    """An application over the three-product catalogue, 10 units each."""
    from pos.domain import InventoryService

    inventory = InventoryService()
    for spec in catalog.all_specifications():
        inventory.set_level(spec.item_id, 10)

    return build_application(
        gateway_kind="simulated",
        store=Store("S001", "Test Store"),
        cashier=Cashier("C001", "Tester"),
        catalog=catalog,
        inventory=inventory,
    )


@pytest.fixture()
def money():
    """Convenience factory for Money values in tests."""
    return Money
