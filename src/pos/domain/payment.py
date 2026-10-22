"""Payments.

A payment is polymorphic: ``CashPayment`` settles immediately, while
``CreditPayment`` delegates authorisation to an external
:class:`~pos.technical.payment_gateway.PaymentGateway` through an *Adapter*, so
the domain stays independent of whatever protocol the bank speaks.

``PaymentFactory`` is the **Factory** (Simple/Concrete Factory) pattern: a Pure
Fabrication object that owns the responsibility and the logic of creating
payment objects, keeping creation out of the domain classes (High Cohesion,
Protected Variations).
"""
from __future__ import annotations

from decimal import Decimal

from .money import Money

__all__ = [
    "Payment",
    "CashPayment",
    "CreditPayment",
    "PaymentFactory",
    "PaymentAuthorizationError",
    "InsufficientTenderError",
    "UnsupportedPaymentError",
]


class PaymentAuthorizationError(RuntimeError):
    """Raised when an external authorisation service declines a payment."""


class InsufficientTenderError(ValueError):
    """Raised when the cash handed over is less than the amount due."""

    def __init__(self, due: Money, tendered: Money):
        super().__init__(f"tendered {tendered} is less than amount due {due}")
        self.due = due
        self.tendered = tendered


class UnsupportedPaymentError(ValueError):
    """Raised by the factory for an unknown payment type."""


class Payment:
    """Abstract payment of a single amount."""

    kind = "Payment"

    def __init__(self, amount: Money | str | int):
        amount = amount if isinstance(amount, Money) else Money(amount)
        if amount.is_negative():
            raise ValueError("payment amount must not be negative")
        self._amount = amount
        self._authorized = False
        self._reference = ""

    @property
    def amount(self) -> Money:
        return self._amount

    @property
    def authorized(self) -> bool:
        return self._authorized

    @property
    def reference(self) -> str:
        """An external reference (authorisation code, change due, ...)."""
        return self._reference

    def authorize(self) -> bool:
        """Validate and record the payment.  Template method style hook."""
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.kind} {self._amount}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self._amount)!r})"


class CashPayment(Payment):
    """Cash tendered by the customer; may produce change."""

    kind = "Cash"

    def __init__(self, amount: Money | str | int,
                 tendered: Money | str | int | None = None):
        super().__init__(amount)
        if tendered is None:
            self._tendered = self._amount
        else:
            self._tendered = tendered if isinstance(tendered, Money) \
                else Money(tendered)
        self._change = Money.zero()

    @property
    def tendered(self) -> Money:
        return self._tendered

    @property
    def change(self) -> Money:
        return self._change

    def authorize(self) -> bool:
        if self._tendered < self._amount:
            raise InsufficientTenderError(self._amount, self._tendered)
        self._change = self._tendered - self._amount
        self._authorized = True
        self._reference = f"CHANGE {self._change}"
        return True


class CreditPayment(Payment):
    """A card payment authorised by an external service through an adapter.

    Information Expert is respected by *not* putting bank-protocol logic here:
    the payment object knows the card data, and the injected
    ``gateway`` (an Adapter) knows how to talk to the bank.
    """

    kind = "Credit"

    def __init__(self, amount: Money, card_number: str, gateway):
        super().__init__(amount)
        digits = "".join(ch for ch in str(card_number) if ch.isdigit())
        if len(digits) < 12:
            raise ValueError("card number must have at least 12 digits")
        self._card_number = digits
        self._gateway = gateway
        self._masked = "*" * (len(digits) - 4) + digits[-4:]

    @property
    def masked_card(self) -> str:
        return self._masked

    @property
    def gateway(self):
        return self._gateway

    def authorize(self) -> bool:
        result = self._gateway.authorize(
            card_number=self._card_number,
            amount=self._amount,
        )
        if not result.approved:
            raise PaymentAuthorizationError(
                f"card declined: {result.message or 'no reason given'}"
            )
        self._authorized = True
        self._reference = result.authorization_code
        return True

    def __str__(self) -> str:
        return f"{self.kind} {self._amount} ({self._masked})"


class PaymentFactory:
    """Factory: creates ``Payment`` objects, hiding creation logic.

    Responsibilities (the *Factory* pattern's stated advantages):

    * separate the responsibility of creation into a cohesive helper object;
    * hide the (potentially complex) creation logic;
    * decide the concrete class from data, so the caller never names it
      (this is where **Protected Variations** on the payment implementation
      is achieved).
    """

    def __init__(self, credit_gateway=None):
        self._credit_gateway = credit_gateway

    def set_credit_gateway(self, gateway) -> None:
        self._credit_gateway = gateway

    def create(self, kind: str, amount: Money | str | int,
               **kwargs) -> Payment:
        """Create a payment of ``kind`` for ``amount``.

        ``kind`` is one of ``cash`` / ``credit`` (case-insensitive), or the
        fully-qualified name of a ``Payment`` subclass.
        """
        normalised = str(kind).strip().lower()

        if normalised == "cash":
            return CashPayment(amount, tendered=kwargs.get("tendered"))

        if normalised == "credit":
            gateway = kwargs.get("gateway") or self._credit_gateway
            if gateway is None:
                raise UnsupportedPaymentError(
                    "no credit gateway configured for credit payments"
                )
            return CreditPayment(amount, kwargs.get("card_number", ""), gateway)

        raise UnsupportedPaymentError(f"unsupported payment type: {kind}")

    @staticmethod
    def cash(amount: Money | str | int,
             tendered: Money | str | int | None = None) -> CashPayment:
        return CashPayment(amount, tendered=tendered)
