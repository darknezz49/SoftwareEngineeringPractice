"""POS domain model - conceptual classes of the problem domain.

This package holds the domain layer of the logical architecture: software
objects whose names and information mirror the real-world POS domain
(``Sale``, ``Payment``, ``ProductSpecification``, ...) and which own the
application logic that concerns them.

Design principles applied in this layer:

* **Information Expert** - a class that has the information also does the work
  (``Sale.get_total``, ``SalesLineItem.get_subtotal``).
* **Creator** - the class that aggregates/records something creates it
  (``Sale`` creates ``SalesLineItem``; ``Register`` creates ``Sale``).
* **Low Coupling / High Cohesion** - the domain layer knows nothing about the
  UI, the database or the network.
* **Model-View Separation** - no domain object references a UI object.
"""
from .catalog import ProductCatalog, ProductSpecification
from .inventory import InventoryService
from .items import ItemID, SalesLineItem, ReturnLineItem
from .money import Money
from .payment import CashPayment, CreditPayment, Payment, PaymentFactory
from .people import Cashier, Customer, Store
from .receipt import Receipt, ReceiptLine
from .register import Register
from .returns import ReturnTransaction
from .sale import Sale, SaleState

__all__ = [
    "Cashier",
    "CashPayment",
    "CreditPayment",
    "Customer",
    "InventoryService",
    "ItemID",
    "Money",
    "Payment",
    "PaymentFactory",
    "ProductCatalog",
    "ProductSpecification",
    "Receipt",
    "ReceiptLine",
    "Register",
    "ReturnLineItem",
    "ReturnTransaction",
    "Sale",
    "SaleState",
    "SalesLineItem",
    "Store",
]
