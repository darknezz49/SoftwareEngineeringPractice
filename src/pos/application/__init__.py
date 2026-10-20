"""Application layer: one controller per use case.

Each controller realises the system operations identified in the use case
model's System Sequence Diagrams, coordinates the domain and technical services,
and returns plain result objects that a UI can render.  The controllers know
about the domain, and the domain knows nothing about them.

**Controller (GRASP)** is applied here: the first object beyond the UI layer
that receives and coordinates a system operation is a *use case controller*,
named ``<UseCase>Controller``.
"""
from .pos_application import (
    LineItemView,
    POSApplication,
    ProcessSaleController,
    HandleReturnsController,
    RefundResult,
    SaleResult,
    TransactionError,
    build_application,
)

__all__ = [
    "HandleReturnsController",
    "LineItemView",
    "POSApplication",
    "ProcessSaleController",
    "RefundResult",
    "SaleResult",
    "TransactionError",
    "build_application",
]
