# User Manual - NextGen POS

How to operate the till.  Written for the cashier; the two required use cases
are **Process Sale** and **Handle Returns**.

---

## 1. Starting the terminal

```bash
cd ProjectPos_2026
export PYTHONPATH=src
python -m pos
```

The window opens on the **Process Sale** tab.  There are three tabs:

| Tab | Used for |
|---|---|
| **Process Sale** | serving the next customer |
| **Handle Returns** | taking goods back and refunding |
| **Store Status** | checking stock, the day's takings and the audit trail |

## 2. Process Sale

### 2.1 Before you scan anything

Press **New Sale**. The Sale Summary panel on the right shows a new sale id
(for example `S000001`) and the total resets to `0.00`. Until you press
**New Sale**, scanning does nothing and the terminal tells you so in the status
bar at the bottom.

### 2.2 Scanning items

1. Type or scan the item id into **Scan / search**.
2. Set **Qty** if the customer has more than one.
3. Press **Enter** or click **Add Item**.

The item appears in the **Current Sale** list with its description, quantity,
unit price and subtotal, and the running **TOTAL** updates immediately.

You can also double-click a row in the **Product Catalogue** to add that
product with the current quantity.

**Scanning the same item twice is safe.** It merges into one line and
increases the quantity rather than creating a duplicate row.

### 2.3 Mistakes

* **Wrong item** - click the line in **Current Sale** and press **Remove
  Selected Line**. The total updates.
* **Wrong customer / start over** - press **Cancel Sale**. The sale is
  abandoned and **stock is not affected**.
* **Item not in the catalogue** - the terminal refuses the scan and says so.
  Nothing is added.
* **Not enough stock** - the terminal refuses and tells you how many are left.

### 2.4 Taking payment

Choose the payment method in the **Payment** panel.

**Cash**

1. Select **Cash**.
2. Type what the customer handed over into **Cash tendered** (for example
   `30.00`). You may leave it blank if they tendered exactly the total.
3. Press **Pay & Print Receipt**.

The receipt dialog shows the tendered amount and the **change due**. If the
customer handed over less than the total, the payment is refused and the sale
stays open so you can try again.

**Credit card**

1. Select **Credit card**.
2. Enter the card number. For the demonstration terminal:
   * any number starting `4111` is **approved**;
   * any number starting `4000` is **declined**;
   * any number starting `4444` or `5000` makes the service **time out**.
3. Press **Pay & Print Receipt**.

If the card is declined the terminal shows the reason, **the sale stays open
and stock is untouched** - take another payment method or cancel the sale.
That is deliberate: inventory only moves once money is authorised.

### 2.5 After payment

The receipt appears in a dialog and can be copied. Stock for every line has
already been reduced; check the **Store Status** tab if you want to see it.

The Sale Summary panel resets. Press **New Sale** for the next customer.

## 3. Handle Returns

### 3.1 Finding the original sale

If the customer has their receipt:

1. Go to the **Handle Returns** tab.
2. The **Recent Sale** list shows the most recent completed sales in this
   session, with their totals.
3. Either double-click the right row, or type the receipt number into
   **Receipt / sale id** and press **Open Return**.

If the customer has **no receipt**, press **Return Without Receipt**. You can
still record the return and refund; it simply is not linked to an original
sale.

### 3.2 Entering the returned goods

1. Type the item id into **Scan / search** and set **Qty**.
2. Decide whether the item is resellable:
   * **tick** *Item is resellable* for undamaged goods that go back on the
     shelf;
   * **untick** it for damaged goods, which are refunded but **not** restocked.
3. Press **Add Return**.

The **Items To Return** list builds up and **REFUND** shows the amount due.

The terminal enforces two rules and will refuse the entry with an explanation:

* you cannot return an item that was **not on that receipt**;
* you cannot return **more units than were sold**.

### 3.3 Paying the refund

Choose **Refund in cash** or **Refund to card**, then press **Authorise
Refund**.

A **REFUND RECEIPT** dialog appears showing the returned lines, the total, the
refund method and the original sale id. If any lines were damaged, the receipt
states how many units were written off rather than restocked.

Press **Cancel Return** to abandon a return without refunding anything - stock
is unaffected.

## 4. Store Status

| Panel | Shows |
|---|---|
| Summary line | completed sales, revenue, number of returns, total refunded |
| Stock on hand | every item and its current level |
| Audit trail | every system operation with its time, name, outcome and detail |

Press **Refresh** after trading to bring the stock and audit figures up to
date. The audit trail is the place to look when the till and the shelf
disagree: it records failed and rejected operations too, not only the
successful ones.

## 5. Text-mode terminal

On a machine without a display, or for scripted operation:

```bash
python -m pos --terminal
```

The same two use cases are available through a numbered menu. Behaviour and
rules are identical because it is the same application layer underneath.

For a completely scripted run that prints receipts and the resulting stock
levels:

```bash
python -m pos --headless-demo
```

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "No sale in progress - press 'New Sale' first." | You scanned before starting a sale. Press **New Sale**. |
| "Item 9999 is not in the catalogue." | Wrong id, or the product is not stocked. Check the Product Catalogue list. |
| "Only 3 unit(s) of 1001 in stock." | The shelf cannot cover the quantity. Reduce it or restock. |
| "Payment declined: card declined: CARD DECLINED BY ISSUER" | The card was refused. Take another payment method. The sale is still open. |
| "authorisation service timeout" | The card service is unreachable. Retry, or take cash. The sale is still open. |
| "cannot return 3 of 1001: only 2 were sold on S000001" | The return exceeds the receipt. Check the quantity with the customer. |
| "1001 was not part of sale S000001" | That item is not on the receipt being used. |
| Change is refused as "tendered 5.00 is less than amount due 9.00" | The cash handed over is short. |
| The window will not open | Tk is unavailable. Use `--terminal`, which needs no display. |
