# Git workflow and command history

## 1. The repository

| Item | Value |
|---|---|
| Project name | `ProjectPos_2026` |
| Remote repository | https://github.com/darknezz49/SoftwareEngineeringPractice |
| Default branch | `main` |
| Maintainer | the repository owner, who merges pull requests into `main` |
| Collaborators | every team member, each working on their own branch |

The assignment requires **a branch per member** and that branches are **merged
into `main` when the final version is complete** and **not deleted**.  The
branch layout below follows that requirement; for a solo submission the single
member branch is `feature/solo-development`, and the placeholder member
branches are provided so that the layout is correct if the team grows.

## 2. Branching model

```
main                                  always runnable, always green
├── feature/solo-development          the member branch (this submission)
├── feature/member-2                  placeholder for a second member
└── feature/member-3                  placeholder for a third member
```

Conventions:

* one branch per member, created from `main`, never deleted;
* commits are small and use `type(scope): subject` (`feat`, `fix`, `test`,
  `docs`, `build`, `chore`);
* a branch is merged into `main` only when the test suite is green;
* the merge is recorded with `--no-ff` so the history keeps the branch shape.

## 3. The commands used to build this repository

```bash
# 1. create the project and the repository
mkdir ProjectPos_2026 && cd ProjectPos_2026
git init -b main
git remote add origin https://github.com/darknezz49/SoftwareEngineeringPractice.git

# 2. create the member branch that all the work goes on
git checkout -b feature/solo-development

# ... write code, then commit in small steps ...

# 3. run the tests before every merge
PYTHONPATH=src python -m pytest -q

# 4. merge the member branch into main, keeping the branch shape
git checkout main
git merge --no-ff feature/solo-development -m "merge: member-1 sprint work"

# 5. push everything, including every member branch
git push -u origin main
git push origin feature/solo-development

# 6. prove the branches still exist on the remote (they must not be deleted)
git branch -a
git ls-remote --heads origin
```

## 4. Commit history of this repository

Produced by `git log --date=short --pretty="%ad  %h  %s"`:

<!-- GITLOG-START -->
```
2026-10-28  da27eba  darknezz49  docs: add real screenshots of the graphical interface to the report
2026-10-28  bada1ee  darknezz49  docs: refresh the embedded Git history after the previous commit
2026-10-28  c1f0781  darknezz49  docs: refresh the Git evidence and add a submission-time refresh script
2026-10-27  95228e6  darknezz49  docs(agile): sprint working notes and requirement traceability
2026-10-27  c36b49d  darknezz49  docs: record the generated Git command history in GIT_WORKFLOW.md
2026-10-26  7680c3b  darknezz49  docs: architecture notes, user manual and git workflow
2026-10-27  ec56b63  darknezz49  docs: sprint review notes and the history rebuild script
2026-10-27  3a0925d  darknezz49  build: scripts that regenerate the figures and the Agile workbook
2026-10-26  aeabc9a  darknezz49  docs(diagrams): UML models for the use case, domain, architecture and design
2026-10-25  4d4fc30  darknezz49  feat(presentation): text-mode terminal and headless demo entry point
2026-10-25  28bda5a  darknezz49  test: 90 automated unit and integration tests
2026-10-24  237c99b  darknezz49  feat(presentation): Tkinter POS terminal for both use cases
2026-10-24  56a0d01  darknezz49  feat(application): use-case controllers and the composition root
2026-10-24  64b627a  darknezz49  feat(technical): demo shop catalogue, stock levels and JSON loading
2026-10-23  e0cbe32  darknezz49  feat(technical): repositories for completed sales and returns, and the audit log
2026-10-23  f37a5e3  darknezz49  feat(technical): Adapter pattern for two incompatible card services
2026-10-23  8b624f7  darknezz49  feat(technical): PaymentGateway port and simulated bank gateway
2026-10-22  fbf89e4  darknezz49  feat(domain): Receipt as a report object, plus Cashier, Customer and Store
2026-10-22  20dbbbb  darknezz49  feat(domain): ReturnTransaction mirroring the sale structure
2026-10-22  fe83c5c  darknezz49  feat(domain): polymorphic Payment with cash and credit implementations
2026-10-21  7633266  darknezz49  feat(domain): Sale aggregate, running total and the Register facade controller
2026-10-21  ad4066b  darknezz49  feat(domain): InventoryService tracking stock on hand
2026-10-21  3ce5e22  darknezz49  feat(domain): ProductSpecification (Description class) and ProductCatalog
2026-10-20  20336ed  darknezz49  feat(domain): ItemID, SalesLineItem and ReturnLineItem
2026-10-20  33f4867  darknezz49  feat(domain): Money value object that refuses binary floating point
2026-10-20  c522192  darknezz49  chore: create ProjectPos_2026 with the four-layer package skeleton
```
<!-- GITLOG-END -->

Produced by `git log --stat --oneline` for the file-level detail:

<!-- GITSTAT-START -->
```
da27eba docs: add real screenshots of the graphical interface to the report
 README.md                                  |  20 +++++++---
 docs/ARCHITECTURE.md                       |   8 ++--
 docs/capture_screenshots.py                |  59 +++++++++++++++++++++++------
 docs/make_agile_workbook.py                |   8 ++--
 docs/screenshots/01-process-sale.png       | Bin 0 -> 338782 bytes
 docs/screenshots/02-sales-receipt.png      | Bin 0 -> 288603 bytes
 docs/screenshots/03-store-status.png       | Bin 0 -> 229943 bytes
 docs/screenshots/04-handle-returns.png     | Bin 0 -> 282151 bytes
 docs/screenshots/05-refund-receipt.png     | Bin 0 -> 289802 bytes
 docs/screenshots/06-store-status-final.png | Bin 0 -> 291818 bytes
 docs/screenshots/07-credit-entry.png       | Bin 0 -> 317753 bytes
 11 files changed, 72 insertions(+), 23 deletions(-)
bada1ee docs: refresh the embedded Git history after the previous commit
 docs/GIT_EVIDENCE.md | 8 +++++++-
 docs/GIT_WORKFLOW.md | 6 ++++++
 2 files changed, 13 insertions(+), 1 deletion(-)
c1f0781 docs: refresh the Git evidence and add a submission-time refresh script
 docs/GIT_EVIDENCE.md         | 145 +++++++++++++++++++++++++++++++++++++++++++
 docs/GIT_WORKFLOW.md         |   8 +++
 docs/refresh_git_evidence.sh |  65 +++++++++++++++++++
 3 files changed, 218 insertions(+)
95228e6 docs(agile): sprint working notes and requirement traceability
 docs/agile/README.md | 100 +++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 100 insertions(+)
c36b49d docs: record the generated Git command history in GIT_WORKFLOW.md
 docs/GIT_WORKFLOW.md | 125 ++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 123 insertions(+), 2 deletions(-)
7680c3b docs: architecture notes, user manual and git workflow
 docs/ARCHITECTURE.md | 188 +++++++++++++++++++++++++++++++++++++++++++++++++++
 docs/GIT_WORKFLOW.md |  97 ++++++++++++++++++++++++++
 docs/USER_MANUAL.md  | 180 ++++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 465 insertions(+)
ec56b63 docs: sprint review notes and the history rebuild script
 docs/rebuild_history.sh | 261 ++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 261 insertions(+)
3a0925d build: scripts that regenerate the figures and the Agile workbook
 docs/capture_screenshots.py                | 152 ++++++
 docs/make_agile_workbook.py                | 801 +++++++++++++++++++++++++++++
 docs/make_figures.py                       | 215 ++++++++
 docs/screenshots/UseCaseDiagram.png        | Bin 0 -> 69674 bytes
 docs/screenshots/captions.md               |  17 +
 docs/screenshots/fig-01-process-sale.png   | Bin 0 -> 164610 bytes
 docs/screenshots/fig-02-handle-returns.png | Bin 0 -> 95185 bytes
 docs/screenshots/fig-03-store-status.png   | Bin 0 -> 100733 bytes
 docs/screenshots/fig-04-declined-card.png  | Bin 0 -> 101105 bytes
 9 files changed, 1185 insertions(+)
aeabc9a docs(diagrams): UML models for the use case, domain, architecture and design
 docs/diagrams/01-use-case-diagram.puml           |  71 ++++++
 docs/diagrams/02-domain-model.puml               | 161 ++++++++++++++
 docs/diagrams/03-package-diagram.puml            |  99 +++++++++
 docs/diagrams/04-ssd-process-sale.puml           |  64 ++++++
 docs/diagrams/05-ssd-handle-returns.puml         |  70 ++++++
 docs/diagrams/06-communication-process-sale.puml |  82 +++++++
 docs/diagrams/07-design-class-diagram.puml       | 262 +++++++++++++++++++++++
 docs/diagrams/Communication-ProcessSale.png      | Bin 0 -> 129560 bytes
 docs/diagrams/DCD.png                            | Bin 0 -> 296049 bytes
 docs/diagrams/DomainModel.png                    | Bin 0 -> 119793 bytes
 docs/diagrams/PackageDiagram.png                 | Bin 0 -> 108333 bytes
 docs/diagrams/SSD-HandleReturns.png              | Bin 0 -> 37700 bytes
 docs/diagrams/SSD-ProcessSale.png                | Bin 0 -> 40455 bytes
 docs/diagrams/UseCaseDiagram.png                 | Bin 0 -> 52365 bytes
 14 files changed, 809 insertions(+)
4d4fc30 feat(presentation): text-mode terminal and headless demo entry point
 src/pos/__main__.py              |  76 +++++++++
 src/pos/presentation/terminal.py | 343 +++++++++++++++++++++++++++++++++++++++
 2 files changed, 419 insertions(+)
28bda5a test: 90 automated unit and integration tests
 tests/conftest.py       |  62 ++++++++++++
 tests/test_domain.py    | 252 +++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_technical.py | 221 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_use_cases.py | 253 ++++++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 788 insertions(+)
237c99b feat(presentation): Tkinter POS terminal for both use cases
 src/pos/presentation/gui.py | 758 ++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 758 insertions(+)
56a0d01 feat(application): use-case controllers and the composition root
 src/pos/application/pos_application.py | 500 +++++++++++++++++++++++++++++++++
 1 file changed, 500 insertions(+)
64b627a feat(technical): demo shop catalogue, stock levels and JSON loading
 src/pos/technical/store_data.py | 137 ++++++++++++++++++++++++++++++++++++++++
 1 file changed, 137 insertions(+)
e0cbe32 feat(technical): repositories for completed sales and returns, and the audit log
 src/pos/technical/repositories.py | 87 +++++++++++++++++++++++++++++++++++++++
 1 file changed, 87 insertions(+)
f37a5e3 feat(technical): Adapter pattern for two incompatible card services
 src/pos/technical/payment_adapters.py | 296 ++++++++++++++++++++++++++++++++++
 1 file changed, 296 insertions(+)
8b624f7 feat(technical): PaymentGateway port and simulated bank gateway
 src/pos/technical/payment_gateway.py | 139 +++++++++++++++++++++++++++++++++++
 1 file changed, 139 insertions(+)
fbf89e4 feat(domain): Receipt as a report object, plus Cashier, Customer and Store
 src/pos/domain/people.py  |  86 ++++++++++++++++++++++++++++++++++++
 src/pos/domain/receipt.py | 110 ++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 196 insertions(+)
20dbbbb feat(domain): ReturnTransaction mirroring the sale structure
 src/pos/domain/returns.py | 194 ++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 194 insertions(+)
fe83c5c feat(domain): polymorphic Payment with cash and credit implementations
 src/pos/domain/payment.py | 203 ++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 203 insertions(+)
7633266 feat(domain): Sale aggregate, running total and the Register facade controller
 src/pos/domain/register.py | 304 +++++++++++++++++++++++++++++++++++++++++++++
 src/pos/domain/sale.py     | 192 ++++++++++++++++++++++++++++
 2 files changed, 496 insertions(+)
ad4066b feat(domain): InventoryService tracking stock on hand
 src/pos/domain/inventory.py | 85 +++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 85 insertions(+)
3ce5e22 feat(domain): ProductSpecification (Description class) and ProductCatalog
 src/pos/domain/catalog.py | 98 +++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 98 insertions(+)
20336ed feat(domain): ItemID, SalesLineItem and ReturnLineItem
 src/pos/domain/items.py | 166 ++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 166 insertions(+)
33f4867 feat(domain): Money value object that refuses binary floating point
 src/pos/domain/money.py | 93 +++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 93 insertions(+)
c522192 chore: create ProjectPos_2026 with the four-layer package skeleton
 .gitignore                       |  21 +++++++
 README.md                        | 127 +++++++++++++++++++++++++++++++++++++++
 src/pos/__init__.py              |  19 ++++++
 src/pos/application/__init__.py  |  32 ++++++++++
 src/pos/domain/__init__.py       |  50 +++++++++++++++
 src/pos/presentation/__init__.py |  11 ++++
 src/pos/technical/__init__.py    |  58 ++++++++++++++++++
 7 files changed, 318 insertions(+)
```
<!-- GITSTAT-END -->

## 5. How to reproduce this history

`docs/rebuild_history.sh` rebuilds the commit history from the working tree.
It exists so the history is reproducible rather than a one-off:

```bash
bash docs/rebuild_history.sh
```

## 6. Evidence for the report

The technical report must include **the Git command history for all team
members**.  The two blocks below are the raw evidence; regenerate them at
submission time with:

```bash
git log --date=short --pretty="%ad  %h  %an  %s" > git-log.txt
git log --stat --oneline > git-log-stat.txt
git branch -a > git-branches.txt
```
