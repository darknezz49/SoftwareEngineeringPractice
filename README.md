# ProjectPos_2026 - NextGen POS

Repository: <https://github.com/darknezz49/SoftwareEngineeringPractice>

A point-of-sale system for a small supermarket, built with object-oriented
analysis and design techniques as required by the *Software Engineering
Practice* assignment (PoS System Using Agile).

The system implements the two required use cases:

| Use case | What it does |
|---|---|
| **Process Sale** | Records each purchased item, shows a running total and line-item detail, takes payment (cash or card), updates inventory and prints a receipt. |
| **Handle Returns** | Looks up the original sale, records returned items (marking damaged goods as not resellable), updates inventory and prints a refund receipt. |

---

## 1. Quick start

Requires **Python 3.10 or newer** (no third-party packages are needed to run
the application - only the standard library).

```bash
cd ProjectPos_2026
export PYTHONPATH=src           # Windows: set PYTHONPATH=src

python -m pos                   # launch the graphical POS terminal
python -m pos --terminal        # text-mode POS terminal
python -m pos --headless-demo   # scripted sale + return, prints receipts
```

Other options:

```bash
python -m pos --gateway legacy  # use the legacy terminal card adapter
python -m pos --gateway soap    # use the SOAP service card adapter
python -m pos --gateway simulated   # default, in-process simulator
```

## 2. Running the tests

The project is developed test-first.  The suite covers the domain rules, both
use cases and every adapter:

```bash
pip install pytest
PYTHONPATH=src python -m pytest -q
```

Expected result: **90 passed**.

## 3. Project layout

```
ProjectPos_2026/
├── src/pos/                  the application
│   ├── domain/               conceptual classes + business logic
│   ├── application/          one controller per use case
│   ├── presentation/         the GUI and the text-mode view
│   └── technical/            gateways/adapters, repositories, audit log
├── tests/                    the automated test suite
├── docs/
│   ├── diagrams/             UML sources (.puml) and rendered images
│   ├── screenshots/          figures used in the report
│   ├── USER_MANUAL.md        how to operate the till
│   ├── ARCHITECTURE.md       the logical architecture and its rules
│   ├── GIT_WORKFLOW.md       branching model and the command history
│   ├── agile/                Part 1 working notes
│   ├── capture_screenshots.py
│   ├── make_figures.py       regenerates the report figures
│   └── make_agile_workbook.py  regenerates the Part 1 workbook
└── README.md
```

## 4. Architecture in one paragraph

The code is organised into four layers, and the dependency rule is that a
higher layer may call a lower one but never the reverse.  `presentation`
contains only widgets and event handlers and delegates every decision to
`application`; `application` holds one controller per use case and coordinates
the work; `domain` holds the conceptual classes (`Sale`, `SalesLineItem`,
`Payment`, `ProductSpecification`, `ReturnTransaction`, ...) and owns the
business rules; `technical` holds the payment gateways and their adapters, the
repositories and the audit log.  **Nothing in `pos.domain` imports anything
from `pos.presentation`, `pos.application` or `pos.technical`** - the domain
depends only on the `PaymentGateway` interface, and the concrete adapter is
injected by the composition root in `build_application()`.  See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 5. Design patterns used

| Pattern | Where | Why |
|---|---|---|
| **Creator** (GRASP) | `Register` creates `Sale`; `Sale` creates `SalesLineItem` | the creator is already connected to the created object, which supports low coupling |
| **Information Expert** (GRASP) | `Sale.get_total`, `SalesLineItem.get_subtotal` | the class that has the data does the work |
| **Controller** (GRASP) | `Register` (facade), `ProcessSaleController`, `HandleReturnsController` | one entry point per system operation, beyond the UI layer |
| **Low Coupling / High Cohesion** | layered packages | each module has one reason to change |
| **Adapter** (GoF) | `LegacyTerminalAdapter`, `SoapServiceAdapter` | two incompatible third-party card interfaces are usable through one port |
| **Factory** (GoF) | `PaymentFactory`, `PaymentGatewayFactory` | creation logic is separated and hidden, and the concrete class is chosen from configuration |
| **Protected Variations** | the `PaymentGateway` port | a new bank means a new adapter, not a change to any caller |
| **Model-View Separation** | both presentation views | the domain knows nothing about the UI, which is why a second view was possible with no domain change |
| **Pure Fabrication** | the factories, `AuditLog`, repositories | behaviour given to a made-up class to preserve cohesion |

## 6. Money is never a float

`pos.domain.money.Money` wraps `decimal.Decimal` and **refuses to accept a
Python `float`**, precisely because binary floating point cannot represent
0.10.  This is the single most common defect in POS software, and the test
suite asserts the rule:

```python
Money(4.50)              # TypeError - use a str or Decimal
Money("0.10") + Money("0.20") == Money("0.30")    # True, exactly
```

## 7. Documentation

* [docs/USER_MANUAL.md](docs/USER_MANUAL.md) - operating the till, screen by screen
* [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - layers, packages and the dependency rule
* [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) - branching model and commit history
* [docs/diagrams/](docs/diagrams) - all UML models with their PlantUML sources

## 8. Screenshots and figures

Two independent sets of figures are generated from the real application, never
drawn by hand:

* `docs/capture_screenshots.py` drives the Tk window through scripted
  scenarios and captures each frame with `screencapture` (macOS Screen
  Recording permission required). These are the report's screenshots.
* `docs/make_figures.py` drives the text-mode view and renders the transcripts.
  These are the evidence that the same use cases run with no display.

```bash
python docs/capture_screenshots.py     # window screenshots
python docs/make_figures.py            # terminal transcripts
```
