"""Use case controllers for Process Sale and Handle Returns.

The controllers own the *sequence* of a use case, apply cross-cutting policy
(audit logging), and hand back view objects.  They contain no widget code and
no SQL - that separation is the Model-View Separation principle applied to the
application layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..domain.catalog import ProductCatalog
from ..domain.inventory import InventoryService, InsufficientStockError, UnknownItemError
from ..domain.money import Money
from ..domain.payment import (
    PaymentAuthorizationError,
    PaymentFactory,
    UnsupportedPaymentError,
)
from ..domain.people import Cashier, Customer, Store
from ..domain.receipt import Receipt
from ..domain.register import Register
from ..domain.returns import EmptyReturnError, ReturnAuthorizationError
from ..domain.sale import EmptySaleError, SaleStateError
from ..technical.payment_adapters import PaymentGatewayFactory
from ..technical.repositories import ReturnRepository, SaleRepository
from ..technical.store_data import (
    AuditLog,
    build_default_catalog,
    build_default_inventory,
)

__all__ = [
    "TransactionError",
    "LineItemView",
    "SaleResult",
    "RefundResult",
    "ProcessSaleController",
    "HandleReturnsController",
    "POSApplication",
    "build_application",
]


class TransactionError(RuntimeError):
    """A use-case level failure that the UI should report to the cashier."""


# ---------------------------------------------------------------------------
# View objects returned to the presentation layer
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LineItemView:
    """A line item flattened for display (no domain object handed to the UI)."""

    item_id: str
    description: str
    quantity: int
    unit_price: str
    subtotal: str

    @classmethod
    def from_domain(cls, line_item) -> "LineItemView":
        return cls(
            item_id=str(line_item.item_id),
            description=line_item.description,
            quantity=line_item.quantity,
            unit_price=str(line_item.unit_price),
            subtotal=str(line_item.get_subtotal()),
        )


@dataclass(frozen=True)
class SaleResult:
    """The outcome of a completed sale, for the UI to display."""

    sale_id: str
    total: str
    payment_kind: str
    change: str = "0.00"
    reference: str = ""
    receipt_text: str = ""
    item_count: int = 0


@dataclass(frozen=True)
class RefundResult:
    """The outcome of a completed return, for the UI to display."""

    return_id: str
    refund_total: str
    method: str
    original_sale_id: str = ""
    receipt_text: str = ""
    item_count: int = 0
    restocked_units: int = 0
    damaged_units: int = 0


# ---------------------------------------------------------------------------
# Process Sale
# ---------------------------------------------------------------------------
class ProcessSaleController:
    """**Controller** for the *Process Sale* use case.

    Realises the system operations shown on the Process Sale SSD:
    ``makeNewSale``, ``enterItem``, ``removeItem``, ``getTotal``,
    ``makePayment``, ``endSale`` - plus ``cancelTransaction``.
    """

    def __init__(self, register: Register, sale_repository: SaleRepository,
                 audit: AuditLog | None = None,
                 clock: Callable[[], datetime] | None = None):
        self._register = register
        self._sales = sale_repository
        self._audit = audit if audit is not None else AuditLog()
        self._clock = clock or datetime.now

    # -- queries ---------------------------------------------------------
    @property
    def register(self) -> Register:
        return self._register

    @property
    def is_sale_in_progress(self) -> bool:
        return self._register.current_sale is not None

    @property
    def sale_id(self) -> str:
        sale = self._register.current_sale
        return sale.id if sale else ""

    def line_items(self) -> list[LineItemView]:
        sale = self._register.current_sale
        if sale is None:
            return []
        return [LineItemView.from_domain(li) for li in sale.line_items]

    def running_total(self) -> Money:
        sale = self._register.current_sale
        return sale.get_total() if sale else Money.zero()

    def item_count(self) -> int:
        sale = self._register.current_sale
        return sale.item_count() if sale else 0

    def catalog_entries(self) -> list[tuple[str, str, str]]:
        """(item id, description, price) for the UI's product list."""
        return [(str(s.item_id), s.description, str(s.price))
                for s in self._register.catalog.all_specifications()]

    def stock_level(self, item_id: str) -> int:
        return self._register.inventory.get_level(item_id)

    # -- system operations ------------------------------------------------
    def make_new_sale(self) -> str:
        """``makeNewSale`` - start a fresh sale, voiding any open one."""
        if self._register.current_sale is not None:
            self.cancel_transaction()
        sale = self._register.make_new_sale(when=self._clock())
        self._audit.record("makeNewSale", f"sale {sale.id}")
        return sale.id

    def enter_item(self, item_id: str, quantity: int = 1) -> LineItemView:
        """``enterItem(itemID, quantity)`` - record a purchased item."""
        if not self.is_sale_in_progress:
            self._audit.record("enterItem", "no sale in progress", "error")
            raise TransactionError(
                "No sale in progress - press 'New Sale' first."
            )
        try:
            line_item = self._register.enter_item(item_id, quantity)
        except UnknownItemError:
            self._audit.record("enterItem", f"unknown item {item_id}", "error")
            raise TransactionError(
                f"Item {item_id} is not in the catalogue."
            ) from None
        except InsufficientStockError as exc:
            self._audit.record(
                "enterItem",
                f"{item_id} x{quantity} - only {exc.available} in stock",
                "error",
            )
            raise TransactionError(
                f"Only {exc.available} unit(s) of {item_id} in stock."
            ) from None

        self._audit.record(
            "enterItem",
            f"{item_id} x{quantity} -> {line_item.get_subtotal()}",
        )
        return LineItemView.from_domain(line_item)

    def remove_item(self, item_id: str) -> None:
        """``removeItem(itemID)`` - take a line off the sale."""
        if not self._register.remove_item(item_id):
            raise TransactionError(f"Item {item_id} is not on this sale.")
        self._audit.record("removeItem", item_id)

    def get_total(self) -> Money:
        """``getTotal`` - the running total shown on the customer display."""
        return self._register.get_total()

    def make_payment(self, kind: str = "cash", **options) -> SaleResult:
        """``makePayment`` - authorise payment, update inventory, close sale.

        Returns the :class:`SaleResult` **and** leaves the receipt retrievable
        through :meth:`end_sale`.
        """
        try:
            sale = self._register.current_sale
            self._register.make_payment(kind, **options)
        except EmptySaleError:
            raise TransactionError("Cannot pay for an empty sale.") from None
        except SaleStateError as exc:
            raise TransactionError(str(exc)) from None
        except InsufficientStockError as exc:
            self._audit.record("makePayment", str(exc), "error")
            raise TransactionError(str(exc)) from None
        except PaymentAuthorizationError as exc:
            self._audit.record("makePayment", str(exc), "declined")
            raise TransactionError(f"Payment declined: {exc}") from None
        except UnsupportedPaymentError as exc:
            raise TransactionError(str(exc)) from None

        receipt = self._register.end_sale()
        self._sales.add(sale)
        payment = sale.payments[-1]
        self._audit.record(
            "makePayment",
            f"sale {sale.id} {payment.kind} {payment.amount} "
            f"-> {receipt.transaction_id}",
        )
        result = SaleResult(
            sale_id=sale.id,
            total=str(sale.get_total()),
            payment_kind=payment.kind,
            change=str(sale.get_change_due()),
            reference=payment.reference,
            receipt_text=receipt.to_text(),
            item_count=sale.item_count(),
        )
        self._last_receipt = receipt
        return result

    def end_sale(self) -> Receipt:
        """``endSale`` - the printed receipt of the last completed sale."""
        receipt = getattr(self, "_last_receipt", None)
        if receipt is None:
            raise TransactionError("No completed sale to print.")
        return receipt

    def cancel_transaction(self) -> None:
        """``cancelTransaction`` - abandon the sale without touching stock."""
        sale = self._register.current_sale
        if sale is not None:
            self._audit.record("cancelTransaction", f"sale {sale.id}", "void")
        self._register.cancel_current_transaction()


# ---------------------------------------------------------------------------
# Handle Returns
# ---------------------------------------------------------------------------
class HandleReturnsController:
    """**Controller** for the *Handle Returns* use case.

    Realises ``makeNewReturn``, ``enterReturnItem``, ``getRefundTotal``,
    ``authorizeRefund``, ``endReturn`` and ``cancelTransaction`` - the mirror
    image of the Process Sale SSD.
    """

    def __init__(self, register: Register, sale_repository: SaleRepository,
                 return_repository: ReturnRepository,
                 audit: AuditLog | None = None,
                 clock: Callable[[], datetime] | None = None):
        self._register = register
        self._sales = sale_repository
        self._returns = return_repository
        self._audit = audit if audit is not None else AuditLog()
        self._clock = clock or datetime.now

    # -- queries ----------------------------------------------------------
    @property
    def is_return_in_progress(self) -> bool:
        return self._register.current_return is not None

    @property
    def return_id(self) -> str:
        ret = self._register.current_return
        return ret.id if ret else ""

    @property
    def original_sale_id(self) -> str:
        ret = self._register.current_return
        if ret is None or ret.original_sale is None:
            return ""
        return ret.original_sale.id

    def line_items(self) -> list[LineItemView]:
        ret = self._register.current_return
        if ret is None:
            return []
        return [LineItemView.from_domain(li) for li in ret.line_items]

    def refund_total(self) -> Money:
        ret = self._register.current_return
        return ret.get_refund_total() if ret else Money.zero()

    def recent_sales(self, limit: int = 10) -> list[tuple[str, str, int]]:
        """(sale id, total, item count) for the 'look up original sale' list."""
        return [(s.id, str(s.get_total()), s.item_count())
                for s in self._sales.recent(limit)]

    def find_sales_by_item(self, item_id: str) -> list[tuple[str, str, int]]:
        """Sales that contained ``item_id`` - the receipt-less return path."""
        return [(s.id, str(s.get_total()), s.item_count())
                for s in self._sales.find_by_item(item_id)]

    # -- system operations -------------------------------------------------
    def make_new_return(self, original_sale_id: str = "",
                        reason: str = "") -> str:
        """``makeNewReturn`` - begin a return, optionally linked to a sale."""
        if self._register.current_return is not None:
            self.cancel_transaction()

        original_sale = None
        if str(original_sale_id).strip():
            original_sale = self._sales.get(original_sale_id)
            if original_sale is None:
                raise TransactionError(
                    f"Sale {original_sale_id} was not found in this store."
                )

        ret = self._register.make_new_return(
            original_sale=original_sale, reason=reason, when=self._clock()
        )
        self._audit.record(
            "makeNewReturn",
            f"return {ret.id} for sale {original_sale_id or 'n/a'}",
        )
        return ret.id

    def enter_return_item(self, item_id: str, quantity: int = 1,
                          resellable: bool = True) -> LineItemView:
        """``enterReturnItem(itemID, quantity)`` - record a returned item."""
        try:
            line_item = self._register.enter_return_item(
                item_id, quantity, resellable=resellable
            )
        except UnknownItemError:
            self._audit.record("enterReturnItem", f"unknown item {item_id}",
                               "error")
            raise TransactionError(
                f"Item {item_id} is not in the catalogue."
            ) from None
        except ReturnAuthorizationError as exc:
            self._audit.record("enterReturnItem", str(exc), "rejected")
            raise TransactionError(str(exc)) from None

        note = "" if resellable else " (damaged, not resellable)"
        self._audit.record(
            "enterReturnItem",
            f"{item_id} x{quantity}{note} -> {line_item.get_subtotal()}",
        )
        return LineItemView.from_domain(line_item)

    def get_refund_total(self) -> Money:
        """``getRefundTotal`` - the refund shown to the customer."""
        return self._register.get_refund_total()

    def authorize_refund(self, method: str = "cash") -> Money:
        """``authorizeRefund(method)`` - approve the refund, restock goods."""
        try:
            refund = self._register.authorize_refund(method)
        except (ReturnAuthorizationError, EmptyReturnError,
                EmptySaleError) as exc:
            self._audit.record("authorizeRefund", str(exc), "rejected")
            raise TransactionError(str(exc)) from None
        self._audit.record("authorizeRefund", f"{refund} via {method}")
        return refund

    def end_return(self) -> RefundResult:
        """``endReturn`` - produce the refund receipt and store the return."""
        ret = self._register.current_return
        if ret is None:
            raise TransactionError("No return in progress.")
        try:
            receipt = self._register.end_return()
        except ValueError as exc:
            raise TransactionError(str(exc)) from None

        self._returns.add(ret)
        result = RefundResult(
            return_id=ret.id,
            refund_total=str(ret.refund),
            method=ret.refund_method,
            original_sale_id=ret.original_sale.id if ret.original_sale else "",
            receipt_text=receipt.to_text(),
            item_count=ret.item_count(),
            restocked_units=sum(li.quantity for li in ret.resellable_lines()),
            damaged_units=sum(li.quantity for li in ret.damaged_lines()),
        )
        self._audit.record(
            "endReturn", f"return {ret.id} refunded {ret.refund}"
        )
        self._last_receipt = receipt
        return result

    def cancel_transaction(self) -> None:
        ret = self._register.current_return
        if ret is not None:
            self._audit.record("cancelTransaction", f"return {ret.id}", "void")
        self._register.cancel_current_transaction()


# ---------------------------------------------------------------------------
# Composition root
# ---------------------------------------------------------------------------
@dataclass
class POSApplication:
    """Everything the UI needs, wired together in one place.

    This is the single composition root: the UI receives a fully built
    application and never constructs a gateway, repository or catalog itself.
    """

    register: Register
    process_sale: ProcessSaleController
    handle_returns: HandleReturnsController
    catalog: ProductCatalog
    inventory: InventoryService
    sales: SaleRepository
    returns: ReturnRepository
    audit: AuditLog = field(default_factory=AuditLog)

    def catalog_entries(self) -> list[tuple[str, str, str]]:
        return [(str(s.item_id), s.description, str(s.price))
                for s in self.catalog.all_specifications()]

    def stock_snapshot(self) -> dict[str, int]:
        return self.inventory.on_hand()

    def sales_summary(self) -> dict:
        total = self.sales.total_revenue()
        return {
            "sales": len(self.sales),
            "revenue": str(total) if total is not None else "0.00",
            "returns": len(self.returns),
            "refunded": str(self.returns.total_refunded() or Money.zero()),
        }


def build_application(gateway_kind: str = "simulated",
                      store: Store | None = None,
                      cashier: Cashier | None = None,
                      catalog: ProductCatalog | None = None,
                      inventory: InventoryService | None = None,
                      clock: Callable[[], datetime] | None = None) -> POSApplication:
    """Build a ready-to-run POS application.

    ``gateway_kind`` selects which card-service adapter the **Factory** builds
    (``simulated`` / ``legacy`` / ``soap``), demonstrating that the rest of the
    system is unaffected by the choice.
    """
    store = store or Store("S001", "NextGen Supermarket", "1 Object Street")
    cashier = cashier or Cashier("C001", "A. Cashier")
    catalog = catalog if catalog is not None else build_default_catalog()
    inventory = inventory if inventory is not None else build_default_inventory()

    gateway = PaymentGatewayFactory(kind=gateway_kind).create()
    payment_factory = PaymentFactory(credit_gateway=gateway)

    register = Register(
        register_id="REG-01",
        catalog=catalog,
        inventory=inventory,
        payment_factory=payment_factory,
        store=store,
        cashier=cashier,
    )

    sales = SaleRepository()
    returns = ReturnRepository()
    # One shared audit log: both use-case controllers append to the same
    # trail, so the Store Status tab shows a single chronological history.
    audit = AuditLog()

    return POSApplication(
        register=register,
        process_sale=ProcessSaleController(register, sales, audit, clock),
        handle_returns=HandleReturnsController(register, sales, returns, audit,
                                              clock),
        catalog=catalog,
        inventory=inventory,
        sales=sales,
        returns=returns,
        audit=audit,
    )
