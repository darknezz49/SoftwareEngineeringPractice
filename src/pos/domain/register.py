"""The ``Register`` - the facade controller of the POS system.

In the book the ``Register`` is both a line item of the conceptual domain
(a "where is the transaction recorded?" class) and, in the design model, the
**facade controller** for the Process Sale system operations.  It is the
**Creator** of ``Sale`` objects (GRASP *Creator*: the register records sales).

Keeping the controller inside the domain keeps the application layer thin and
preserves Model-View Separation: the UI talks to a ``Register``, never to
database or network code.
"""
from __future__ import annotations

from .catalog import ProductCatalog
from .inventory import InventoryService
from .money import Money
from .payment import Payment, PaymentFactory
from .receipt import Receipt, ReceiptLine
from .returns import ReturnTransaction
from .sale import Sale

__all__ = ["Register", "UnknownItemError"]

# Re-exported for callers that only import the register.
from .inventory import UnknownItemError  # noqa: E402


class Register:
    """The point-of-sale terminal: system operations enter here.

    Application-layer controllers (``ProcessSaleController``,
    ``HandleReturnsController``) send messages to this object; it owns the
    in-memory working state (the current ``Sale`` / ``ReturnTransaction``).
    """

    def __init__(self, register_id: str, catalog: ProductCatalog,
                 inventory: InventoryService, payment_factory: PaymentFactory,
                 store=None, cashier=None):
        self._id = str(register_id).strip()
        if not self._id:
            raise ValueError("register id is required")
        self._catalog = catalog
        self._inventory = inventory
        self._payment_factory = payment_factory
        self._store = store
        self._cashier = cashier
        self._current_sale: Sale | None = None
        self._current_return: ReturnTransaction | None = None

    # -- collaborators ----------------------------------------------------
    @property
    def id(self) -> str:
        return self._id

    @property
    def catalog(self) -> ProductCatalog:
        return self._catalog

    @property
    def inventory(self) -> InventoryService:
        return self._inventory

    @property
    def payment_factory(self) -> PaymentFactory:
        return self._payment_factory

    @property
    def store(self):
        return self._store

    @property
    def cashier(self):
        return self._cashier

    def set_cashier(self, cashier) -> None:
        self._cashier = cashier

    # -- current transaction ----------------------------------------------
    @property
    def current_sale(self) -> Sale | None:
        return self._current_sale

    @property
    def current_return(self) -> ReturnTransaction | None:
        return self._current_return

    # -- Process Sale system operations ------------------------------------
    def make_new_sale(self, when=None) -> Sale:
        """System operation ``makeNewSale``.

        Creator: the ``Register`` creates the ``Sale`` it records.

        ``when`` lets the caller supply the transaction timestamp; it defaults
        to "now" and exists so that receipts in tests and transcripts are
        deterministic.
        """
        self._current_sale = Sale(cashier=self._cashier, store=self._store,
                                  when=when)
        return self._current_sale

    def enter_item(self, item_id: str, quantity: int = 1):
        """System operation ``enterItem``.

        Returns the created/extended :class:`SalesLineItem`.  Raises
        ``UnknownItemError`` if the id is not in the catalog, and
        ``InsufficientStockError`` if the shelf cannot cover the quantity.
        """
        sale = self._require_sale()
        specification = self._catalog.get_specification(item_id)
        if specification is None:
            raise UnknownItemError(str(item_id))

        existing = sale.find_line_item(item_id)
        already = existing.quantity if existing else 0
        if not self._inventory.is_available(item_id, already + quantity):
            from .inventory import InsufficientStockError
            available = self._inventory.get_level(item_id)
            raise InsufficientStockError(specification.item_id,
                                         already + quantity, available)

        if existing is not None:
            existing.increase_quantity(quantity)
            return existing
        return sale.make_line_item(specification, quantity)

    def remove_item(self, item_id: str) -> bool:
        """System operation ``removeItem`` - take a line off the sale."""
        return self._require_sale().remove_line_item(item_id)

    def get_total(self) -> Money:
        """System operation ``getTotal`` - the running total on the display."""
        return self._require_sale().get_total()

    def make_payment(self, kind: str, **kwargs) -> Payment:
        """System operation ``makePayment``.

        Validates and records the payment, **updates inventory** for every line
        of the sale (as the use case requires), and closes the sale.
        """
        sale = self._require_sale()
        payment = self._payment_factory.create(kind, sale.get_total(), **kwargs)
        sale.make_payment(payment)

        # "The system updates inventory."  Done only after the payment is
        # authorised, so an abandoned sale never decrements stock.
        for line_item in sale.line_items:
            self._inventory.remove(line_item.item_id, line_item.quantity)
        return payment

    def end_sale(self) -> Receipt:
        """System operation ``endSale`` - produce the customer's receipt."""
        sale = self._require_sale()
        if not sale.is_complete:
            raise ValueError("cannot produce a receipt for an unpaid sale")
        receipt = self._build_receipt(sale)
        self._current_sale = None
        return receipt

    def _build_receipt(self, sale: Sale) -> Receipt:
        lines = [
            ReceiptLine(li.description, li.quantity, li.unit_price,
                        li.get_subtotal())
            for li in sale.line_items
        ]
        extra = [f"{type(p).kind + ' tender':<32}{str(p.amount):>14}"
                 for p in sale.payments]
        change = sale.get_change_due()
        if not change.is_zero():
            extra.append(f"{'Change':<32}{str(change):>14}")
        return Receipt(
            title="SALES RECEIPT",
            store_name=getattr(self._store, "name", "NextGen POS Store"),
            transaction_id=sale.id,
            when=sale.time,
            lines=lines,
            total=sale.get_total(),
            cashier_name=getattr(self._cashier, "name", ""),
            extra=extra,
        )

    # -- Handle Returns system operations ----------------------------------
    def make_new_return(self, original_sale: Sale | None = None,
                        reason: str = "", when=None) -> ReturnTransaction:
        """System operation ``makeNewReturn`` (Creator)."""
        self._current_return = ReturnTransaction(
            original_sale=original_sale,
            cashier=self._cashier,
            store=self._store,
            reason=reason,
            when=when,
        )
        return self._current_return

    def enter_return_item(self, item_id: str, quantity: int = 1,
                          resellable: bool = True):
        """System operation ``enterReturnItem``.

        Mirrors ``enterItem``.  When the original sale is known the returned
        quantity is checked against what was actually bought.
        """
        ret = self._require_return()
        specification = self._catalog.get_specification(item_id)
        if specification is None:
            raise UnknownItemError(str(item_id))

        if ret.original_sale is not None:
            sold_line = ret.original_sale.find_line_item(item_id)
            sold = sold_line.quantity if sold_line else 0
            already = 0
            existing = ret.find_line_item(item_id)
            if existing is not None:
                already = existing.quantity
            if sold == 0:
                from .returns import ReturnAuthorizationError
                raise ReturnAuthorizationError(
                    f"{item_id} was not part of sale "
                    f"{ret.original_sale.id}"
                )
            if already + quantity > sold:
                from .returns import ReturnAuthorizationError
                raise ReturnAuthorizationError(
                    f"cannot return {already + quantity} of {item_id}: "
                    f"only {sold} were sold on {ret.original_sale.id}"
                )

        existing = ret.find_line_item(item_id)
        if existing is not None:
            existing.increase_quantity(quantity)
            if resellable:
                existing.set_resellable(True)
            return existing
        return ret.make_line_item(specification, quantity,
                                  resellable=resellable)

    def get_refund_total(self) -> Money:
        return self._require_return().get_refund_total()

    def authorize_refund(self, method: str = "cash") -> Money:
        """System operation ``authorizeRefund``.

        Declares the refund, **updates inventory** for every resellable line
        (damaged goods are not put back on the shelf), and closes the return.
        """
        ret = self._require_return()
        refund = ret.authorize_refund(method)
        for line_item in ret.resellable_lines():
            self._inventory.restock(line_item.item_id, line_item.quantity)
        return refund

    def end_return(self) -> Receipt:
        """System operation ``endReturn`` - produce the refund receipt."""
        ret = self._require_return()
        if ret.state.value != "refunded":
            raise ValueError("cannot produce a receipt for an unauthorised return")
        lines = [
            ReceiptLine(li.description, li.quantity, li.unit_price,
                        li.get_subtotal())
            for li in ret.line_items
        ]
        extra = [f"{'Refund via':<32}{ret.refund_method:>14}",
                 f"{'Original sale':<32}"
                 f"{(ret.original_sale.id if ret.original_sale else 'n/a'):>14}"]
        if ret.damaged_lines():
            extra.append(
                f"{'Not resellable':<32}{len(ret.damaged_lines()):>14}"
            )
        receipt = Receipt(
            title="REFUND RECEIPT",
            store_name=getattr(self._store, "name", "NextGen POS Store"),
            transaction_id=ret.id,
            when=ret.time,
            lines=lines,
            total=ret.refund,
            cashier_name=getattr(self._cashier, "name", ""),
            extra=extra,
        )
        self._current_return = None
        return receipt

    def cancel_current_transaction(self) -> None:
        """System operation ``cancelTransaction``."""
        if self._current_sale is not None:
            self._current_sale.void()
            self._current_sale = None
        if self._current_return is not None:
            self._current_return.cancel()
            self._current_return = None

    # -- helpers -----------------------------------------------------------
    def _require_sale(self) -> Sale:
        if self._current_sale is None:
            raise ValueError("no sale in progress; call makeNewSale first")
        return self._current_sale

    def _require_return(self) -> ReturnTransaction:
        if self._current_return is None:
            raise ValueError("no return in progress; call makeNewReturn first")
        return self._current_return

    def __str__(self) -> str:
        return f"Register {self._id}"

    def __repr__(self) -> str:
        return f"Register({self._id!r})"
