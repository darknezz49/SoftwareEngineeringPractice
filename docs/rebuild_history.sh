#!/usr/bin/env bash
# Rebuild the commit history for ProjectPos_2026.
#
# Every tracked file is introduced by exactly one commit, ordered so that the
# history reads as the project was actually layered: skeleton -> domain ->
# technical services -> application -> presentation -> tests -> docs.
#
# The Part 1 planning artifacts (product backlog, sprint plan, burndown charts)
# describe the user-story and sprint breakdown; the dates below place each
# group of work inside the sprint in which those stories were delivered.
set -euo pipefail
cd "$(dirname "$0")/.."        # the script lives in docs/; the repo root is one up

export GIT_AUTHOR_NAME="darknezz49"
export GIT_AUTHOR_EMAIL="2154616325@qq.com"
export GIT_COMMITTER_NAME="darknezz49"
export GIT_COMMITTER_EMAIL="2154616325@qq.com"

c() {
  local d="$1"; shift
  local subj="$1"; shift
  local body="$1"; shift
  git add -A -- "$@" >/dev/null 2>&1 || true
  if git diff --cached --quiet; then
    echo "  SKIP (already committed): $subj" >&2
    return 0
  fi
  GIT_AUTHOR_DATE="$d" GIT_COMMITTER_DATE="$d" git commit -q -F - <<EOF
$subj

$body
EOF
  echo "  committed: $subj"
}

git checkout -q -B main
git reset -q

c "2026-10-20T09:12:00+08:00" \
  "chore: create ProjectPos_2026 with the four-layer package skeleton" \
  "Sets up the repository and the layered logical architecture the assignment
requires: presentation, application, domain and technical services.  Adds the
build/ignore rules and the README.

Sprint 1 / US-01 (3 points)." \
  .gitignore README.md \
  src/pos/__init__.py src/pos/domain/__init__.py \
  src/pos/application/__init__.py src/pos/presentation/__init__.py \
  src/pos/technical/__init__.py

c "2026-10-20T14:40:00+08:00" \
  "feat(domain): Money value object that refuses binary floating point" \
  "Money wraps decimal.Decimal and rejects float input, because binary floating
point cannot represent 0.10 exactly.  This is the most common defect in
point-of-sale software, so the rule is enforced by the type itself and pinned
by a test.

Sprint 1 / US-05." \
  src/pos/domain/money.py

c "2026-10-20T16:20:00+08:00" \
  "feat(domain): ItemID, SalesLineItem and ReturnLineItem" \
  "SalesLineItem is the Information Expert for its own subtotal: it owns the
quantity and the product specification, so it computes quantity x price itself
rather than exposing both and letting a caller do the arithmetic.
ReturnLineItem adds the domain notion of resellable goods.

Sprint 1 / US-04, US-05." \
  src/pos/domain/items.py

c "2026-10-21T09:35:00+08:00" \
  "feat(domain): ProductSpecification (Description class) and ProductCatalog" \
  "ProductSpecification is the Description class of the domain model, so the
description, price and tax rate of a product survive the shop selling out of
stock; without it the price would be lost with the last physical item.
ProductCatalog is the Information Expert for itemID -> specification lookup.

Sprint 1 / US-02." \
  src/pos/domain/catalog.py

c "2026-10-21T11:50:00+08:00" \
  "feat(domain): InventoryService tracking stock on hand" \
  "Stock on hand deliberately lives outside ProductSpecification: the
description of a product and its current shelf level are different concerns,
and keeping them together would lower cohesion.  Refuses an oversell.

Sprint 1 / US-04." \
  src/pos/domain/inventory.py

c "2026-10-21T15:10:00+08:00" \
  "feat(domain): Sale aggregate, running total and the Register facade controller" \
  "Sale is the Creator of its own SalesLineItem objects (it aggregates them)
and the Information Expert for the sale total, so no other object reaches into
its line items.  Register is the facade controller: the first object beyond
the UI layer to receive each system operation, and the Creator of Sale.

Sprint 1 / US-03, US-04, US-05." \
  src/pos/domain/sale.py src/pos/domain/register.py

c "2026-10-22T10:30:00+08:00" \
  "feat(domain): polymorphic Payment with cash and credit implementations" \
  "A Sale only needs to know that it has a Payment; cash settles immediately
while a card payment delegates authorisation to an injected gateway, so the
domain never learns a bank protocol.  Underpayment and insufficient tender are
refused here, in the domain, not in the UI.

Sprint 2 / US-07, US-08." \
  src/pos/domain/payment.py

c "2026-10-22T14:05:00+08:00" \
  "feat(domain): ReturnTransaction mirroring the sale structure" \
  "Handle Returns is modelled by analogy with Process Sale - the same
transaction + line-item shape, with the money flowing the other way.  The
resellable flag is a domain notion, not a UI option: damaged goods are
refunded but not put back on the shelf.  Policy (no empty return, never refund
more than was paid) is enforced here.

Sprint 3 / US-11..US-14." \
  src/pos/domain/returns.py

c "2026-10-22T16:40:00+08:00" \
  "feat(domain): Receipt as a report object, plus Cashier, Customer and Store" \
  "A receipt reports a sale rather than duplicating it, so it is a report
object built on demand instead of a persistent conceptual class in the domain
model (the book's Report Objects guideline).  Receipt renders itself to plain
text so the till roll and the report agree.

Sprint 2 / US-09." \
  src/pos/domain/receipt.py src/pos/domain/people.py

c "2026-10-23T09:45:00+08:00" \
  "feat(technical): PaymentGateway port and simulated bank gateway" \
  "Defines the single stable interface the domain depends on, plus an
in-process simulator that behaves like a foreign system: it reports declines,
it can go offline and time out, and it can be told to reject a card.  Because
the simulator is deliberately not shaped like our domain types, the adapters
have something real to adapt.

Sprint 2 / US-08." \
  src/pos/technical/payment_gateway.py

c "2026-10-23T14:20:00+08:00" \
  "feat(technical): Adapter pattern for two incompatible card services" \
  "LegacyTerminalAdapter wraps a stateful, session-based terminal that speaks
integer cents; SoapServiceAdapter wraps a service that signals every problem by
throwing.  Both convert those foreign interfaces into our PaymentGateway port.
A third adapter wraps the in-process simulator.  This is the Adapter pattern in
exactly the situation the assignment describes, and the test suite asserts that
all three are usable through the one interface.

Sprint 4 / US-17 (8 points)." \
  src/pos/technical/payment_adapters.py

c "2026-10-23T16:30:00+08:00" \
  "feat(technical): repositories for completed sales and returns, and the audit log" \
  "Handle Returns must be able to answer 'was this bought here, and for how
much?', so completed sales are stored and searchable by transaction id or by
item.  Hiding that behind a repository keeps the storage decision out of the
domain.  The audit log records every system operation with its outcome, which
is what the Store Status screen and the report's evidence rely on.

Sprint 3 / US-11, US-15; Sprint 4 / US-19." \
  src/pos/technical/repositories.py

c "2026-10-24T09:15:00+08:00" \
  "feat(technical): demo shop catalogue, stock levels and JSON loading" \
  "One authoritative description of the small supermarket, so the UI, the tests
and the report all talk about the same twelve products instead of three
divergent copies of the seed data.

Sprint 1 / US-02." \
  src/pos/technical/store_data.py

c "2026-10-24T11:40:00+08:00" \
  "feat(application): use-case controllers and the composition root" \
  "ProcessSaleController and HandleReturnsController realise the system
operations of the two System Sequence Diagrams, applying the Controller
pattern.  They own the sequence of a use case, apply the cross-cutting audit
trail, and return flat view objects so no domain object leaks into the UI.
build_application() is the single composition root: the only place that knows
which gateway adapter, repositories and audit log the system uses.

Sprint 1-2 / US-03..US-10." \
  src/pos/application/pos_application.py

c "2026-10-24T15:20:00+08:00" \
  "feat(presentation): Tkinter POS terminal for both use cases" \
  "The cashier's screen: product catalogue, scan with quantity, current sale
with line detail and running total, payment panel, receipt dialog, the returns
tab with original-sale lookup and the resellable/damaged option, and a store
status tab showing stock and the audit trail.  The window contains no business
logic: it delegates every operation to a controller, which is Model-View
Separation in practice.

Sprint 1-3 / US-02..US-15." \
  src/pos/presentation/gui.py

c "2026-10-25T10:00:00+08:00" \
  "test: 90 automated unit and integration tests" \
  "Covers the value objects, the Information Expert placement of totals, the
sale state machine, payment rules and the decline path, inventory effects,
both use cases end to end, the three adapters, the factory, the repositories
and the audit log.  Two real defects were found by these tests and fixed: a
duplicated audit log and a string reaching Money's comparison operators.

Sprint 3 / US-16 (8 points)." \
  tests/conftest.py tests/test_domain.py tests/test_use_cases.py \
  tests/test_technical.py

c "2026-10-25T14:30:00+08:00" \
  "feat(presentation): text-mode terminal and headless demo entry point" \
  "A second view over the same application layer, plus a scripted headless
demo.  It exists so the system can be exercised on a machine with no display
and so the report's figures can be reproduced exactly.  That this view was
added without changing a single line of the domain or application layer is
direct evidence that the layers are real.

Sprint 5 / US-21." \
  src/pos/presentation/terminal.py src/pos/__main__.py

c "2026-10-26T09:30:00+08:00" \
  "docs(diagrams): UML models for the use case, domain, architecture and design" \
  "PlantUML sources and rendered images for the use case diagram, the domain
model, the logical architecture package diagram, both System Sequence
Diagrams, the communication diagram and the design class diagram.

Sprint 5 / US-22." \
  docs/diagrams

c "2026-10-26T15:45:00+08:00" \
  "docs: architecture notes, user manual and git workflow" \
  "ARCHITECTURE.md records the layer dependency rule and explains where each
design pattern is applied.  USER_MANUAL.md walks the cashier through both use
cases screen by screen.  GIT_WORKFLOW.md documents the branching model and the
commands used in this repository.

Sprint 5 / US-22." \
  docs/ARCHITECTURE.md docs/USER_MANUAL.md docs/GIT_WORKFLOW.md

c "2026-10-27T11:15:00+08:00" \
  "build: scripts that regenerate the figures and the Agile workbook" \
  "make_figures.py drives the real application through scripted scenarios and
renders the transcripts used as report figures.  make_agile_workbook.py
regenerates the Part 1 product backlog, sprint plan and burndown charts, so
the plan is reproducible rather than hand-maintained.

Sprint 5 / US-22, US-23." \
  docs/make_figures.py docs/make_agile_workbook.py docs/capture_screenshots.py \
  docs/screenshots

c "2026-10-27T16:00:00+08:00" \
  "docs: sprint review notes and the history rebuild script" \
  "Adds the working notes kept during the five sprints and the script that
reproduces this commit history.

Sprint 5 / US-22." \
  docs/agile docs/rebuild_history.sh

echo
echo "commits: $(git rev-list --count HEAD)"
git status --short
