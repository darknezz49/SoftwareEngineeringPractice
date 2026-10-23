"""Adapter pattern: wrap an incompatible external device behind our port.

This module demonstrates the **Adapter (GoF)** pattern in the exact situation
the assignment's Quiz 2 question 15 describes: *"How to resolve incompatible
interfaces, or provide a stable interface to similar components with different
interfaces?"*

The story is the NextGen POS story:

* The POS must work with several third-party card terminals, each with its own
  API that **cannot be changed**.
* We therefore define one stable interface inside our application
  (:class:`~pos.technical.payment_gateway.PaymentGateway`).
* For each foreign device we write a small **adapter** object that converts the
  device's interface into ours.

Three concrete variations are included so the point is unmistakable:

* :class:`LegacyTerminalAdapter` - wraps a stateful, session-based terminal
  that thinks in integer cents.
* :class:`SoapServiceAdapter` - assumes the exception-based error style of a
  remote SOAP/REST service.
* :class:`SimulatedBankAdapter` - wraps the in-process simulator.

:class:`PaymentGatewayFactory` then applies the **Factory** pattern to decide
*which* adapter to build from a configuration string, so the rest of the
application never names a concrete class (**Protected Variations**).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..domain.money import Money
from .payment_gateway import (
    AuthorizationResult,
    PaymentGateway,
    PaymentGatewayError,
    SimulatedBankGateway,
)

__all__ = [
    "ExternalPaymentTerminal",
    "LegacyPaymentTerminal",
    "SoapAuthorizationService",
    "LegacyTerminalAdapter",
    "SoapServiceAdapter",
    "SimulatedBankAdapter",
    "PaymentGatewayFactory",
    "UnknownGatewayError",
]


class UnknownGatewayError(ValueError):
    """Raised by the factory when the requested gateway kind is not known."""


# ---------------------------------------------------------------------------
# The foreign components.  Their interfaces are NOT ours and cannot be changed.
# ---------------------------------------------------------------------------
class ExternalPaymentTerminal(ABC):
    """The 'foreign' interface every legacy terminal exposes."""

    @abstractmethod
    def open_session(self, terminal_id: str) -> str:
        """Open a session; returns a session token."""

    @abstractmethod
    def charge_card(self, session: str, pan: str, amount_in_cents: int) -> dict:
        """Charge the card.  Returns a dict, not an object, and not our types."""

    @abstractmethod
    def close_session(self, session: str) -> None:
        """Close the session."""


class LegacyPaymentTerminal(ExternalPaymentTerminal):
    """A 1990s-style serial/terminal device: session based, integer cents."""

    def __init__(self, terminal_id: str = "TERM-01"):
        self._terminal_id = terminal_id
        self._sessions: set[str] = set()
        self._counter = 0
        self._fail_cards: set[str] = set()

    def fail_card(self, pan: str) -> None:
        self._fail_cards.add(str(pan))

    def open_session(self, terminal_id: str) -> str:
        self._counter += 1
        token = f"{terminal_id}:{self._counter:04d}"
        self._sessions.add(token)
        return token

    def charge_card(self, session: str, pan: str, amount_in_cents: int) -> dict:
        if session not in self._sessions:
            raise RuntimeError("E-SESS: invalid or closed session")
        if str(pan) in self._fail_cards or str(pan).startswith("4000"):
            return {"status": "05", "text": "DECLINED", "ref": ""}
        return {"status": "00", "text": "APPROVED",
                "ref": f"LEGACY-{amount_in_cents:08d}"}

    def close_session(self, session: str) -> None:
        self._sessions.discard(session)


@dataclass
class SoapAuthorizationService:
    """A 'remote' service that signals every problem by raising."""

    endpoint: str = "https://bank.example/soap/Authorize"

    def __post_init__(self):
        self._declined: set[str] = set()

    def decline(self, pan: str) -> None:
        self._declined.add(str(pan))

    def invoke_authorize(self, pan: str, amount_minor: int, currency: str) -> dict:
        if str(pan) in self._declined or str(pan).startswith("4000"):
            raise RuntimeError("SOAP Fault: 51 - Insufficient funds")
        if str(pan).startswith("5000"):
            raise TimeoutError("SOAP endpoint did not respond")
        return {"approved": True,
                "authorizationId": f"SOAP-{amount_minor:06d}",
                "currency": currency}


# ---------------------------------------------------------------------------
# The Adapters.  Each one converts a foreign interface into OUR interface.
# ---------------------------------------------------------------------------
class _AdapterBase(PaymentGateway):
    """Shared behaviour: convert Money to minor units, log the target name."""

    @staticmethod
    def _to_cents(amount: Money) -> int:
        return int((amount.amount * 100).to_integral_value())

    @property
    def name(self) -> str:
        return type(self).__name__


class LegacyTerminalAdapter(_AdapterBase):
    """Adapt :class:`ExternalPaymentTerminal` to :class:`PaymentGateway`."""

    def __init__(self, terminal: ExternalPaymentTerminal,
                 terminal_id: str = "TERM-01"):
        self._terminal = terminal
        self._terminal_id = terminal_id

    @property
    def name(self) -> str:
        return f"LegacyTerminalAdapter({self._terminal_id})"

    def authorize(self, card_number: str, amount: Money) -> AuthorizationResult:
        # 1. our (stateless) call  ->  the device's required session
        session = self._terminal.open_session(self._terminal_id)
        try:
            # 2. our Money object  ->  the device's integer cents
            response = self._terminal.charge_card(
                session, str(card_number), self._to_cents(amount)
            )
        except Exception as exc:                      # device blew up
            raise PaymentGatewayError(
                f"legacy terminal error: {exc}"
            ) from exc
        finally:
            # 3. always close the session - the device is stateful, we are not
            self._terminal.close_session(session)

        # 4. the device's dict/status codes  ->  our result object
        if response.get("status") == "00":
            return AuthorizationResult(
                approved=True,
                authorization_code=response.get("ref", ""),
                message=response.get("text", "APPROVED"),
            )
        return AuthorizationResult(
            approved=False,
            message=f"{response.get('text', 'DECLINED')} "
                    f"(terminal status {response.get('status')})",
        )


class SoapServiceAdapter(_AdapterBase):
    """Adapt the exception-throwing SOAP service to our result-object port.

    The essential Adapter job in the error dimension: the foreign service
    reports failure by *throwing*, our interface reports failure by returning a
    value (or by raising our own well-defined exception type).
    """

    def __init__(self, service: SoapAuthorizationService, currency: str = "CNY"):
        self._service = service
        self._currency = currency

    @property
    def name(self) -> str:
        return f"SoapServiceAdapter({self._service.endpoint})"

    def authorize(self, card_number: str, amount: Money) -> AuthorizationResult:
        try:
            response = self._service.invoke_authorize(
                pan=str(card_number),
                amount_minor=self._to_cents(amount),
                currency=self._currency,
            )
        except TimeoutError as exc:
            # A transport failure is a *different* fault from a decline and
            # must not be mistaken for one.
            raise PaymentGatewayError(f"authorisation service timeout: {exc}") from exc
        except Exception as exc:
            # A SOAP fault here means a decline in this service's vocabulary.
            return AuthorizationResult(approved=False, message=str(exc))

        return AuthorizationResult(
            approved=bool(response.get("approved")),
            authorization_code=str(response.get("authorizationId", "")),
            message="APPROVED" if response.get("approved") else "DECLINED",
        )


class SimulatedBankAdapter(_AdapterBase):
    """Adapt the in-process :class:`SimulatedBankGateway` (already our port)."""

    def __init__(self, bank: SimulatedBankGateway | None = None):
        self._bank = bank or SimulatedBankGateway()

    @property
    def bank(self) -> SimulatedBankGateway:
        return self._bank

    @property
    def name(self) -> str:
        return f"SimulatedBankAdapter({self._bank.name})"

    def authorize(self, card_number: str, amount: Money) -> AuthorizationResult:
        return self._bank.authorize(str(card_number), amount)


# ---------------------------------------------------------------------------
# The Factory: decide which adapter to build, from data.
# ---------------------------------------------------------------------------
class PaymentGatewayFactory:
    """**Factory** pattern for the family of gateway adapters.

    The advantages the book lists for Factory objects are exactly what happens
    here:

    * the responsibility of (non-trivial) creation sits in one cohesive helper
      object rather than being smeared over the domain;
    * the creation logic is hidden from clients;
    * the concrete class is chosen from *data* (``kind``), so introducing a new
      terminal means adding one branch (or one registry entry) and **no change
      to any caller** - Protected Variations.
    """

    DEFAULT_KIND = "simulated"

    def __init__(self, kind: str = DEFAULT_KIND, **options):
        self._kind = str(kind).strip().lower()
        self._options = options

    @property
    def kind(self) -> str:
        return self._kind

    def create(self, kind: str | None = None, **options) -> PaymentGateway:
        """Create and return a :class:`PaymentGateway` adapter."""
        chosen = str(kind or self._kind).strip().lower()
        opts = {**self._options, **options}

        if chosen == "simulated":
            return SimulatedBankAdapter(
                opts.get("bank") or SimulatedBankGateway(
                    name=opts.get("name", "SimulatedBank"))
            )

        if chosen == "legacy":
            return LegacyTerminalAdapter(
                opts.get("terminal") or LegacyPaymentTerminal(),
                terminal_id=opts.get("terminal_id", "TERM-01"),
            )

        if chosen in ("soap", "rest"):
            return SoapServiceAdapter(
                opts.get("service") or SoapAuthorizationService(),
                currency=opts.get("currency", "CNY"),
            )

        raise UnknownGatewayError(f"unknown gateway kind: {chosen!r}")

    @classmethod
    def available_kinds(cls) -> tuple[str, ...]:
        return ("simulated", "legacy", "soap")
