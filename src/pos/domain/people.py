"""Actors and their roles in the POS domain.

These are the domain's "roles of people or organisations" conceptual classes.
They intentionally hold almost no logic - they are identified by an id and a
name, and they exist so that a ``Sale`` can be attributed to a ``Cashier`` and
a ``Store``.
"""
from __future__ import annotations

__all__ = ["Person", "Cashier", "Customer", "Store"]


class Person:
    """Base class for a human role in the domain."""

    def __init__(self, identifier: str, name: str = ""):
        identifier = str(identifier).strip()
        if not identifier:
            raise ValueError("identifier must not be empty")
        self._id = identifier
        self._name = str(name).strip() or identifier

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._id))

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._id!r}, {self._name!r})"


class Cashier(Person):
    """The primary actor who operates the register."""


class Customer(Person):
    """The customer buying or returning goods.

    A walk-in customer has no loyalty id; ``Customer`` therefore has a
    ``walk_in`` convenience constructor.
    """

    @classmethod
    def walk_in(cls) -> "Customer":
        return cls("WALK-IN", "Walk-in customer")


class Store:
    """The store where the sale/return happens (place of transaction)."""

    def __init__(self, store_id: str, name: str, address: str = ""):
        self._id = str(store_id).strip()
        self._name = str(name).strip()
        self._address = str(address).strip()
        if not self._id or not self._name:
            raise ValueError("store id and name are required")

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"Store({self._id!r}, {self._name!r})"
