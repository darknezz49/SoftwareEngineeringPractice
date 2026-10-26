# Architecture

This document records the logical architecture of the POS system and, more
importantly, the **rule** that keeps it a layered architecture rather than a
set of folders that happen to have layer-like names.

---

## 1. The four layers

| Layer | Package | Responsibility | May depend on |
|---|---|---|---|
| **Presentation** | `pos.presentation` | Windows, widgets, keyboard/mouse events, formatting, terminal I/O. No business rules. | Application |
| **Application** | `pos.application` | One controller per use case. Owns the *sequence* of a use case and the cross-cutting audit log. Returns flat view objects. | Domain, Technical |
| **Domain** | `pos.domain` | The conceptual classes of the problem domain and the business rules that concern them. | Technical (interfaces only) |
| **Technical Services** | `pos.technical` | Payment gateways and their adapters, repositories, the audit log, seed data. | Domain types (Money, Sale) |

The dependency direction is **downward only**. A higher layer may call a lower
one; a lower one never calls upward.

## 2. The rule is enforced, not just documented

The claim "we have a layered architecture" is worth nothing unless it can be
checked. Two checks back it up.

**a) Nothing in `pos.domain` imports a higher layer.** The domain's own
`__init__.py` states it, and it is a one-line check:

```bash
grep -rn "from \.\.\(presentation\|application\|technical\)" src/pos/domain/
# expected output: (nothing)
grep -rn "import tkinter" src/pos/domain/
# expected output: (nothing)
```

**b) A second presentation layer was added without touching the domain.**
`pos/presentation/terminal.py` is a complete, working text-mode POS UI. It was
written after the Tk GUI and required **zero** changes to `pos.domain` or
`pos.application`. That is the practical test of Model-View Separation: if a
new view needs changes in the model, the separation was not real.

## 3. Where the dependency is inverted

The domain must not depend on a particular bank. The chain is:

```
domain.Payment / PaymentFactory
        |
        |  depends on the *interface* only
        v
technical.payment_gateway.PaymentGateway          <-- the port
        ^
        |  implements
        |
technical.payment_adapters.LegacyTerminalAdapter
technical.payment_adapters.SoapServiceAdapter
technical.payment_adapters.SimulatedBankAdapter
```

`build_application(gateway_kind=...)` is the single **composition root**: the
only place that names a concrete adapter and hands it to the domain. Changing
`gateway_kind` from `"legacy"` to `"soap"` changes which bank the shop talks to
and changes nothing else.

## 4. Packages inside a layer

```
pos.presentation     gui.py        Tk window (POSWindow)
                    terminal.py   text-mode view (TerminalPOS)

pos.application     pos_application.py   ProcessSaleController,
                                          HandleReturnsController,
                                          POSApplication, build_application

pos.domain          money.py      Money
                    items.py      ItemID, SalesLineItem, ReturnLineItem
                    catalog.py    ProductSpecification, ProductCatalog
                    inventory.py  InventoryService
                    sale.py       Sale, SaleState
                    returns.py    ReturnTransaction, ReturnState
                    payment.py    Payment, CashPayment, CreditPayment,
                                  PaymentFactory
                    receipt.py    Receipt (report object)
                    register.py   Register (facade controller)
                    people.py     Cashier, Customer, Store

pos.technical       payment_gateway.py   PaymentGateway, RefundGateway,
                                         SimulatedBankGateway
                    payment_adapters.py  the three adapters and the factory
                    repositories.py      SaleRepository, ReturnRepository
                    store_data.py        AuditLog and the demo shop
```

## 5. Layer-by-layer design notes

### 5.1 Domain

The domain is the only layer allowed to contain business rules. Every rule that
matters lives here, which is why the tests for those rules need no UI:

* `Money` refuses `float` and quantises to two decimal places with
  `ROUND_HALF_UP`.
* `Sale.make_payment` refuses an empty sale, refuses a second payment, and
  requires the payment to cover the total.
* `Sale.make_line_item` raises once the sale has been paid.
* `ReturnTransaction.authorize_refund` refuses an empty return and refuses to
  refund more than the original sale was worth.
* `InventoryService.remove` refuses an oversell and names the numbers involved.

### 5.2 Application

A controller per use case, named `<UseCase>Controller` (the GRASP **Controller**
pattern). The controllers do three things and no more:

1. own the order of the system operations from the use case's SSD,
2. apply the cross-cutting concern (writing to the audit log),
3. translate a domain exception into a `TransactionError` that a UI can show.

They return **view objects** (`LineItemView`, `SaleResult`, `RefundResult`),
never live domain objects. That keeps the coupling between UI and domain at
"strings and numbers".

### 5.3 Presentation

`gui.py` and `terminal.py` are interchangeable. Both build widgets or prompts
and then delegate immediately. Neither contains a single arithmetic operation
on money.

### 5.4 Technical Services

The adapters are the interesting part; see
[`../docs/diagrams/07-design-class-diagram.puml`](diagrams/07-design-class-diagram.puml)
and the Adapter tests in `tests/test_technical.py`.

A repository hides the store. Today `SaleRepository` is a dictionary; swapping
in SQLite would touch this package and nothing else. That is the point of the
seam.

## 6. Sequence of a Process Sale, layer by layer

```
POSWindow            ProcessSaleController        Register        Sale        InventoryService
    |                        |                       |              |                |
    |-- enter_item(id,2) --->|                       |              |                |
    |                        |-- enter_item -------->|              |                |
    |                        |                       |-- is_available --------------->|
    |                        |                       |-- make_line_item ------------>|
    |                        |                       |              |<- «create» ----|
    |                        |<- SalesLineItem ------|              |                |
    |<- LineItemView --------|                       |              |                |
    |                        |                       |              |                |
    |-- make_payment(cash) ->|                       |              |                |
    |                        |-- make_payment ------>|              |                |
    |                        |                       |-- make_payment -------------->|
    |                        |                       |              |-- authorize()  |
    |                        |                       |-- remove(id, 2) -------------->|
    |                        |-- end_sale ---------->|              |                |
    |<- SaleResult ----------|                       |              |                |
```

Nothing in the right-hand half of that picture knows a window exists.

## 7. Testing strategy

| Level | File | What it pins down |
|---|---|---|
| Unit - value objects | `test_domain.py` | exact decimal money, no floats |
| Unit - domain rules | `test_domain.py` | totals, state machine, payment and refund policy |
| Integration - use cases | `test_use_cases.py` | both SSDs end to end, including inventory effects |
| Integration - ports | `test_technical.py` | three adapters behind one interface, the factory, repositories, audit |

Run them with:

```bash
PYTHONPATH=src python -m pytest -q      # 90 passed
```

## 8. Known limitations

* Persistence is in-memory; the repositories are the seam where a database
  would go.
* The card gateways are simulated; the adapters are real in structure but the
  far end is in-process.
* Tax rates are carried on `ProductSpecification` but no tax is computed on the
  receipt. The assignment's use cases do not require it.
* The Tk window could not be captured as a screenshot in the build
  environment (no Screen Recording permission), so `docs/make_figures.py`
  documents behaviour using transcripts of the real text-mode application.
