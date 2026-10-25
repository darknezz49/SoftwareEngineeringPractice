"""Presentation layer - the text-mode POS terminal.

A second, headless view over exactly the same application layer as the Tk
GUI.  It exists for three practical reasons:

1. **Accessibility / fallback.**  If Tk is unavailable (a bare server, a
   serial-attached till, a locked-down IT image) the shop can still trade.
2. **Automation.**  A terminal transcript is trivially scriptable, so the
   report's figures and the acceptance demo can be reproduced exactly.
3. **Separation of concerns, demonstrated.**  Because this file replaces
   :mod:`pos.presentation.gui` without changing a single line of the domain or
   application layer, it is direct evidence that the logical architecture's
   layers are real and not decorative.

Run it with::

    python -m pos --terminal
"""
from __future__ import annotations

import sys
from typing import IO, Callable, Iterable

from ..application.pos_application import POSApplication, TransactionError
from ..domain.money import Money

__all__ = ["TerminalPOS", "run_terminal"]

RULE = "=" * 64
THIN = "-" * 64


class TerminalPOS:
    """An interactive, line-oriented POS terminal."""

    def __init__(self, app: POSApplication, stdin: IO[str] | None = None,
                 stdout: IO[str] | None = None,
                 inputs: Iterable[str] | None = None):
        self.app = app
        self._in = stdin or sys.stdin
        self._out = stdout or sys.stdout
        # Scripted input takes precedence, so the demo can be reproduced.
        self._scripted = list(inputs) if inputs is not None else None
        self._script_index = 0
        self._script_exhausted = False

    # -- io helpers --------------------------------------------------------
    def _write(self, text: str = "") -> None:
        self._out.write(text + "\n")

    def _ask(self, prompt: str, default: str = "") -> str:
        if self._scripted is not None:
            if self._script_index >= len(self._scripted):
                # A scripted run has run out of answers.  Mark it so the main
                # loop terminates instead of spinning on the default forever.
                self._script_exhausted = True
                return default
            answer = self._scripted[self._script_index]
            self._script_index += 1
            shown = answer if answer else f"<{default}>"
            self._write(f"{prompt}{shown}")
            return answer.strip() or default
        self._out.write(prompt)
        self._out.flush()
        try:
            answer = input().strip()
        except EOFError:
            self._write("")
            return default
        return answer or default

    # -- chrome ------------------------------------------------------------
    def banner(self) -> None:
        store = getattr(self.app.register.store, "name", "Store")
        self._write(RULE)
        self._write("  NextGen POS  -  Point of Sale System".ljust(64))
        self._write(f"  {store}   |   Register {self.app.register.id}".ljust(64))
        self._write(RULE)

    def main_menu_line(self) -> None:
        self._write("")
        self._write("  [1] Process Sale        [2] Handle Returns")
        self._write("  [3] Store Status        [0] Exit")
        self._write(THIN)

    # -- Process Sale ------------------------------------------------------
    def process_sale(self) -> None:
        controller = self.app.process_sale
        self._write("")
        self._write("PROCESS SALE")
        self._write(THIN)
        controller.make_new_sale()
        self._write(f"Sale {controller.sale_id} opened.")
        self._print_catalogue_brief()

        while True:
            entry = self._ask("  Scan item id (or 'total' to pay, "
                              "'remove' to void a line): ")
            if not entry:
                continue
            if entry.lower() in ("total", "t", "pay", "done"):
                if not controller.line_items():
                    self._write("  ! The sale is empty - nothing to pay for.")
                    continue
                break
            if entry.lower() in ("remove", "r"):
                item_id = self._ask("  Item id to remove: ")
                try:
                    controller.remove_item(item_id)
                    self._write(f"  - removed {item_id}")
                except TransactionError as exc:
                    self._write(f"  ! {exc}")
                self._print_basket()
                continue

            quantity_raw = self._ask("  Quantity <1>: ", "1")
            try:
                quantity = int(quantity_raw)
            except ValueError:
                quantity = 1
            try:
                line = controller.enter_item(entry, quantity)
            except TransactionError as exc:
                self._write(f"  ! {exc}")
                continue
            self._write(f"  + {line.quantity} x {line.description:<28}"
                        f"{line.subtotal:>8}")
            self._print_basket()

        self._print_basket()
        self._write(f"  AMOUNT DUE: {controller.running_total()}")
        self._write("")
        self._write("  [1] Cash    [2] Credit card    [0] Cancel sale")
        choice = self._ask("  Payment method <1>: ", "1")

        if choice == "0":
            controller.cancel_transaction()
            self._write("  Sale cancelled. Inventory unchanged.")
            return

        options: dict = {}
        if choice == "2":
            options["card_number"] = self._ask(
                "  Card number <4111111111111111>: ", "4111111111111111")
            kind = "credit"
        else:
            tendered = self._ask("  Cash tendered: ")
            if tendered:
                options["tendered"] = Money(tendered)
            kind = "cash"

        self._write(THIN)
        try:
            result = controller.make_payment(kind, **options)
        except TransactionError as exc:
            self._write(f"  !! PAYMENT FAILED: {exc}")
            self._write("  The sale is still open - try another payment.")
            retry = self._ask("  Retry? [1] cash [2] card [0] cancel <0>: ", "0")
            if retry == "1" and kind != "cash":
                tendered = self._ask("  Cash tendered: ")
                opts = {"tendered": Money(tendered)} if tendered else {}
                try:
                    result = controller.make_payment("cash", **opts)
                except TransactionError as exc2:
                    self._write(f"  !! {exc2}")
                    controller.cancel_transaction()
                    return
            elif retry == "2":
                card = self._ask("  Card number: ")
                try:
                    result = controller.make_payment("credit", card_number=card)
                except TransactionError as exc2:
                    self._write(f"  !! {exc2}")
                    controller.cancel_transaction()
                    return
            else:
                controller.cancel_transaction()
                self._write("  Sale cancelled.")
                return

        self._write("")
        self._write(result.receipt_text)
        self._write("")
        self._write(f"  Sale {result.sale_id} complete. "
                    f"{result.payment_kind} {result.total}"
                    + (f", change {result.change}" if result.change != "0.00"
                       else ""))

    # -- Handle Returns ----------------------------------------------------
    def handle_returns(self) -> None:
        controller = self.app.handle_returns
        self._write("")
        self._write("HANDLE RETURNS")
        self._write(THIN)

        recent = controller.recent_sales(6)
        if recent:
            self._write("  Recent sales:")
            for sale_id, total, items in recent:
                self._write(f"    {sale_id}   total {total:>8}   {items} item(s)")
        else:
            self._write("  No completed sales in this session.")

        sale_id = self._ask("  Original receipt / sale id "
                            "(blank = no receipt): ")
        try:
            controller.make_new_return(sale_id)
        except TransactionError as exc:
            self._write(f"  ! {exc}")
            self._write("  Return abandoned - returning to the main menu.")
            return
        self._write(f"  Return {controller.return_id} opened"
                    + (f" against {sale_id}." if sale_id else "."))

        while True:
            entry = self._ask("  Item id being returned "
                              "(or 'done' to refund): ")
            if not entry:
                continue
            if entry.lower() in ("done", "d", "refund"):
                if not controller.line_items():
                    self._write("  ! Nothing has been entered to return.")
                    continue
                break
            quantity_raw = self._ask("  Quantity <1>: ", "1")
            try:
                quantity = int(quantity_raw)
            except ValueError:
                quantity = 1
            damaged = self._ask("  Is the item resellable? [Y/n] <Y>: ", "Y")
            resellable = damaged.strip().lower() in ("", "y", "yes")
            try:
                line = controller.enter_return_item(
                    entry, quantity, resellable=resellable)
            except TransactionError as exc:
                self._write(f"  ! {exc}")
                continue
            note = "" if resellable else "  (damaged - will NOT be restocked)"
            self._write(f"  + {line.quantity} x {line.description:<28}"
                        f"{line.subtotal:>8}{note}")

        self._write(THIN)
        self._write(f"  REFUND DUE: {controller.refund_total()}")
        method = self._ask("  Refund method [1] cash [2] card <1>: ", "1")
        method_name = "card" if method == "2" else "cash"

        try:
            controller.authorize_refund(method_name)
            result = controller.end_return()
        except TransactionError as exc:
            self._write(f"  !! REFUND FAILED: {exc}")
            controller.cancel_transaction()
            return

        self._write("")
        self._write(result.receipt_text)
        self._write("")
        self._write(f"  Return {result.return_id} refunded {result.refund_total}"
                    f" via {result.method}.")
        self._write(f"  Restocked {result.restocked_units} unit(s); "
                    f"{result.damaged_units} unit(s) written off as damaged.")

    # -- Store Status ------------------------------------------------------
    def store_status(self) -> None:
        self._write("")
        self._write("STORE STATUS")
        self._write(THIN)
        summary = self.app.sales_summary()
        self._write(f"  Completed sales : {summary['sales']}")
        self._write(f"  Revenue         : {summary['revenue']}")
        self._write(f"  Returns         : {summary['returns']}")
        self._write(f"  Refunded        : {summary['refunded']}")
        self._write("")
        self._write(f"  {'Item':<8}{'Description':<32}{'Price':>8}{'Stock':>7}")
        self._write("  " + "-" * 53)
        specs = {str(s.item_id): s
                 for s in self.app.catalog.all_specifications()}
        for item_id, level in self.app.stock_snapshot().items():
            spec = specs.get(item_id)
            description = spec.description if spec else ""
            price = str(spec.price) if spec else ""
            self._write(f"  {item_id:<8}{description:<32}{price:>8}{level:>7}")
        self._write("")
        self._write("  Recent system operations:")
        for entry in self.app.audit.recent(8):
            self._write(f"    {entry.when:%H:%M:%S}  {entry.operation:<18}"
                        f"[{entry.outcome}] {entry.detail}")

    # -- helpers -----------------------------------------------------------
    def _print_catalogue_brief(self) -> None:
        self._write("  Catalogue:")
        entries = self.app.catalog_entries()
        for i in range(0, len(entries), 2):
            row = ""
            for item_id, description, price in entries[i:i + 2]:
                row += f"    {item_id}  {description[:24]:<24}{price:>7}"
            self._write(row)

    def _print_basket(self) -> None:
        lines = self.app.process_sale.line_items()
        if not lines:
            return
        self._write("  " + "-" * 60)
        for line in lines:
            self._write(f"    {line.item_id:<6}{line.description[:26]:<27}"
                        f"{line.quantity:>4} x {line.unit_price:>7}"
                        f" = {line.subtotal:>8}")
        self._write(f"    {'RUNNING TOTAL':<52}"
                    f"{str(self.app.process_sale.running_total()):>8}")
        self._write("  " + "-" * 60)

    # -- main loop ---------------------------------------------------------
    def run(self) -> int:
        self.banner()
        while True:
            if self._script_exhausted:
                self._write("")
                self._write("  (scripted session finished)")
                return 0
            self.main_menu_line()
            choice = self._ask("  Select <0>: ", "0")
            if choice == "1":
                self.process_sale()
            elif choice == "2":
                self.handle_returns()
            elif choice == "3":
                self.store_status()
            elif choice in ("0", "q", "quit", "exit"):
                self._write("")
                self._write("  Goodbye.")
                return 0
            else:
                self._write("  ! Unknown option.")


def run_terminal(gateway_kind: str = "simulated",
                 inputs: Iterable[str] | None = None,
                 stdout: IO[str] | None = None) -> int:
    """Build the application and run the terminal view."""
    from ..application.pos_application import build_application

    app = build_application(gateway_kind=gateway_kind)
    return TerminalPOS(app, inputs=inputs, stdout=stdout).run()
