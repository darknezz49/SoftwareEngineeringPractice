"""Integration tests for the two use cases, driven through the controllers."""
from __future__ import annotations

import pytest

from pos.application.pos_application import TransactionError
from pos.domain import Money


# ---------------------------------------------------------------------------
# Process Sale
# ---------------------------------------------------------------------------
class TestProcessSaleUseCase:
    def test_happy_path_produces_a_receipt_and_a_total(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 2)          # 4.50 x 2 = 9.00
        sale.enter_item("1005", 1)          # 8.80
        assert sale.running_total() == Money("17.80")

        result = sale.make_payment("cash", tendered="20.00")
        assert result.total == "17.80"
        assert result.change == "2.20"
        assert "SALES RECEIPT" in result.receipt_text
        assert "Veggie Burger" in result.receipt_text
        assert not sale.is_sale_in_progress

    def test_inventory_is_decremented_on_payment(self, small_app):
        inv = small_app.inventory
        assert inv.get_level("1001") == 10
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 3)
        sale.make_payment("cash")
        assert inv.get_level("1001") == 7

    def test_inventory_is_not_decremented_for_an_abandoned_sale(self, small_app):
        inv = small_app.inventory
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 4)
        sale.cancel_transaction()
        assert inv.get_level("1001") == 10

    def test_scanning_the_same_item_twice_merges_the_line(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 1)
        sale.enter_item("1001", 2)
        lines = sale.line_items()
        assert len(lines) == 1
        assert lines[0].quantity == 3
        assert sale.running_total() == Money("13.50")

    def test_unknown_item_is_reported_as_a_transaction_error(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        with pytest.raises(TransactionError, match="not in the catalogue"):
            sale.enter_item("9999", 1)

    def test_oversell_is_refused(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        with pytest.raises(TransactionError, match="in stock"):
            sale.enter_item("1001", 11)

    def test_enter_item_without_a_sale_is_refused(self, small_app):
        with pytest.raises(TransactionError):
            small_app.process_sale.enter_item("1001", 1)

    def test_remove_item_takes_the_line_off(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 1)
        sale.enter_item("1002", 1)
        sale.remove_item("1001")
        assert [li.item_id for li in sale.line_items()] == ["1002"]

    def test_removing_an_absent_item_reports_an_error(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        with pytest.raises(TransactionError, match="not on this sale"):
            sale.remove_item("1001")

    def test_credit_payment_is_authorised_by_the_gateway(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1005", 1)
        result = sale.make_payment("credit", card_number="4111111111111111")
        assert result.payment_kind == "Credit"
        assert result.reference.startswith("AUTH")

    def test_declined_card_leaves_the_sale_open(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1005", 1)
        with pytest.raises(TransactionError, match="declined"):
            sale.make_payment("credit", card_number="4000000000000002")
        assert sale.is_sale_in_progress          # can still be retried
        assert small_app.inventory.get_level("1005") == 10

    def test_completed_sale_is_stored_in_the_repository(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale_id = sale.sale_id
        sale.enter_item("1001", 1)
        sale.make_payment("cash")
        assert len(small_app.sales) == 1
        assert small_app.sales.get(sale_id) is not None

    def test_summary_reports_revenue(self, small_app):
        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 2)
        sale.make_payment("cash")
        assert small_app.sales_summary()["revenue"] == "9.00"


# ---------------------------------------------------------------------------
# Handle Returns
# ---------------------------------------------------------------------------
class TestHandleReturnsUseCase:
    def _make_a_sale(self, app, items=(("1001", 2),)):
        sale = app.process_sale
        sale.make_new_sale()
        for item_id, quantity in items:
            sale.enter_item(item_id, quantity)
        sale.make_payment("cash")
        return app.sales.all_sales()[-1].id

    def test_return_with_receipt_refunds_and_restocks(self, small_app):
        sale_id = self._make_a_sale(small_app, (("1001", 2),))
        assert small_app.inventory.get_level("1001") == 8

        returns = small_app.handle_returns
        returns.make_new_return(sale_id)
        returns.enter_return_item("1001", 1)
        assert returns.refund_total() == Money("4.50")
        returns.authorize_refund("cash")
        result = returns.end_return()

        assert result.refund_total == "4.50"
        assert result.original_sale_id == sale_id
        assert "REFUND RECEIPT" in result.receipt_text
        assert small_app.inventory.get_level("1001") == 9     # restocked

    def test_damaged_item_is_not_restocked(self, small_app):
        sale_id = self._make_a_sale(small_app, (("1001", 2),))
        before = small_app.inventory.get_level("1001")

        returns = small_app.handle_returns
        returns.make_new_return(sale_id)
        returns.enter_return_item("1001", 1, resellable=False)
        returns.authorize_refund("cash")
        result = returns.end_return()

        assert small_app.inventory.get_level("1001") == before   # unchanged
        assert result.damaged_units == 1
        assert result.restocked_units == 0

    def test_cannot_return_more_than_was_sold(self, small_app):
        sale_id = self._make_a_sale(small_app, (("1001", 2),))
        returns = small_app.handle_returns
        returns.make_new_return(sale_id)
        with pytest.raises(TransactionError, match="only 2 were sold"):
            returns.enter_return_item("1001", 3)

    def test_cannot_return_an_item_not_on_the_receipt(self, small_app):
        sale_id = self._make_a_sale(small_app, (("1001", 2),))
        returns = small_app.handle_returns
        returns.make_new_return(sale_id)
        with pytest.raises(TransactionError, match="was not part of sale"):
            returns.enter_return_item("1005", 1)

    def test_unknown_original_sale_is_rejected(self, small_app):
        with pytest.raises(TransactionError, match="was not found"):
            small_app.handle_returns.make_new_return("S999999")

    def test_return_without_a_receipt_is_allowed(self, small_app):
        returns = small_app.handle_returns
        returns.make_new_return("")
        returns.enter_return_item("1002", 1)
        returns.authorize_refund("cash")
        result = returns.end_return()
        assert result.refund_total == "2.20"
        assert result.original_sale_id == ""

    def test_empty_return_cannot_be_authorised(self, small_app):
        returns = small_app.handle_returns
        returns.make_new_return("")
        with pytest.raises(TransactionError):
            returns.authorize_refund("cash")

    def test_completed_return_is_stored(self, small_app):
        self._make_a_sale(small_app, (("1001", 1),))
        returns = small_app.handle_returns
        returns.make_new_return("")
        returns.enter_return_item("1001", 1)
        returns.authorize_refund("cash")
        returns.end_return()
        assert len(small_app.returns) == 1
        assert small_app.sales_summary()["refunded"] == "4.50"

    def test_return_merges_repeated_lines(self, small_app):
        self._make_a_sale(small_app, (("1001", 2),))
        returns = small_app.handle_returns
        returns.make_new_return("")
        returns.enter_return_item("1001", 1)
        returns.enter_return_item("1001", 1)
        assert len(returns.line_items()) == 1
        assert returns.line_items()[0].quantity == 2

    def test_cancelled_return_does_not_restock(self, small_app):
        self._make_a_sale(small_app, (("1001", 2),))
        before = small_app.inventory.get_level("1001")
        returns = small_app.handle_returns
        returns.make_new_return("")
        returns.enter_return_item("1001", 1)
        returns.cancel_transaction()
        assert small_app.inventory.get_level("1001") == before


# ---------------------------------------------------------------------------
# End-to-end: sale then return of part of it
# ---------------------------------------------------------------------------
class TestSaleThenReturnRoundTrip:
    def test_full_round_trip_leaves_consistent_stock(self, small_app):
        inv = small_app.inventory
        start = inv.get_level("1001")

        sale = small_app.process_sale
        sale.make_new_sale()
        sale.enter_item("1001", 4)
        sale.enter_item("1005", 2)
        sale.make_payment("cash")
        sale_id = small_app.sales.all_sales()[-1].id

        assert inv.get_level("1001") == start - 4
        assert inv.get_level("1005") == 8

        returns = small_app.handle_returns
        returns.make_new_return(sale_id)
        returns.enter_return_item("1001", 2)        # keep 2, return 2
        returns.authorize_refund("cash")
        result = returns.end_return()

        assert result.refund_total == "9.00"
        assert inv.get_level("1001") == start - 2
        summary = small_app.sales_summary()
        assert summary["sales"] == 1
        assert summary["returns"] == 1
        # 4 x 4.50 = 18.00, plus 2 x 8.80 = 17.60  -> 35.60
        assert summary["revenue"] == "35.60"
