# Figure captions

**Process Sale - text-mode POS terminal** (`fig-01-process-sale.png`)

The cashier scans three products, the running total and line-item detail build up, then payment is taken in cash and change is given.

**Handle Returns - text-mode POS terminal** (`fig-02-handle-returns.png`)

A return is opened against receipt S000001 (issued in figure 1), one unit comes back resellable and two units damaged, and the refund goes back to the card.

**Store Status after both use cases have run** (`fig-03-store-status.png`)

Stock levels after the sale and the return, plus the audit trail of system operations the two controllers recorded.

**Credit payment declined by the issuing bank** (`fig-04-declined-card.png`)

The Adapter reports the decline, the sale stays open and inventory is untouched - the 'reimbursement rejected' alternate scenario from the fully dressed use case.
