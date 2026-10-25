"""Entry point: ``python -m pos`` launches the POS terminal GUI.

A ``--demo`` flag drives a scripted sale so the application can be exercised
without a human at the keyboard (used by the tests and the screenshot script).
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pos", description="NextGen POS - point of sale system")
    parser.add_argument("--gateway", default="simulated",
                        choices=["simulated", "legacy", "soap"],
                        help="which card-service adapter to use")
    parser.add_argument("--headless-demo", action="store_true",
                        help="run a scripted sale/return with no GUI")
    parser.add_argument("--terminal", action="store_true",
                        help="use the text-mode interface instead of the GUI")
    args = parser.parse_args(argv)

    if args.headless_demo:
        return _headless_demo(args.gateway)

    if args.terminal:
        from .presentation.terminal import run_terminal
        return run_terminal(gateway_kind=args.gateway)

    from .presentation.gui import launch
    launch(gateway_kind=args.gateway)
    return 0


def _headless_demo(gateway_kind: str) -> int:
    from .application.pos_application import TransactionError, build_application

    app = build_application(gateway_kind=gateway_kind)
    sale = app.process_sale

    print("=" * 58)
    print(f"NextGen POS headless demo (gateway = {gateway_kind})")
    print("=" * 58)

    sale.make_new_sale()
    for item_id, quantity in (("1001", 2), ("1005", 1), ("1008", 3)):
        line = sale.enter_item(item_id, quantity)
        print(f"  enterItem      {line.quantity} x {line.description:<28} "
              f"{line.subtotal:>8}")
    print(f"  running total  {sale.running_total()}")
    try:
        result = sale.make_payment("cash", tendered="30.00")
    except TransactionError as exc:
        print(f"  payment failed: {exc}")
        return 1
    print(result.receipt_text)

    returns = app.handle_returns
    returns.make_new_return("")
    line = returns.enter_return_item("1001", 1, resellable=True)
    print(f"\n  enterReturnItem {line.quantity} x {line.description} "
          f"-> refund {line.subtotal}")
    returns.authorize_refund("cash")
    refund = returns.end_return()
    print(refund.receipt_text)

    print("\nStock on hand after the transactions:")
    for item_id, level in app.stock_snapshot().items():
        print(f"  {item_id}: {level}")
    print(f"\nSummary: {app.sales_summary()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
