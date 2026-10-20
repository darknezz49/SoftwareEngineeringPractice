"""Technical Services layer.

General-purpose, application-independent-ish services that support the domain:
payment gateways and their adapters, persistence repositories, store data and
the audit log.  Nothing in this layer knows about the UI.
"""
from .payment_gateway import (
    AuthorizationResult,
    PaymentGateway,
    PaymentGatewayError,
    RefundGateway,
    SimulatedBankGateway,
    gateway_error,
)
from .payment_adapters import (
    LegacyPaymentTerminal,
    LegacyTerminalAdapter,
    PaymentGatewayFactory,
    SimulatedBankAdapter,
    SoapAuthorizationService,
    SoapServiceAdapter,
    UnknownGatewayError,
)
from .repositories import ReturnRepository, SaleRepository
from .store_data import (
    AuditEntry,
    AuditLog,
    build_default_catalog,
    build_default_inventory,
    describe_products,
    load_products,
    seed_store,
)

__all__ = [
    "AuditEntry",
    "AuditLog",
    "AuthorizationResult",
    "LegacyPaymentTerminal",
    "LegacyTerminalAdapter",
    "PaymentGateway",
    "PaymentGatewayError",
    "PaymentGatewayFactory",
    "RefundGateway",
    "ReturnRepository",
    "SaleRepository",
    "SimulatedBankAdapter",
    "SimulatedBankGateway",
    "SoapAuthorizationService",
    "SoapServiceAdapter",
    "UnknownGatewayError",
    "build_default_catalog",
    "build_default_inventory",
    "describe_products",
    "gateway_error",
    "load_products",
    "seed_store",
]
