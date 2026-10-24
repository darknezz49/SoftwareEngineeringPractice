"""Presentation layer - the POS GUI (Tkinter).

Model-View Separation in practice: this module builds widgets, catches UI
events, and **delegates** every piece of application logic to the controllers.
It contains no business rules, no arithmetic on money, and no knowledge of the
payment gateways.

Layout:

* **Process Sale** tab  - the cashier's checkout screen.
* **Handle Returns** tab - the same screen shape for refunds ("比着葫芦画瓢").
* **Store Status** tab  - stock on hand, session summary and the audit trail.

Run it with::

    python -m pos
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from ..application.pos_application import POSApplication, TransactionError

__all__ = ["POSWindow", "launch"]

# -- palette -----------------------------------------------------------------
BG = "#F4F6F8"
PANEL = "#FFFFFF"
INK = "#1F2A37"
ACCENT = "#1F4E79"
ACCENT_LIGHT = "#DEEAF6"
OK = "#1E7B34"
WARN = "#B45309"
ERR = "#B42318"
MONO = ("Courier New", 10)
UI = ("Arial", 11)
UI_BOLD = ("Arial", 11, "bold")
UI_BIG = ("Arial", 22, "bold")
UI_TITLE = ("Arial", 15, "bold")


class POSWindow:
    """The main POS terminal window."""

    def __init__(self, app: POSApplication, master: tk.Misc | None = None):
        self.app = app
        self.root = master if master is not None else tk.Tk()
        self._owns_root = master is None

        self.root.title("NextGen POS  -  Point of Sale System")
        self.root.configure(bg=BG)
        self.root.geometry("1180x760")
        self.root.minsize(1040, 700)

        self._configure_styles()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        # seed a clean state
        self.sales_status.set("Ready. Press  New Sale  to begin.")
        self.returns_status.set("Ready. Look up the original sale, or enter items.")
        self._refresh_product_list()
        self._refresh_recent_sales()
        self._refresh_stock()

    # =====================================================================
    # styling
    # =====================================================================
    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=UI_BOLD, padding=(18, 9),
                        background="#E3E8EF", foreground=INK)
        style.map("TNotebook.Tab",
                  background=[("selected", PANEL)],
                  foreground=[("selected", ACCENT)])
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL, relief="flat")
        style.configure("TLabel", background=PANEL, foreground=INK, font=UI)
        style.configure("Head.TLabel", background=PANEL, foreground=ACCENT,
                        font=UI_BOLD)
        style.configure("Big.TLabel", background=PANEL, foreground=ACCENT,
                        font=UI_BIG)
        style.configure("Hint.TLabel", background=PANEL, foreground="#667085",
                        font=("Arial", 9))
        style.configure("TButton", font=UI_BOLD, padding=(12, 7))
        style.configure("Accent.TButton", font=UI_BOLD, padding=(14, 9),
                        background=ACCENT, foreground="white")
        style.map("Accent.TButton",
                  background=[("active", "#2E75B6"), ("disabled", "#B6C2D1")])
        style.configure("Danger.TButton", font=UI_BOLD, padding=(12, 7),
                        background="#FEE4E2", foreground=ERR)
        style.configure("Treeview", font=("Arial", 10), rowheight=24,
                        background=PANEL, fieldbackground=PANEL)
        style.configure("Treeview.Heading", font=UI_BOLD,
                        background=ACCENT_LIGHT, foreground=ACCENT)
        style.configure("TLabelframe", background=PANEL, borderwidth=1,
                        relief="solid")
        style.configure("TLabelframe.Label", background=PANEL,
                        foreground=ACCENT, font=UI_BOLD)
        style.configure("TCheckbutton", background=PANEL, font=UI)
        style.configure("TRadiobutton", background=PANEL, font=UI)

    # =====================================================================
    # chrome
    # =====================================================================
    def _build_header(self) -> None:
        bar = tk.Frame(self.root, bg=ACCENT, height=58)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        tk.Label(bar, text="NextGen POS", bg=ACCENT, fg="white",
                 font=UI_TITLE).pack(side="left", padx=(18, 10), pady=12)
        tk.Label(bar, text="Point of Sale System  -  Process Sale & Handle Returns",
                 bg=ACCENT, fg="#CBDBEC", font=("Arial", 10)
                 ).pack(side="left", pady=16)
        store = getattr(self.app.register.store, "name", "")
        tk.Label(bar, text=f"{store}   |   {self.app.register.id}",
                 bg=ACCENT, fg="white", font=UI_BOLD
                 ).pack(side="right", padx=18)

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self.root, bg="#E3E8EF", height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.statusbar = tk.Label(bar, text="System ready.", bg="#E3E8EF",
                                  fg=INK, font=("Arial", 9), anchor="w")
        self.statusbar.pack(fill="x", padx=14, pady=6)

    def _build_tabs(self) -> None:
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.sales_status = tk.StringVar()
        self.returns_status = tk.StringVar()

        self.sale_tab = ttk.Frame(self.tabs)
        self.return_tab = ttk.Frame(self.tabs)
        self.status_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.sale_tab, text="  Process Sale  ")
        self.tabs.add(self.return_tab, text="  Handle Returns  ")
        self.tabs.add(self.status_tab, text="  Store Status  ")

        self._build_sale_tab()
        self._build_return_tab()
        self._build_status_tab()

    def _say(self, text: str, tone: str = "info") -> None:
        self.statusbar.configure(text=text,
                                 fg={"info": INK, "ok": OK, "warn": WARN,
                                     "error": ERR}.get(tone, INK))

    # =====================================================================
    # Process Sale tab
    # =====================================================================
    def _build_sale_tab(self) -> None:
        tab = self.sale_tab
        left = ttk.Frame(tab, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
        right = ttk.Frame(tab, style="Card.TFrame", width=330)
        right.pack(side="right", fill="y", padx=(8, 0), pady=8)
        right.pack_propagate(False)

        # ---- left: catalogue + basket -----------------------------------
        ttk.Label(left, text="Product Catalogue", style="Head.TLabel"
                  ).pack(anchor="w", padx=14, pady=(12, 4))

        search_row = ttk.Frame(left, style="Card.TFrame")
        search_row.pack(fill="x", padx=14, pady=(0, 6))
        ttk.Label(search_row, text="Scan / search:", style="TLabel"
                  ).pack(side="left")
        self.sale_search = tk.StringVar()
        entry = ttk.Entry(search_row, textvariable=self.sale_search, font=UI, width=26)
        entry.pack(side="left", padx=8)
        entry.bind("<Return>", lambda _e: self._sale_scan())
        ttk.Button(search_row, text="Add Item", style="Accent.TButton",
                   command=self._sale_scan).pack(side="left")
        self.sale_qty = tk.IntVar(value=1)
        ttk.Label(search_row, text="Qty:", style="TLabel").pack(side="left", padx=(14, 2))
        ttk.Spinbox(search_row, from_=1, to=99, width=4,
                    textvariable=self.sale_qty).pack(side="left")

        cols = ("id", "description", "price", "stock")
        self.product_tree = ttk.Treeview(left, columns=cols, show="headings",
                                         height=7)
        for col, title, width in (("id", "Item ID", 90),
                                  ("description", "Description", 330),
                                  ("price", "Price", 90),
                                  ("stock", "Stock", 80)):
            self.product_tree.heading(col, text=title)
            self.product_tree.column(col, width=width,
                                     anchor="e" if col in ("price", "stock") else "w")
        self.product_tree.pack(fill="x", padx=14, pady=(0, 8))
        self.product_tree.bind("<Double-1>", lambda _e: self._sale_scan())

        ttk.Label(left, text="Current Sale", style="Head.TLabel"
                  ).pack(anchor="w", padx=14, pady=(6, 4))

        basket_cols = ("id", "description", "qty", "price", "subtotal")
        self.basket_tree = ttk.Treeview(left, columns=basket_cols,
                                        show="headings", height=8)
        for col, title, width in (("id", "Item ID", 80),
                                  ("description", "Description", 300),
                                  ("qty", "Qty", 60),
                                  ("price", "Unit Price", 90),
                                  ("subtotal", "Subtotal", 100)):
            self.basket_tree.heading(col, text=title)
            self.basket_tree.column(
                col, width=width,
                anchor="e" if col in ("qty", "price", "subtotal") else "w")
        self.basket_tree.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # ---- right: totals + payment ------------------------------------
        ttk.Label(right, text="Sale Summary", style="Head.TLabel"
                  ).pack(anchor="w", padx=16, pady=(14, 4))
        self.sale_id_label = ttk.Label(right, text="Sale:  -", style="Hint.TLabel")
        self.sale_id_label.pack(anchor="w", padx=16)

        box = ttk.Frame(right, style="Card.TFrame")
        box.pack(fill="x", padx=16, pady=(10, 4))
        ttk.Label(box, text="Items", style="TLabel").grid(row=0, column=0, sticky="w")
        self.sale_items_value = ttk.Label(box, text="0", style="Head.TLabel")
        self.sale_items_value.grid(row=0, column=1, sticky="e", padx=(60, 0))
        ttk.Label(box, text="TOTAL", style="Head.TLabel"
                  ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.sale_total_value = ttk.Label(box, text="0.00", style="Big.TLabel")
        self.sale_total_value.grid(row=1, column=1, sticky="e", pady=(8, 0))

        pay = ttk.LabelFrame(right, text="Payment")
        pay.pack(fill="x", padx=16, pady=(14, 6))
        self.pay_kind = tk.StringVar(value="cash")
        ttk.Radiobutton(pay, text="Cash", value="cash",
                        variable=self.pay_kind).grid(row=0, column=0,
                                                     sticky="w", padx=10, pady=(8, 2))
        ttk.Radiobutton(pay, text="Credit card", value="credit",
                        variable=self.pay_kind).grid(row=0, column=1,
                                                     sticky="w", pady=(8, 2))
        ttk.Label(pay, text="Cash tendered:", style="TLabel"
                  ).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.tendered = tk.StringVar(value="")
        ttk.Entry(pay, textvariable=self.tendered, width=10, font=UI
                  ).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(pay, text="Card number:", style="TLabel"
                  ).grid(row=2, column=0, sticky="w", padx=10, pady=4)
        self.card_number = tk.StringVar(value="4111111111111111")
        ttk.Entry(pay, textvariable=self.card_number, width=20, font=UI
                  ).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Label(pay, text="(use 4111... to approve, 4000... to decline)",
                  style="Hint.TLabel").grid(row=3, column=0, columnspan=2,
                                            sticky="w", padx=10, pady=(0, 8))

        actions = ttk.Frame(right, style="Card.TFrame")
        actions.pack(fill="x", padx=16, pady=(6, 4))
        ttk.Button(actions, text="New Sale", style="Accent.TButton",
                   command=self._sale_new).pack(fill="x", pady=3)
        ttk.Button(actions, text="Pay & Print Receipt",
                   command=self._sale_pay).pack(fill="x", pady=3)
        ttk.Button(actions, text="Remove Selected Line",
                   command=self._sale_remove).pack(fill="x", pady=3)
        ttk.Button(actions, text="Cancel Sale", style="Danger.TButton",
                   command=self._sale_cancel).pack(fill="x", pady=3)

        ttk.Label(right, textvariable=self.sales_status, style="Hint.TLabel",
                  wraplength=290, justify="left"
                  ).pack(anchor="w", padx=16, pady=(8, 0))

    # -- sale actions ------------------------------------------------------
    def _refresh_product_list(self, filter_text: str = "") -> None:
        self.product_tree.delete(*self.product_tree.get_children())
        needle = filter_text.strip().lower()
        for item_id, description, price in self.app.catalog_entries():
            if needle and needle not in item_id.lower() \
                    and needle not in description.lower():
                continue
            try:
                stock = self.app.inventory.get_level(item_id)
            except Exception:
                stock = "-"
            self.product_tree.insert("", "end",
                                     values=(item_id, description, price, stock))

    def _sale_scan(self) -> None:
        item_id = self.sale_search.get().strip()
        if not item_id:
            selected = self.product_tree.selection()
            if selected:
                item_id = self.product_tree.item(selected[0])["values"][0]
        if not item_id:
            self._say("Enter or select an item id first.", "warn")
            return
        try:
            quantity = int(self.sale_qty.get())
        except (tk.TclError, ValueError):
            quantity = 1
        try:
            self.app.process_sale.enter_item(str(item_id), quantity)
        except TransactionError as exc:
            messagebox.showerror("Process Sale", str(exc), parent=self.root)
            self._say(str(exc), "error")
            return
        self.sale_search.set("")
        self.sale_qty.set(1)
        self._refresh_sale()
        self._refresh_stock()
        self._say(f"Added {item_id} x{quantity}.", "ok")

    def _sale_new(self) -> None:
        try:
            sale_id = self.app.process_sale.make_new_sale()
        except TransactionError as exc:
            self._say(str(exc), "error")
            return
        self._refresh_sale()
        self._say(f"Started {sale_id}. Scan items to begin.", "ok")

    def _sale_remove(self) -> None:
        selected = self.basket_tree.selection()
        if not selected:
            self._say("Select a line in the current sale to remove.", "warn")
            return
        item_id = self.basket_tree.item(selected[0])["values"][0]
        try:
            self.app.process_sale.remove_item(str(item_id))
        except TransactionError as exc:
            self._say(str(exc), "error")
            return
        self._refresh_sale()
        self._refresh_stock()
        self._say(f"Removed {item_id}.", "ok")

    def _sale_cancel(self) -> None:
        self.app.process_sale.cancel_transaction()
        self._refresh_sale()
        self._refresh_stock()
        self._say("Sale cancelled. Inventory unchanged.", "warn")

    def _sale_pay(self) -> None:
        if not self.app.process_sale.is_sale_in_progress:
            self._say("Start a new sale first.", "warn")
            return
        kind = self.pay_kind.get()
        options: dict = {}
        if kind == "cash":
            raw = self.tendered.get().strip()
            if raw:
                try:
                    from ..domain.money import Money
                    options["tendered"] = Money(raw)
                except Exception:
                    messagebox.showerror("Payment",
                                         f"'{raw}' is not a valid amount.",
                                         parent=self.root)
                    return
        else:
            options["card_number"] = self.card_number.get().strip()
        try:
            result = self.app.process_sale.make_payment(kind, **options)
        except TransactionError as exc:
            messagebox.showerror("Payment", str(exc), parent=self.root)
            self._say(str(exc), "error")
            return

        self._refresh_sale()
        self._refresh_stock()
        self.tendered.set("")
        self._show_receipt("Sales Receipt", result.receipt_text)
        summary = (f"Sale {result.sale_id} paid by {result.payment_kind}: "
                   f"{result.total}")
        if result.change not in ("0.00", ""):
            summary += f"   change {result.change}"
        self._say(summary, "ok")

    def _refresh_sale(self) -> None:
        self.basket_tree.delete(*self.basket_tree.get_children())
        for line in self.app.process_sale.line_items():
            self.basket_tree.insert(
                "", "end",
                values=(line.item_id, line.description, line.quantity,
                        line.unit_price, line.subtotal))
        total = self.app.process_sale.running_total()
        self.sale_total_value.configure(text=str(total))
        self.sale_items_value.configure(text=str(self.app.process_sale.item_count()))
        sale_id = self.app.process_sale.sale_id or "-"
        self.sale_id_label.configure(text=f"Sale:  {sale_id}")

    # =====================================================================
    # Handle Returns tab
    # =====================================================================
    def _build_return_tab(self) -> None:
        tab = self.return_tab
        left = ttk.Frame(tab, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
        right = ttk.Frame(tab, style="Card.TFrame", width=330)
        right.pack(side="right", fill="y", padx=(8, 0), pady=8)
        right.pack_propagate(False)

        ttk.Label(left, text="Original Sale Look-up", style="Head.TLabel"
                  ).pack(anchor="w", padx=14, pady=(12, 4))

        lookup = ttk.Frame(left, style="Card.TFrame")
        lookup.pack(fill="x", padx=14, pady=(0, 8))
        ttk.Label(lookup, text="Receipt / sale id:", style="TLabel").pack(side="left")
        self.return_sale_id = tk.StringVar()
        ttk.Entry(lookup, textvariable=self.return_sale_id, width=14, font=UI
                  ).pack(side="left", padx=8)
        ttk.Button(lookup, text="Open Return", style="Accent.TButton",
                   command=self._return_open).pack(side="left")
        ttk.Button(lookup, text="Return Without Receipt",
                   command=self._return_open_blank).pack(side="left", padx=8)

        self.sale_tree = ttk.Treeview(
            left, columns=("id", "total", "items"), show="headings", height=4)
        for col, title, width in (("id", "Recent Sale", 140),
                                  ("total", "Sale Total", 120),
                                  ("items", "Items", 90)):
            self.sale_tree.heading(col, text=title)
            self.sale_tree.column(col, width=width,
                                  anchor="e" if col != "id" else "w")
        self.sale_tree.pack(fill="x", padx=14, pady=(0, 10))
        self.sale_tree.bind("<Double-1>", self._return_pick_sale)

        ttk.Label(left, text="Items To Return", style="Head.TLabel"
                  ).pack(anchor="w", padx=14, pady=(4, 4))

        entry_row = ttk.Frame(left, style="Card.TFrame")
        entry_row.pack(fill="x", padx=14, pady=(0, 6))
        ttk.Label(entry_row, text="Scan / search:", style="TLabel").pack(side="left")
        self.return_search = tk.StringVar()
        ttk.Entry(entry_row, textvariable=self.return_search, width=24, font=UI
                  ).pack(side="left", padx=8)
        ttk.Label(entry_row, text="Qty:", style="TLabel").pack(side="left", padx=(8, 2))
        self.return_qty = tk.IntVar(value=1)
        ttk.Spinbox(entry_row, from_=1, to=99, width=4,
                    textvariable=self.return_qty).pack(side="left")
        ttk.Button(entry_row, text="Add Return",
                   command=self._return_add).pack(side="left", padx=8)

        self.return_tree = ttk.Treeview(
            left, columns=("id", "description", "qty", "price", "subtotal"),
            show="headings", height=9)
        for col, title, width in (("id", "Item ID", 80),
                                  ("description", "Description", 290),
                                  ("qty", "Qty", 60),
                                  ("price", "Unit Price", 90),
                                  ("subtotal", "Refund", 100)):
            self.return_tree.heading(col, text=title)
            self.return_tree.column(
                col, width=width,
                anchor="e" if col in ("qty", "price", "subtotal") else "w")
        self.return_tree.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # ---- right -------------------------------------------------------
        ttk.Label(right, text="Refund Summary", style="Head.TLabel"
                  ).pack(anchor="w", padx=16, pady=(14, 4))
        self.return_id_label = ttk.Label(right, text="Return:  -",
                                         style="Hint.TLabel")
        self.return_id_label.pack(anchor="w", padx=16)
        self.return_sale_label = ttk.Label(right, text="Original sale:  -",
                                           style="Hint.TLabel")
        self.return_sale_label.pack(anchor="w", padx=16)

        box = ttk.Frame(right, style="Card.TFrame")
        box.pack(fill="x", padx=16, pady=(10, 4))
        ttk.Label(box, text="Items", style="TLabel").grid(row=0, column=0, sticky="w")
        self.return_items_value = ttk.Label(box, text="0", style="Head.TLabel")
        self.return_items_value.grid(row=0, column=1, sticky="e", padx=(60, 0))
        ttk.Label(box, text="REFUND", style="Head.TLabel"
                  ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.return_total_value = ttk.Label(box, text="0.00", style="Big.TLabel")
        self.return_total_value.grid(row=1, column=1, sticky="e", pady=(8, 0))

        opts = ttk.LabelFrame(right, text="Return Options")
        opts.pack(fill="x", padx=16, pady=(14, 6))
        self.return_resellable = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Item is resellable (restock it)",
                        variable=self.return_resellable
                        ).pack(anchor="w", padx=10, pady=(8, 2))
        self.refund_method = tk.StringVar(value="cash")
        ttk.Radiobutton(opts, text="Refund in cash", value="cash",
                        variable=self.refund_method).pack(anchor="w", padx=10)
        ttk.Radiobutton(opts, text="Refund to card", value="card",
                        variable=self.refund_method).pack(anchor="w", padx=10,
                                                          pady=(0, 8))

        actions = ttk.Frame(right, style="Card.TFrame")
        actions.pack(fill="x", padx=16, pady=(6, 4))
        ttk.Button(actions, text="Authorise Refund", style="Accent.TButton",
                   command=self._return_authorise).pack(fill="x", pady=3)
        ttk.Button(actions, text="Remove Selected Line",
                   command=self._return_remove).pack(fill="x", pady=3)
        ttk.Button(actions, text="Cancel Return", style="Danger.TButton",
                   command=self._return_cancel).pack(fill="x", pady=3)

        ttk.Label(right, textvariable=self.returns_status, style="Hint.TLabel",
                  wraplength=290, justify="left"
                  ).pack(anchor="w", padx=16, pady=(8, 0))

    # -- return actions ----------------------------------------------------
    def _refresh_recent_sales(self) -> None:
        self.sale_tree.delete(*self.sale_tree.get_children())
        for sale_id, total, items in self.app.handle_returns.recent_sales(8):
            self.sale_tree.insert("", "end", values=(sale_id, total, items))

    def _return_pick_sale(self, _event=None) -> None:
        selected = self.sale_tree.selection()
        if selected:
            self.return_sale_id.set(str(self.sale_tree.item(selected[0])["values"][0]))
            self._return_open()

    def _return_open(self) -> None:
        sale_id = self.return_sale_id.get().strip()
        try:
            return_id = self.app.handle_returns.make_new_return(sale_id)
        except TransactionError as exc:
            messagebox.showerror("Handle Returns", str(exc), parent=self.root)
            self._say(str(exc), "error")
            return
        self._refresh_return()
        self._say(f"Opened {return_id}"
                  + (f" against sale {sale_id}." if sale_id else "."), "ok")

    def _return_open_blank(self) -> None:
        self.return_sale_id.set("")
        try:
            return_id = self.app.handle_returns.make_new_return("")
        except TransactionError as exc:
            self._say(str(exc), "error")
            return
        self._refresh_return()
        self._say(f"Opened {return_id} (no original receipt).", "warn")

    def _return_add(self) -> None:
        item_id = self.return_search.get().strip()
        if not item_id:
            self._say("Enter an item id to return.", "warn")
            return
        if not self.app.handle_returns.is_return_in_progress:
            self._return_open_blank()
        try:
            quantity = int(self.return_qty.get())
        except (tk.TclError, ValueError):
            quantity = 1
        try:
            self.app.handle_returns.enter_return_item(
                item_id, quantity, resellable=self.return_resellable.get())
        except TransactionError as exc:
            messagebox.showerror("Handle Returns", str(exc), parent=self.root)
            self._say(str(exc), "error")
            return
        self.return_search.set("")
        self.return_qty.set(1)
        self._refresh_return()
        self._say(f"Returning {item_id} x{quantity}.", "ok")

    def _return_remove(self) -> None:
        selected = self.return_tree.selection()
        if not selected:
            self._say("Select a return line to remove.", "warn")
            return
        item_id = str(self.return_tree.item(selected[0])["values"][0])
        ret = self.app.register.current_return
        if ret is not None:
            ret.remove_line_item(item_id)
        self._refresh_return()

    def _return_cancel(self) -> None:
        self.app.handle_returns.cancel_transaction()
        self._refresh_return()
        self._refresh_stock()
        self._say("Return cancelled.", "warn")

    def _return_authorise(self) -> None:
        if not self.app.handle_returns.is_return_in_progress:
            self._say("Open a return first.", "warn")
            return
        method = self.refund_method.get()
        try:
            self.app.handle_returns.authorize_refund(method)
            result = self.app.handle_returns.end_return()
        except TransactionError as exc:
            messagebox.showerror("Handle Returns", str(exc), parent=self.root)
            self._say(str(exc), "error")
            return
        self._refresh_return()
        self._refresh_stock()
        self._refresh_recent_sales()
        self._show_receipt("Refund Receipt", result.receipt_text)
        self._say(f"Refunded {result.refund_total} via {result.method} "
                  f"(return {result.return_id}).", "ok")

    def _refresh_return(self) -> None:
        self.return_tree.delete(*self.return_tree.get_children())
        for line in self.app.handle_returns.line_items():
            self.return_tree.insert(
                "", "end",
                values=(line.item_id, line.description, line.quantity,
                        line.unit_price, line.subtotal))
        self.return_total_value.configure(
            text=str(self.app.handle_returns.refund_total()))
        self.return_items_value.configure(
            text=str(sum(li.quantity
                         for li in self.app.handle_returns.line_items())))
        self.return_id_label.configure(
            text=f"Return:  {self.app.handle_returns.return_id or '-'}")
        self.return_sale_label.configure(
            text=f"Original sale:  "
                 f"{self.app.handle_returns.original_sale_id or '-'}")

    # =====================================================================
    # Store Status tab
    # =====================================================================
    def _build_status_tab(self) -> None:
        tab = self.status_tab
        wrap = ttk.Frame(tab, style="Card.TFrame")
        wrap.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Label(wrap, text="Store Status", style="Head.TLabel"
                  ).pack(anchor="w", padx=14, pady=(12, 6))

        self.summary_label = ttk.Label(wrap, text="", style="TLabel")
        self.summary_label.pack(anchor="w", padx=14, pady=(0, 10))

        panes = ttk.Frame(wrap, style="Card.TFrame")
        panes.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        stock_box = ttk.LabelFrame(panes, text="Stock on hand")
        stock_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.stock_tree = ttk.Treeview(stock_box, columns=("id", "level"),
                                       show="headings", height=12)
        self.stock_tree.heading("id", text="Item ID")
        self.stock_tree.heading("level", text="On hand")
        self.stock_tree.column("id", width=110)
        self.stock_tree.column("level", width=90, anchor="e")
        self.stock_tree.pack(fill="both", expand=True, padx=8, pady=8)

        audit_box = ttk.LabelFrame(panes, text="Audit trail (system operations)")
        audit_box.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self.audit_tree = ttk.Treeview(
            audit_box, columns=("time", "operation", "detail"),
            show="headings", height=12)
        self.audit_tree.heading("time", text="Time")
        self.audit_tree.heading("operation", text="Operation")
        self.audit_tree.heading("detail", text="Detail")
        self.audit_tree.column("time", width=80)
        self.audit_tree.column("operation", width=130)
        self.audit_tree.column("detail", width=320)
        self.audit_tree.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Button(wrap, text="Refresh", command=self._refresh_stock
                   ).pack(anchor="e", padx=14, pady=(0, 12))

    def _refresh_stock(self) -> None:
        self.stock_tree.delete(*self.stock_tree.get_children())
        for item_id, level in self.app.stock_snapshot().items():
            self.stock_tree.insert("", "end", values=(item_id, level))
        self.audit_tree.delete(*self.audit_tree.get_children())
        for entry in self.app.audit.recent(18):
            self.audit_tree.insert(
                "", "end",
                values=(f"{entry.when:%H:%M:%S}", entry.operation,
                        f"[{entry.outcome}] {entry.detail}"))
        summary = self.app.sales_summary()
        self.summary_label.configure(
            text=(f"Completed sales: {summary['sales']}     "
                  f"Revenue: {summary['revenue']}     "
                  f"Returns: {summary['returns']}     "
                  f"Refunded: {summary['refunded']}"))

    # =====================================================================
    # receipt dialog
    # =====================================================================
    def _show_receipt(self, title: str, text: str) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=PANEL)
        win.geometry("480x560")
        win.transient(self.root)
        ttk.Label(win, text=title, style="Head.TLabel"
                  ).pack(anchor="w", padx=16, pady=(14, 8))
        frame = tk.Frame(win, bg=PANEL)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        scroll = tk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        widget = tk.Text(frame, font=MONO, bg="#FBFCFD", fg=INK,
                         relief="solid", borderwidth=1, wrap="none",
                         yscrollcommand=scroll.set)
        widget.pack(fill="both", expand=True)
        scroll.configure(command=widget.yview)
        widget.insert("1.0", text)
        widget.configure(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy
                   ).pack(anchor="e", padx=16, pady=(0, 14))

    # =====================================================================
    # automation hooks (used by the report's screenshot script)
    # =====================================================================
    def select_tab(self, index: int) -> None:
        """Programmatically switch tabs (for scripted screenshots)."""
        self.tabs.select(index)
        self.root.update_idletasks()
        self.root.update()

    def run(self) -> None:
        """Enter the Tk main loop (blocks until the window is closed)."""
        if self._owns_root:
            self.root.mainloop()

    def destroy(self) -> None:
        self.root.destroy()

    # -- scripted scenarios ------------------------------------------------
    def demo_process_sale(self, items=(("1001", 2), ("1005", 1), ("1008", 3)),
                          tendered: str = "30.00") -> None:
        """Drive a complete Process Sale through the UI for the report."""
        self.select_tab(0)
        self._sale_new()
        self.return_resellable.set(True)
        for item_id, quantity in items:
            self.sale_search.set(item_id)
            self.sale_qty.set(quantity)
            self._sale_scan()
        self.pay_kind.set("cash")
        self.tendered.set(tendered)
        self.root.update_idletasks()
        self.root.update()

    def demo_handle_returns(self, items=(("1001", 1),), method: str = "card",
                            resellable: bool = True) -> None:
        """Drive a complete Handle Returns through the UI for the report."""
        self.select_tab(1)
        self.return_resellable.set(resellable)
        self.refund_method.set(method)
        recent = self.app.handle_returns.recent_sales(1)
        if recent:
            self.return_sale_id.set(recent[0][0])
            self._return_open()
        for item_id, quantity in items:
            self.return_search.set(item_id)
            self.return_qty.set(quantity)
            self._return_add()
        self.root.update_idletasks()
        self.root.update()


def launch(gateway_kind: str = "simulated") -> None:
    """Build the application and show the window."""
    from ..application.pos_application import build_application

    app = build_application(gateway_kind=gateway_kind)
    window = POSWindow(app)
    window.run()
