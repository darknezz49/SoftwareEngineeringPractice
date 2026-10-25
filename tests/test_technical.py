"""Tests for the Technical Services layer.

The adapter tests are the interesting ones: they prove that three foreign
components with completely different interfaces are all usable through the one
stable interface our domain depends on.
"""
from __future__ import annotations

import pytest

from pos.domain import Money
from pos.technical import (
    LegacyPaymentTerminal,
    LegacyTerminalAdapter,
    PaymentGateway,
    PaymentGatewayError,
    PaymentGatewayFactory,
    SimulatedBankAdapter,
    SimulatedBankGateway,
    SoapAuthorizationService,
    SoapServiceAdapter,
    UnknownGatewayError,
)
from pos.technical.store_data import (
    build_default_catalog,
    build_default_inventory,
)


# ---------------------------------------------------------------------------
# The simulated bank
# ---------------------------------------------------------------------------
class TestSimulatedBankGateway:
    def test_approves_a_good_card(self):
        result = SimulatedBankGateway().authorize("4111111111111111",
                                                  Money("9.00"))
        assert result.approved
        assert result.authorization_code.startswith("AUTH")

    def test_declines_the_4000_prefix(self):
        result = SimulatedBankGateway().authorize("4000000000000002",
                                                  Money("9.00"))
        assert not result.approved
        assert "DECLINED" in result.message

    def test_offline_raises(self):
        gateway = SimulatedBankGateway()
        gateway.go_offline()
        with pytest.raises(PaymentGatewayError):
            gateway.authorize("4111111111111111", Money("9.00"))


# ---------------------------------------------------------------------------
# Adapter pattern - all three adapters satisfy the same port
# ---------------------------------------------------------------------------
class TestAdaptersSatisfyThePort:
    @pytest.mark.parametrize("adapter", [
        LegacyTerminalAdapter(LegacyPaymentTerminal()),
        SoapServiceAdapter(SoapAuthorizationService()),
        SimulatedBankAdapter(),
    ])
    def test_adapter_is_a_payment_gateway(self, adapter):
        assert isinstance(adapter, PaymentGateway)

    @pytest.mark.parametrize("adapter", [
        LegacyTerminalAdapter(LegacyPaymentTerminal()),
        SoapServiceAdapter(SoapAuthorizationService()),
        SimulatedBankAdapter(),
    ])
    def test_adapter_approves_a_good_card(self, adapter):
        result = adapter.authorize("4111111111111111", Money("12.34"))
        assert result.approved is True
        assert result.authorization_code

    @pytest.mark.parametrize("adapter", [
        LegacyTerminalAdapter(LegacyPaymentTerminal()),
        SoapServiceAdapter(SoapAuthorizationService()),
        SimulatedBankAdapter(),
    ])
    def test_adapter_declines_a_bad_card(self, adapter):
        result = adapter.authorize("4000000000000002", Money("12.34"))
        assert result.approved is False


class TestLegacyTerminalAdapter:
    def test_money_is_converted_to_integer_cents(self):
        """The device speaks cents; we speak Money - the adapter translates."""
        terminal = LegacyPaymentTerminal()
        adapter = LegacyTerminalAdapter(terminal)
        result = adapter.authorize("4111111111111111", Money("12.34"))
        assert result.authorization_code == "LEGACY-00001234"

    def test_session_is_opened_and_closed_around_each_call(self):
        terminal = LegacyPaymentTerminal()
        adapter = LegacyTerminalAdapter(terminal)
        adapter.authorize("4111111111111111", Money("1.00"))
        # no session may leak: the device is stateful, we must not be
        assert terminal._sessions == set()

    def test_device_failure_becomes_our_exception(self):
        class Exploding(LegacyPaymentTerminal):
            def charge_card(self, session, pan, amount_in_cents):
                raise RuntimeError("E-COM: serial port dead")

        adapter = LegacyTerminalAdapter(Exploding())
        with pytest.raises(PaymentGatewayError, match="legacy terminal error"):
            adapter.authorize("4111111111111111", Money("1.00"))


class TestSoapServiceAdapter:
    def test_soap_fault_becomes_a_decline_not_an_exception(self):
        """Adapter job: reconcile the two error-reporting styles."""
        adapter = SoapServiceAdapter(SoapAuthorizationService())
        result = adapter.authorize("4000000000000002", Money("5.00"))
        assert result.approved is False
        assert "Insufficient funds" in result.message

    def test_transport_timeout_becomes_our_exception(self):
        adapter = SoapServiceAdapter(SoapAuthorizationService())
        with pytest.raises(PaymentGatewayError, match="timeout"):
            adapter.authorize("5000000000000000", Money("5.00"))


# ---------------------------------------------------------------------------
# Factory pattern
# ---------------------------------------------------------------------------
class TestPaymentGatewayFactory:
    @pytest.mark.parametrize("kind,expected", [
        ("simulated", SimulatedBankAdapter),
        ("legacy", LegacyTerminalAdapter),
        ("soap", SoapServiceAdapter),
        ("LEGACY", LegacyTerminalAdapter),       # case-insensitive
    ])
    def test_factory_builds_the_right_adapter(self, kind, expected):
        gateway = PaymentGatewayFactory().create(kind)
        assert isinstance(gateway, expected)

    def test_every_kind_produces_a_usable_gateway(self):
        """The caller never needs to know which concrete class it got."""
        for kind in PaymentGatewayFactory.available_kinds():
            gateway = PaymentGatewayFactory().create(kind)
            assert gateway.authorize("4111111111111111",
                                     Money("1.00")).approved

    def test_unknown_kind_raises(self):
        with pytest.raises(UnknownGatewayError):
            PaymentGatewayFactory().create("quantum-teleport")

    def test_factory_can_be_configured_up_front(self):
        factory = PaymentGatewayFactory(kind="legacy")
        assert isinstance(factory.create(), LegacyTerminalAdapter)


# ---------------------------------------------------------------------------
# Seed data consistency
# ---------------------------------------------------------------------------
class TestSeedData:
    def test_catalog_and_inventory_cover_the_same_items(self):
        catalog = build_default_catalog()
        inventory = build_default_inventory()
        catalog_ids = {str(s.item_id) for s in catalog.all_specifications()}
        assert catalog_ids == set(inventory.on_hand())

    def test_default_shop_has_twelve_products(self):
        assert len(build_default_catalog()) == 12

    def test_every_price_is_positive(self):
        for spec in build_default_catalog().all_specifications():
            assert spec.price > Money.zero()


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------
class TestRepositories:
    def test_sale_repository_finds_by_item(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 1)
        sale.make_payment("cash")
        found = small_app.sales.find_by_item("1001")
        assert len(found) == 1
        assert small_app.sales.find_by_item("1005") == []

    def test_return_repository_accumulates_refunds(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 2)
        sale.make_payment("cash")
        sale_id = small_app.sales.all_sales()[-1].id

        returns = small_app.handle_returns
        returns.make_new_return(sale_id)
        returns.enter_return_item("1001", 1)
        returns.authorize_refund("cash")
        returns.end_return()

        assert len(small_app.returns) == 1
        assert small_app.returns.total_refunded() == Money("4.50")


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
class TestAuditLog:
    def test_system_operations_are_recorded(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 1)
        sale.make_payment("cash")
        operations = [e.operation for e in small_app.audit.entries]
        assert "makeNewSale" in operations
        assert "enterItem" in operations
        assert "makePayment" in operations

    def test_failures_are_recorded_with_an_error_outcome(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        with pytest.raises(Exception):
            sale.enter_item("9999", 1)
        assert any(e.outcome == "error" for e in small_app.audit.entries)
