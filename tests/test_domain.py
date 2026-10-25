"""Unit tests for the domain model: Money, Sale, Returns, Payment."""
from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import (
    CashPayment,
    Money,
    PaymentFactory,
    ProductCatalog,
    ProductSpecification,
    ReturnTransaction,
    Sale,
    SaleState,
    SalesLineItem,
)
from pos.domain.payment import InsufficientTenderError, PaymentAuthorizationError
from pos.domain.sale import EmptySaleError, SaleStateError
from pos.technical import SimulatedBankGateway


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
class TestMoney:
    def test_no_binary_float_is_accepted(self):
        """Money must never be built from a float - that is the whole point."""
        with pytest.raises(TypeError):
            Money(4.50)

    def test_addition_and_subtraction_are_exact(self):
        assert Money("0.10") + Money("0.20") == Money("0.30")
        assert Money("10.00") - Money("3.33") == Money("6.67")

    def test_multiplication_by_quantity(self):
        assert Money("4.50") * 3 == Money("13.50")

    def test_half_up_rounding_to_cents(self):
        # 1 / 3 of a yuan must round, not truncate
        assert Money(Decimal("1") / 3) == Money("0.33")
        assert Money(Decimal("2") / 3) == Money("0.67")

    def test_comparison_and_negation(self):
        assert Money("4.50") < Money("4.51")
        assert Money("4.50") >= Money("4.50")
        assert -Money("2.00") == Money("-2.00")
        assert abs(Money("-2.00")) == Money("2.00")

    def test_zero_and_negative_predicates(self):
        assert Money.zero().is_zero()
        assert Money("-1.00").is_negative()

    def test_str_has_two_decimals(self):
        assert str(Money("4.5")) == "4.50"
        assert str(Money("0")) == "0.00"


# ---------------------------------------------------------------------------
# Line items and Sale totals (Information Expert)
# ---------------------------------------------------------------------------
class TestSaleTotals:
    def test_line_item_subtotal_is_quantity_times_price(self, catalog):
        spec = catalog.get_specification("1001")
        line = SalesLineItem(spec, 3)
        assert line.get_subtotal() == Money("13.50")

    def test_sale_total_sums_its_line_items(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 2)   #  9.00
        sale.make_line_item(catalog.get_specification("1005"), 1)   #  8.80
        assert sale.get_total() == Money("17.80")

    def test_empty_sale_totals_zero(self):
        assert Sale().get_total() == Money.zero()

    def test_quantity_must_be_positive(self, catalog):
        with pytest.raises(ValueError):
            SalesLineItem(catalog.get_specification("1001"), 0)


# ---------------------------------------------------------------------------
# Sale lifecycle
# ---------------------------------------------------------------------------
class TestSaleLifecycle:
    def test_new_sale_is_open_and_incomplete(self):
        assert Sale().state is SaleState.OPEN
        assert not Sale().is_complete

    def test_paying_an_empty_sale_is_rejected(self):
        sale = Sale()
        with pytest.raises(EmptySaleError):
            sale.make_payment(CashPayment(Money("0.00")))

    def test_successful_cash_payment_completes_the_sale(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 2)
        payment = sale.make_payment(CashPayment(Money("9.00"), Money("10.00")))
        assert sale.is_complete
        assert payment.authorized
        assert sale.get_change_due() == Money("1.00")

    def test_underpayment_is_rejected(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 2)
        with pytest.raises(ValueError):
            sale.make_payment(CashPayment(Money("5.00")))

    def test_cash_tendered_below_total_raises(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 2)
        with pytest.raises(InsufficientTenderError):
            sale.make_payment(CashPayment(Money("9.00"), Money("8.00")))

    def test_cannot_add_items_after_payment(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 1)
        sale.make_payment(CashPayment(Money("4.50")))
        with pytest.raises(SaleStateError):
            sale.make_line_item(catalog.get_specification("1002"), 1)

    def test_cannot_pay_twice(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 1)
        sale.make_payment(CashPayment(Money("4.50")))
        with pytest.raises(SaleStateError):
            sale.make_payment(CashPayment(Money("4.50")))

    def test_find_and_remove_line_item(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 1)
        sale.make_line_item(catalog.get_specification("1002"), 1)
        assert sale.find_line_item("1002").quantity == 1
        assert sale.remove_line_item("1002") is True
        assert sale.find_line_item("1002") is None
        assert len(sale.line_items) == 1

    def test_void_refuses_after_payment(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 1)
        sale.make_payment(CashPayment(Money("4.50")))
        with pytest.raises(SaleStateError):
            sale.void()

    def test_item_count_sums_quantities(self, catalog):
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 2)
        sale.make_line_item(catalog.get_specification("1002"), 3)
        assert sale.item_count() == 5


# ---------------------------------------------------------------------------
# Payment factory and adapters
# ---------------------------------------------------------------------------
class TestPaymentFactory:
    def test_factory_creates_cash(self):
        payment = PaymentFactory().create("cash", Money("9.00"))
        assert isinstance(payment, CashPayment)
        assert payment.kind == "Cash"

    def test_factory_kind_is_case_insensitive(self):
        payment = PaymentFactory().create("CASH", Money("9.00"))
        assert isinstance(payment, CashPayment)

    def test_factory_needs_a_gateway_for_credit(self):
        from pos.domain.payment import UnsupportedPaymentError
        with pytest.raises(UnsupportedPaymentError):
            PaymentFactory().create("credit", Money("9.00"),
                                    card_number="4111111111111111")

    def test_factory_creates_credit_with_gateway(self):
        gateway = SimulatedBankGateway()
        payment = PaymentFactory(credit_gateway=gateway).create(
            "credit", Money("9.00"), card_number="4111111111111111")
        assert payment.kind == "Credit"
        assert payment.masked_card == "************1111"

    def test_declined_card_raises_authorization_error(self):
        gateway = SimulatedBankGateway()
        payment = PaymentFactory(credit_gateway=gateway).create(
            "credit", Money("9.00"), card_number="4000000000000002")
        with pytest.raises(PaymentAuthorizationError):
            payment.authorize()

    def test_unknown_kind_raises(self):
        from pos.domain.payment import UnsupportedPaymentError
        with pytest.raises(UnsupportedPaymentError):
            PaymentFactory().create("bitcoin", Money("9.00"))


# ---------------------------------------------------------------------------
# Return transaction
# ---------------------------------------------------------------------------
class TestReturnTransaction:
    def test_refund_total_sums_line_items(self, catalog):
        ret = ReturnTransaction()
        ret.make_line_item(catalog.get_specification("1001"), 1)   # 4.50
        ret.make_line_item(catalog.get_specification("1002"), 2)   # 4.40
        assert ret.get_refund_total() == Money("8.90")

    def test_empty_return_cannot_be_authorised(self):
        from pos.domain.returns import EmptyReturnError
        with pytest.raises(EmptyReturnError):
            ReturnTransaction().authorize_refund()

    def test_refund_cannot_exceed_original_sale(self, catalog):
        from pos.domain.returns import ReturnAuthorizationError
        sale = Sale()
        sale.make_line_item(catalog.get_specification("1001"), 1)
        sale.make_payment(CashPayment(Money("4.50")))

        ret = ReturnTransaction(original_sale=sale)
        ret.make_line_item(catalog.get_specification("1001"), 5)   # 22.50
        with pytest.raises(ReturnAuthorizationError):
            ret.authorize_refund()

    def test_resellable_and_damaged_lines_are_separated(self, catalog):
        ret = ReturnTransaction()
        ret.make_line_item(catalog.get_specification("1001"), 1, resellable=True)
        ret.make_line_item(catalog.get_specification("1002"), 1, resellable=False)
        assert len(ret.resellable_lines()) == 1
        assert len(ret.damaged_lines()) == 1
        assert ret.resellable_lines()[0].item_id.value == "1001"

    def test_authorising_sets_state_and_refund(self, catalog):
        ret = ReturnTransaction()
        ret.make_line_item(catalog.get_specification("1001"), 2)
        refund = ret.authorize_refund("card")
        assert refund == Money("9.00")
        assert ret.refund == Money("9.00")
        assert ret.state.value == "refunded"
        assert ret.refund_method == "card"


# ---------------------------------------------------------------------------
# Catalog / description class
# ---------------------------------------------------------------------------
class TestProductCatalog:
    def test_lookup_by_string_and_item_id(self, catalog):
        assert catalog.get_specification("1001") is not None
        assert catalog.get_specification("9999") is None
        assert catalog.contains("1002")

    def test_description_class_survives_having_no_physical_items(self, catalog):
        """The whole point of the Description class: price survives the stock."""
        spec = catalog.get_specification("1001")
        assert spec.price == Money("4.50")   # known even with zero items on shelf

    def test_catalog_is_sorted_by_item_id(self, catalog):
        ids = [str(s.item_id) for s in catalog.all_specifications()]
        assert ids == sorted(ids)
