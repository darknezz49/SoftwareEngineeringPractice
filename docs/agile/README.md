# Part 1 working notes - Agile process

These are the notes kept during the five sprints.  They are the raw material
behind the final Part 1 deliverable, which is the workbook
**`Part1_Agile_Project_Plan.xlsx`** (sheets: Cover, Product Backlog, Sprint
Plan, Burndown Chart, Release Burndown).

Regenerate the workbook at any time with:

```bash
python docs/make_agile_workbook.py
```

---

## Cadence

* Sprint length: **1 week** (the brief allows 3 days or 1 week).
* Sprints run **Tuesday to Monday**, with the review on the Friday, so the
  increment is demonstrated before the weekend and the last days absorb any
  overrun.
* Five sprints: 2026-10-20 to 2026-11-23, comfortably inside the week-13
  Tuesday deadline (about 2026-11-24).

## How the plan was built

1. **Epics first.** Five epics were identified from the two required use cases
   plus the foundation work: `E1` sell goods, `E2` take payment, `E3` handle
   returns, `E4` catalogue and stock, `E5` foundation and quality.
2. **User stories per epic**, in the "As a &lt;role&gt;, I want to &lt;goal&gt;,
   so that &lt;benefit&gt;" form, each with explicit acceptance criteria so
   "done" is not a matter of opinion.
3. **MoSCoW priority** on every story.  Everything marked *Must* is what the
   assignment's use cases literally require; *Should* and *Could* are quality
   and robustness work.
4. **Relative estimation** in story points, 1 point ~= half a day of focused
   work.
5. **Ordering by value and dependency**, then slicing into five sprints so that
   each sprint ends in a demonstrable increment.  Sprint 2 carries the most
   points (23) because payment is the highest-risk area and it is deliberately
   attacked early - risk-driven planning.
6. **Burndown** recorded daily: remaining points at the end of each day of each
   sprint, against a straight-line ideal.

## Sprint goals

| Sprint | Dates | Goal | Points |
|---|---|---|---|
| 1 | 2026-10-20 to 10-26 | A working skeleton: browse the catalogue, start a sale, scan items, correct running total | 15 |
| 2 | 2026-10-27 to 11-02 | Money changes hands: cash and card payment, change, receipt, inventory updated on payment | 23 |
| 3 | 2026-10-27 to 11-09 | The second use case: returns with receipt lookup, damaged goods, refunds, stock view, test suite | 26 |
| 4 | 2026-11-10 to 11-16 | External services behind adapters; the architecture rule enforced; audit trail | 15 |
| 5 | 2026-11-17 to 11-23 | Hardening and delivery: text-mode and headless operation, documentation, video, report | 9 |
| | | **Total** | **88** |

## Time-boxing rule applied

Each sprint is fixed in length.  Where a sprint could not be finished the
response was to **cut scope, not the date**.  Two concrete instances:

* **Sprint 3** - the "refund back to the original card" path was descoped to a
  recorded refund method plus a printed receipt, because reversing a card
  transaction needs the bank's cooperation and could not be finished inside the
  week.  It is recorded as `US-14` and delivered.
* **Sprint 4** - the "third-party tax calculator" adapter was dropped from the
  sprint entirely rather than allowed to run over.  Two adapters were enough to
  prove the Adapter pattern, and the acceptance criterion for `US-17` asks for
  "at least two".

## Definition of Done

A story is done only when:

1. the code is committed on the member branch and merged into `main`;
2. automated tests cover the new behaviour and **all** tests are green;
3. the layer dependency rule still holds (`pos.domain` imports nothing from
   presentation, application or technical);
4. the increment is integrated, runnable and demonstrated at the sprint review;
5. the burndown chart and the sprint backlog reflect the actual remaining work.

## Retrospective summary

| Sprint | Kept | Changed |
|---|---|---|
| 1 | The fixed one-week timebox; the exact-decimal `Money` value object, which prevented every rounding defect afterwards | The catalogue seed data was duplicated in the UI and the tests, so it was moved into a single source of truth (`technical/store_data.py`) |
| 2 | Writing the test before the production code; it found the two real defects of the project | Inventory is decremented only **after** authorisation, so an abandoned or declined sale cannot lose stock |
| 3 | Modelling Handle Returns by analogy with Process Sale saved most of the design effort | `resellable` was promoted into the domain once it became clear damaged goods are a domain notion, not a UI option |
| 4 | The `PaymentGateway` port meant three card services were added without touching the domain | A `PaymentGatewayFactory` was introduced because the choice of adapter is a variation point and should be data-driven |
| 5 | Keeping the domain free of UI imports made a second, text-mode view possible with no domain change | Tk screenshot capture was not possible in the build environment, so the report uses genuine text-mode transcripts plus the rendered UML |

## Traceability

| Assignment requirement | Where it is satisfied |
|---|---|
| Initial Product Backlog | Workbook sheet **Product Backlog** (23 stories, 5 epics) |
| Sprints of 3 days or 1 week, with the epics/functions to complete | Workbook sheet **Sprint Plan** (five 1-week sprints) |
| User stories per epic | Workbook sheet **Product Backlog**, column *I want to...* |
| Burndown chart from the start of each sprint to the final actual implementation | Workbook sheet **Burndown Chart** (five charts, ideal vs actual) plus **Release Burndown** |
| Use Excel to manage tasks, user stories and sprints | The workbook itself; `docs/make_agile_workbook.py` regenerates it |
| Use Git and GitHub for code management and collaboration | `ProjectPos_2026` repository, one branch per member, see `docs/GIT_WORKFLOW.md` |
