#!/usr/bin/env python3
"""Drive the POS GUI through scripted scenarios and capture screenshots.

Used to produce the figures for the technical report and the slide deck.

Usage::

    python docs/capture_screenshots.py [output-dir]

The script builds the real application, exercises it through the real
controllers (not by faking state), and saves a PNG per scenario via the macOS
``screencapture`` utility, cropping to the POS window's own frame.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import tkinter as tk  # noqa: E402

from pos.application import build_application  # noqa: E402
from pos.presentation.gui import POSWindow  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screenshots"


def capture(root: tk.Tk, name: str) -> str:
    """Screenshot the region occupied by ``root`` into ``OUT/<name>.png``."""
    root.update_idletasks()
    root.update()
    time.sleep(0.45)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    path = OUT / f"{name}.png"
    result = subprocess.run(
        ["screencapture", "-x", "-o", "-R", f"{x},{y},{w},{h}", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  !! screencapture failed for {name}: {result.stderr.strip()}")
    return str(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = build_application(gateway_kind="simulated")

    root = tk.Tk()
    root.geometry("1180x760+40+60")
    window = POSWindow(app, master=root)
    root.update_idletasks()
    root.update()

    # Bring the window forward so the capture is not occluded, but restore the
    # user's focus afterwards.
    root.lift()
    root.attributes("-topmost", True)
    root.update()
    time.sleep(0.6)

    shots: list[tuple[str, str]] = []

    # ---- 1. Process Sale: basket built, waiting for payment ---------------
    window.select_tab(0)
    window.demo_process_sale(items=(("1001", 2), ("1005", 1), ("1008", 3)),
                             tendered="30.00")
    shots.append(("01-process-sale", capture(root, "01-process-sale")))

    # ---- 2. Sales receipt -------------------------------------------------
    result = app.process_sale.make_payment("cash", tendered="30.00")
    window._refresh_sale()
    window._refresh_stock()
    window._show_receipt("Sales Receipt", result.receipt_text)
    root.update_idletasks()
    root.update()
    time.sleep(0.7)
    shots.append(("02-sales-receipt", capture(root, "02-sales-receipt")))
    # close the receipt dialog (it is a Toplevel, so it is the last child)
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel):
            child.destroy()
    root.update()

    # ---- 3. Store status after the sale -----------------------------------
    window.select_tab(2)
    window._refresh_stock()
    shots.append(("03-store-status", capture(root, "03-store-status")))

    # ---- 4. Handle Returns: a return opened against the receipt ----------
    window.select_tab(1)
    window._refresh_recent_sales()
    sale_id = app.sales.all_sales()[-1].id
    window.return_sale_id.set(sale_id)
    window._return_open()
    window.return_resellable.set(True)
    window.refund_method.set("card")
    for item_id, quantity in (("1001", 1), ("1008", 2)):
        window.return_search.set(item_id)
        window.return_qty.set(quantity)
        window._return_add()
    window.select_tab(1)
    shots.append(("04-handle-returns", capture(root, "04-handle-returns")))

    # ---- 5. Refund receipt ------------------------------------------------
    app.handle_returns.authorize_refund("card")
    refund = app.handle_returns.end_return()
    window._refresh_return()
    window._refresh_stock()
    window._refresh_recent_sales()
    window._show_receipt("Refund Receipt", refund.receipt_text)
    root.update_idletasks()
    root.update()
    time.sleep(0.7)
    shots.append(("05-refund-receipt", capture(root, "05-refund-receipt")))
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel):
            child.destroy()
    root.update()

    # ---- 6. Store status after the return ---------------------------------
    window.select_tab(2)
    window._refresh_stock()
    shots.append(("06-store-status-final", capture(root, "06-store-status-final")))

    # ---- 7. The decline path ---------------------------------------------
    window.select_tab(0)
    window._sale_new()
    window.sale_search.set("1005")
    window.sale_qty.set(1)
    window._sale_scan()
    window.pay_kind.set("credit")
    window.card_number.set("4000000000000002")
    shots.append(("07-credit-entry", capture(root, "07-credit-entry")))

    root.attributes("-topmost", False)
    root.destroy()

    print(f"\nWrote {len(shots)} screenshots to {OUT}")
    for name, path in shots:
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {name:<24} {size:>9,} bytes  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
