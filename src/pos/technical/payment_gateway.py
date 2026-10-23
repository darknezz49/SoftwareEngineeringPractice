"""Payment gateway ports and SimulatedBankGateway implementation.

The domain layer depends only on the abstract :class:`PaymentGateway` and the
:class:`AuthorizationResult` it returns.  Concrete bank protocols live here, in
the Technical Services layer, and are reached through an Adapter
(see :mod:`pos.technical.payment_adapters`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..domain.money import Money

__all__ = [
    "AuthorizationResult",
    "PaymentGateway",
    "RefundGateway",
    "gateway_error",
]


@dataclass(frozen=True)
class AuthorizationResult:
    """Outcome of an authorisation attempt against an external service."""

    approved: bool
    authorization_code: str = ""
    message: str = ""


class PaymentGatewayError(RuntimeError):
    """Raised when the external service cannot be reached at all."""


# Public alias used by callers that prefer a name ending in "Error".
gateway_error = PaymentGatewayError


class PaymentGateway(ABC):
    """Port: authorise a card payment for an amount."""

    @abstractmethod
    def authorize(self, card_number: str, amount: Money) -> AuthorizationResult:
        """Return an :class:`AuthorizationResult` for ``card_number``."""

    @property
    def name(self) -> str:
        return type(self).__name__


class RefundGateway(ABC):
    """Port: send a refund back to the card that paid."""

    @abstractmethod
    def refund(self, card_number: str, amount: Money) -> AuthorizationResult:
        """Return an :class:`AuthorizationResult` for the refund."""


class SimulatedBankGateway(PaymentGateway, RefundGateway):
    """A stand-in for a real bank/PSP, used by the demo and by the tests.

    Deliberately behaves like a *foreign* system:

    * it speaks in integer **cents**, not in ``Money``;
    * it returns its own response object with its own field names
      (``approved``, ``code``, ``reason``) - hence the need for an Adapter;
    * it can be told to decline a card, so the "reimbursement transaction
      rejected" alternate scenario can be demonstrated.
    """

    DECLINE_PREFIX = "4000"          # any card starting 4000 is declined
    FLAKY_PREFIX = "4444"            # any card starting 4444 times out

    def __init__(self, name: str = "SimulatedBank"):
        self._name = name
        self._authorizations: dict[str, Money] = {}
        self._sequence = 0
        self._declines: set[str] = set()
        self._offline = False

    # -- test/demo controls ---------------------------------------------
    @property
    def name(self) -> str:
        return self._name

    def decline(self, card_number: str) -> None:
        self._declines.add(str(card_number))

    def go_offline(self, offline: bool = True) -> None:
        self._offline = offline

    # -- gateway port ----------------------------------------------------
    def authorize(self, card_number: str, amount: Money) -> AuthorizationResult:
        card = str(card_number)

        if self._offline or card.startswith(self.FLAKY_PREFIX):
            raise PaymentGatewayError(
                f"{self._name} is unreachable (network timeout)"
            )

        if card in self._declines or card.startswith(self.DECLINE_PREFIX):
            return AuthorizationResult(
                approved=False,
                authorization_code="",
                message="CARD DECLINED BY ISSUER",
            )

        self._sequence += 1
        code = f"AUTH{self._sequence:06d}"
        self._authorizations[code] = amount
        return AuthorizationResult(
            approved=True,
            authorization_code=code,
            message="APPROVED",
        )

    def refund(self, card_number: str, amount: Money) -> AuthorizationResult:
        card = str(card_number)
        if self._offline or card.startswith(self.FLAKY_PREFIX):
            raise PaymentGatewayError(
                f"{self._name} is unreachable (network timeout)"
            )
        if card.startswith(self.DECLINE_PREFIX):
            return AuthorizationResult(
                approved=False,
                message="REFUND REJECTED - please reimburse in cash",
            )
        self._sequence += 1
        code = f"REF{self._sequence:06d}"
        self._authorizations[code] = -amount
        return AuthorizationResult(True, code, "REFUNDED")

    # -- introspection ----------------------------------------------------
    def get_authorized_amount(self, code: str) -> Money | None:
        return self._authorizations.get(code)

    def authorization_count(self) -> int:
        return len(self._authorizations)
