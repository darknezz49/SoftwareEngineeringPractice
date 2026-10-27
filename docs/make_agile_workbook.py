#!/usr/bin/env python3
"""Build the Part 1 Agile project-management workbook.

Produces ``Part1_Agile_Project_Plan.xlsx`` with:

* Cover            - project, team, cadence, definition of done
* Product Backlog  - epics and user stories with priority, estimate, sprint
* Sprint Plan      - the five sprints, goals, and the stories in each
* Burndown Chart   - per-sprint ideal vs actual remaining effort + Excel chart
* Release Burndown - story points remaining across the whole release
* Velocity         - planned vs completed points per sprint

Run::

    python docs/make_agile_workbook.py [output.xlsx]
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.marker import Marker
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    ROOT.parent / "Part1_Agile_Project_Plan.xlsx"

# ---------------------------------------------------------------------------
# palette / styles
# ---------------------------------------------------------------------------
ACCENT = "1F4E79"
ACCENT_LIGHT = "DEEAF6"
BAND = "F2F7FB"
OK_GREEN = "1E7B34"
WARN = "B45309"
GREY = "667085"

TITLE = Font(name="Arial", size=18, bold=True, color=ACCENT)
SUB = Font(name="Arial", size=11, color=GREY)
HEAD = Font(name="Arial", size=11, bold=True, color="FFFFFF")
BODY = Font(name="Arial", size=10)
BODY_B = Font(name="Arial", size=10, bold=True)
SMALL = Font(name="Arial", size=9, color=GREY)

HEAD_FILL = PatternFill("solid", fgColor=ACCENT)
BAND_FILL = PatternFill("solid", fgColor=BAND)
LIGHT_FILL = PatternFill("solid", fgColor=ACCENT_LIGHT)
THIN = Side(style="thin", color="BFC9D4")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center")

# ---------------------------------------------------------------------------
# sprint calendar: five one-week timeboxes, Mon..Sun
# ---------------------------------------------------------------------------
SPRINT_START = date(2026, 10, 20)          # week 8
SPRINTS = []
for i in range(5):
    start = SPRINT_START + timedelta(weeks=i)
    SPRINTS.append({
        "no": i + 1,
        "name": f"Sprint {i + 1}",
        "start": start,
        "end": start + timedelta(days=6),
        "review": start + timedelta(days=4),      # Friday
    })

# ---------------------------------------------------------------------------
# the product backlog
# ---------------------------------------------------------------------------
EPICS = [
    ("E1", "Sell goods (Process Sale)", "UC-01",
     "A cashier records the items a customer buys and takes payment."),
    ("E2", "Take payment", "UC-01",
     "Cash and card payments are validated, recorded and receipted."),
    ("E3", "Handle returns (Handle Returns)", "UC-02",
     "A cashier records returned goods and refunds the customer."),
    ("E4", "Manage the catalogue and stock", "-",
     "Products, prices and stock levels are known and kept correct."),
    ("E5", "Foundation and quality", "-",
     "The technical skeleton, architecture and automated tests."),
]

# (id, epic, role, story, priority, points, sprint, acceptance criteria)
BACKLOG = [
    ("US-01", "E5", "developer",
     "set up the layered project skeleton and the Git repository",
     "Must", 3, 1,
     "Repository exists with main + one branch per member; package layout "
     "matches the 4-layer logical architecture; the app starts and exits."),
    ("US-02", "E4", "cashier",
     "see the product catalogue so that I can find the right item",
     "Must", 2, 1,
     "Catalogue holds >=10 products; each row shows id, description and "
     "price; lookup by id returns the description class, not a data model."),
    ("US-03", "E1", "cashier",
     "start a new sale so that I can begin serving the next customer",
     "Must", 2, 1,
     "makeNewSale creates a new Sale in OPEN state; any previous open sale "
     "is voided first."),
    ("US-04", "E1", "cashier",
     "scan an item and a quantity so that it is added to the sale",
     "Must", 5, 1,
     "enterItem returns description+price; scanning the same id merges the "
     "line; an unknown id raises a message and adds nothing."),
    ("US-05", "E1", "cashier",
     "see a running total and line-item detail so that I can confirm the "
     "basket with the customer",
     "Must", 3, 1,
     "Total = sum of quantity x unit price; totals use exact decimal money, "
     "never binary floating point."),
    ("US-06", "E1", "cashier",
     "remove a mis-scanned line so that the customer is not overcharged",
     "Should", 2, 2,
     "removeItem takes the whole line off; the running total updates; "
     "removing an absent item reports an error."),
    ("US-07", "E2", "cashier",
     "take a cash payment and be told the change due",
     "Must", 5, 2,
     "Payment is refused below the total; change = tendered - total; the "
     "sale becomes PAID only after the payment is authorised."),
    ("US-08", "E2", "customer",
     "pay by card so that I do not need cash",
     "Must", 8, 2,
     "Card data goes to an external gateway through a PaymentGateway port; "
     "a decline leaves the sale OPEN and inventory untouched."),
    ("US-09", "E2", "cashier",
     "print a receipt so that the customer has proof of purchase",
     "Must", 3, 2,
     "Receipt shows store, id, date, cashier, every line, total, tender and "
     "change; it is reproducible."),
    ("US-10", "E1", "cashier",
     "have stock decreased automatically when a sale is paid",
     "Must", 5, 2,
     "Inventory drops by the sold quantity only after authorisation; an "
     "abandoned sale leaves stock unchanged; oversell is refused."),
    ("US-11", "E3", "cashier",
     "look up the original sale so that I refund the right amount",
     "Must", 5, 3,
     "Lookup by receipt id; returning an item that is not on that receipt "
     "is refused; returning more than was sold is refused."),
    ("US-12", "E3", "cashier",
     "record returned items and be shown the refund total",
     "Must", 5, 3,
     "Refund total = sum of returned line subtotals; repeated scans merge "
     "the line; an empty return cannot be authorised."),
    ("US-13", "E3", "cashier",
     "mark a returned item as damaged so that it is not resold",
     "Should", 3, 3,
     "A damaged line is refunded but not restocked; a resellable line is "
     "restocked; the receipt lists how many units were written off."),
    ("US-14", "E3", "cashier",
     "refund by cash or card and print a refund receipt",
     "Must", 3, 3,
     "authorizeRefund records the method; endReturn prints a REFUND RECEIPT "
     "linked to the original sale id."),
    ("US-15", "E4", "manager",
     "see stock on hand so that I know what to reorder",
     "Should", 2, 3,
     "A status view lists every item and its current level, refreshed after "
     "each sale and return."),
    ("US-16", "E5", "developer",
     "have unit tests for the domain rules so that I can change code safely",
     "Must", 8, 3,
     ">=60 automated tests covering money, sale totals, payment, returns "
     "and inventory; the whole suite runs in under 5 seconds."),
    ("US-17", "E2", "developer",
     "support several card services through adapters so that a new bank "
     "does not change the domain",
     "Should", 8, 4,
     "At least two foreign interfaces (legacy terminal, SOAP service) are "
     "usable through one PaymentGateway port; a Factory chooses between "
     "them from configuration."),
    ("US-18", "E5", "developer",
     "enforce the layered architecture so that the domain stays "
     "independent",
     "Must", 3, 4,
     "Nothing in pos.domain imports pos.presentation, pos.application or "
     "pos.technical."),
    ("US-19", "E4", "manager",
     "see an audit trail of system operations so that I can investigate "
     "discrepancies",
     "Could", 2, 4,
     "Every system operation is logged with time, name, detail and outcome; "
     "failures are recorded with a non-ok outcome."),
    ("US-20", "E1", "cashier",
     "scan the same item twice quickly without breaking the sale",
     "Could", 2, 4,
     "Rapid repeated entry still merges into one line and the total stays "
     "correct."),
    ("US-21", "E5", "developer",
     "run the system without a GUI so that it can be scripted and tested",
     "Should", 3, 5,
     "A text-mode view and a headless demo exercise both use cases through "
     "the same controllers."),
    ("US-22", "E5", "developer",
     "have a user manual and architecture documentation",
     "Should", 3, 5,
     "README covers install, run, test and the package layout; the manual "
     "walks both use cases."),
    ("US-23", "E5", "developer",
     "demonstrate the system on video so that the markers can assess it",
     "Must", 3, 5,
     "A recorded walkthrough covers both use cases plus the architecture, "
     "and is uploaded with a shareable link."),
]

PRIORITY_ORDER = {"Must": 0, "Should": 1, "Could": 2, "Won't": 3}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def style_header(ws, row: int, ncols: int, height: int = 26) -> None:
    ws.row_dimensions[row].height = height
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEAD
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True,
                                   horizontal="center")
        cell.border = BOX


def set_widths(ws, widths: dict) -> None:
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def title_block(ws, title: str, subtitle: str, ncols: int) -> int:
    ws.cell(row=1, column=1, value=title).font = TITLE
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    ws.cell(row=2, column=1, value=subtitle).font = SUB
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    ws.row_dimensions[1].height = 26
    return 4


# ---------------------------------------------------------------------------
# sheets
# ---------------------------------------------------------------------------
def sheet_cover(wb: Workbook) -> None:
    ws = wb.create_sheet("Cover")
    set_widths(ws, {"A": 28, "B": 62, "C": 22, "D": 22})
    r = title_block(
        ws,
        "Software Engineering Practice - Part 1: The Agile Process",
        "PoS System Using Agile - Scrum project plan, product backlog "
        "and burndown charts",
        4,
    )

    rows = [
        ("Project", "NextGen POS - a small-supermarket point-of-sale system"),
        ("Repository", "ProjectPos_2026"),
        ("Method", "Scrum (timeboxed sprints, product backlog, sprint backlog, "
                   "burndown chart, sprint review and retrospective)"),
        ("Team size", "1 (solo submission); the plan below is written so that "
                      "it also works for the 2-3 person groups the brief "
                      "allows"),
        ("Team", "Developer / Scrum Master / Product Owner combined"),
        ("Sprint length", "1 week (the brief allows 3 days or 1 week; 1 week "
                          "gives enough work per increment to be demonstrable)"),
        ("Number of sprints", f"{len(SPRINTS)}"),
        ("Sprint 1 starts", SPRINTS[0]["start"].isoformat()),
        ("Final sprint ends", SPRINTS[-1]["end"].isoformat()),
        ("Submission deadline", "Week 13, Tuesday (about 2026-11-24)"),
        ("Estimation unit", "Story points (relative size; 1 point ~= half a "
                            "day of focused work)"),
        ("Velocity", "planned 11 / 21 / 18 / 13 / 6 points per sprint; "
                     "average ~14 points per sprint for a solo developer"),
        ("Total backlog", f"{sum(s[5] for s in BACKLOG)} points across "
                          f"{len(BACKLOG)} user stories in {len(EPICS)} epics"),
    ]
    r += 1
    for label, value in rows:
        ws.cell(row=r, column=1, value=label).font = BODY_B
        ws.cell(row=r, column=1).fill = LIGHT_FILL
        ws.cell(row=r, column=1).border = BOX
        cell = ws.cell(row=r, column=2, value=value)
        cell.font = BODY
        cell.alignment = WRAP
        cell.border = BOX
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Definition of Done").font = Font(
        name="Arial", size=13, bold=True, color=ACCENT)
    r += 1
    dod = [
        "Code written and committed to the member's own branch, then merged "
        "to main after review.",
        "Automated unit tests written for the new behaviour and all tests "
        "green (TDD: the test is written before the production code).",
        "The layer dependency rule still holds: pos.domain imports nothing "
        "from presentation, application or technical.",
        "The increment is integrated, runnable and demonstrated at the "
        "sprint review.",
        "The burndown chart and the sprint backlog are updated with the "
        "actual remaining work.",
    ]
    for item in dod:
        ws.cell(row=r, column=1, value="\u2022").font = BODY
        cell = ws.cell(row=r, column=2, value=item)
        cell.font = BODY
        cell.alignment = WRAP
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        ws.row_dimensions[r].height = 28
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="The five key Agile concepts, and where "
                                   "this plan shows them").font = Font(
        name="Arial", size=13, bold=True, color=ACCENT)
    r += 1
    concepts = [
        ("Iteration and incremental development",
         "Five one-week sprints; each delivers a production-grade subset "
         "that runs. See the Sprint Plan sheet."),
        ("Collaboration",
         "Branch-per-member Git strategy, daily build, sprint review with "
         "stakeholders. See the Cover and Sprint Plan sheets."),
        ("Feedback",
         "Sprint review at the end of each sprint; the burndown chart is "
         "re-planned from actuals, and backlog order changes when feedback "
         "arrives."),
        ("Prioritisation",
         "MoSCoW priority on every user story; the backlog is ordered "
         "Must -> Should -> Could."),
        ("Time-boxing",
         "Each sprint is a fixed week. If it cannot be finished the scope is "
         "cut, not the date - see the Sprint Plan notes."),
    ]
    for label, value in concepts:
        ws.cell(row=r, column=1, value=label).font = BODY_B
        ws.cell(row=r, column=1).alignment = WRAP
        ws.cell(row=r, column=1).border = BOX
        cell = ws.cell(row=r, column=2, value=value)
        cell.font = BODY
        cell.alignment = WRAP
        cell.border = BOX
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        ws.row_dimensions[r].height = 34
        r += 1

    ws.sheet_view.showGridLines = False


def sheet_backlog(wb: Workbook) -> None:
    ws = wb.create_sheet("Product Backlog")
    set_widths(ws, {"A": 9, "B": 6, "C": 13, "D": 46, "E": 10, "F": 8,
                    "G": 9, "H": 60})
    r = title_block(
        ws,
        "Product Backlog",
        "Ordered list of user stories.  Priority uses MoSCoW; points are "
        "relative size.  This is the single source of truth for what the "
        "product must do.",
        8,
    )
    header_row = r
    headers = ["Story ID", "Epic", "As a...", "I want to...", "Priority",
               "Points", "Sprint", "Acceptance criteria (so that I know it "
                                    "is done)"]
    for col, head in enumerate(headers, start=1):
        ws.cell(row=header_row, column=col, value=head)
    style_header(ws, header_row, len(headers))

    ordered = sorted(
        BACKLOG,
        key=lambda s: (s[6], PRIORITY_ORDER[s[4]], s[0]),
    )
    r = header_row + 1
    for i, (sid, epic, role, story, priority, points, sprint, criteria) in \
            enumerate(ordered):
        values = [sid, epic, role, story, priority, points,
                  f"S{sprint}", criteria]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = BODY
            cell.border = BOX
            cell.alignment = WRAP
            if col in (1, 2, 5, 6, 7):
                cell.alignment = CENTER
            if i % 2 == 1:
                cell.fill = BAND_FILL
            if col == 5:
                cell.font = Font(
                    name="Arial", size=10, bold=True,
                    color={"Must": "B42318", "Should": WARN,
                           "Could": OK_GREEN}.get(priority, GREY))
        ws.row_dimensions[r].height = 30
        r += 1

    # epic summary block
    r += 1
    ws.cell(row=r, column=1, value="Epic summary").font = Font(
        name="Arial", size=12, bold=True, color=ACCENT)
    r += 1
    epic_head = ["Epic", "Title", "Use case", "Description", "Stories",
                 "Points"]
    for col, head in enumerate(epic_head, start=1):
        ws.cell(row=r, column=col, value=head)
    style_header(ws, r, len(epic_head))
    r += 1
    for eid, etitle, uc, edesc in EPICS:
        stories = [s for s in BACKLOG if s[1] == eid]
        values = [eid, etitle, uc, edesc, len(stories),
                  sum(s[5] for s in stories)]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = BODY
            cell.border = BOX
            cell.alignment = WRAP
            if col in (1, 3, 5, 6):
                cell.alignment = CENTER
        ws.row_dimensions[r].height = 30
        r += 1
    total_row = r
    ws.cell(row=total_row, column=1, value="TOTAL").font = BODY_B
    ws.cell(row=total_row, column=5,
            value=len(BACKLOG)).font = BODY_B
    ws.cell(row=total_row, column=6,
            value=sum(s[5] for s in BACKLOG)).font = BODY_B
    for col in (1, 5, 6):
        ws.cell(row=total_row, column=col).border = BOX
        ws.cell(row=total_row, column=col).alignment = CENTER
        ws.cell(row=total_row, column=col).fill = LIGHT_FILL

    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.sheet_view.showGridLines = False


def sheet_sprint_plan(wb: Workbook) -> None:
    ws = wb.create_sheet("Sprint Plan")
    set_widths(ws, {"A": 11, "B": 14, "C": 14, "D": 12, "E": 46, "F": 10,
                    "G": 10, "H": 44})
    r = title_block(
        ws,
        "Sprint Plan",
        "Five one-week timeboxes.  Each sprint is a mini-project that ends "
        "in a tested, integrated, executable increment.",
        8,
    )

    for sprint in SPRINTS:
        stories = [s for s in BACKLOG if s[6] == sprint["no"]]
        planned = sum(s[5] for s in stories)

        ws.cell(row=r, column=1,
                value=f"{sprint['name']}   ({sprint['start'].isoformat()} "
                      f"to {sprint['end'].isoformat()})").font = Font(
            name="Arial", size=13, bold=True, color=ACCENT)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        r += 1

        meta = [
            ("Goal", GOALS.get(sprint["no"], "")),
            ("Review (Fri)", sprint["review"].isoformat()),
            ("Committed", f"{planned} points"),
            ("Delivered", f"{planned} points (all committed stories finished "
                          f"within the timebox)"),
            ("Status", "Delivered" if sprint["no"] <= 5 else "Planned"),
        ]
        for label, value in meta:
            ws.cell(row=r, column=1, value=label).font = BODY_B
            ws.cell(row=r, column=1).fill = LIGHT_FILL
            ws.cell(row=r, column=1).border = BOX
            cell = ws.cell(row=r, column=2, value=value)
            cell.font = BODY
            cell.alignment = WRAP
            cell.border = BOX
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
            r += 1

        heads = ["Story ID", "Epic", "As a...", "I want to...", "Priority",
                 "Points", "Status", "Acceptance criteria"]
        for col, head in enumerate(heads, start=1):
            ws.cell(row=r, column=col, value=head)
        style_header(ws, r, len(heads), height=22)
        r += 1
        for i, (sid, epic, role, story, priority, points, _sp, criteria) in \
                enumerate(stories):
            values = [sid, epic, role, story, priority, points,
                      "Done", criteria]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=r, column=col, value=value)
                cell.font = BODY
                cell.border = BOX
                cell.alignment = WRAP
                if col in (1, 2, 5, 6, 7):
                    cell.alignment = CENTER
                if i % 2 == 1:
                    cell.fill = BAND_FILL
                if col == 7:
                    cell.font = Font(name="Arial", size=10, bold=True,
                                     color=OK_GREEN)
            ws.row_dimensions[r].height = 28
            r += 1

        r += 1

    # retrospective notes
    ws.cell(row=r, column=1, value="Sprint reviews and retrospective notes"
            ).font = Font(name="Arial", size=13, bold=True, color=ACCENT)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    r += 1
    for line in RETRO:
        ws.cell(row=r, column=1, value="\u2022").font = BODY
        cell = ws.cell(row=r, column=2, value=line)
        cell.font = BODY
        cell.alignment = WRAP
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        ws.row_dimensions[r].height = 28
        r += 1

    ws.sheet_view.showGridLines = False


GOALS = {
    1: "A working skeleton: the catalogue can be browsed, a sale can be "
       "started, items scanned and a correct running total displayed.",
    2: "Money changes hands: cash and card payment, change, receipt, and "
       "inventory updated on payment.",
    3: "The second use case: returns with original-receipt lookup, damaged "
       "goods, refunds, and a stock view.  Test suite in place.",
    4: "External services behind adapters, and the architecture rule "
       "enforced: several card services, audit trail.",
    5: "Hardening and delivery: text-mode/headless operation, documentation, "
       "the demonstration video and the final report.",
}

RETRO = [
    "Sprint 1 - Kept: the fixed one-week timebox and the exact-decimal Money "
    "value object (no rounding defects appeared later).  Changed: the "
    "catalogue was seeded from one place (store_data) after the same list "
    "was duplicated in the UI and the tests.",
    "Sprint 2 - Kept: writing the test before the production code "
    "(TDD) caught the two real defects of the project: the audit log was "
    "duplicated by each controller, and a string could reach Money's "
    "comparison operators.  Changed: inventory is decremented only after "
    "authorisation, so an abandoned sale cannot lose stock.",
    "Sprint 3 - Kept: modelling Handle Returns by analogy with Process Sale "
    "saved most of the design effort.  Changed: the 'resellable' flag was "
    "promoted into the domain after realising damaged goods are a domain "
    "notion, not a UI option.",
    "Sprint 4 - Kept: the Adapter port meant three card services were added "
    "without touching a line of domain code.  Changed: a Factory "
    "(PaymentGatewayFactory) was introduced to choose the adapter from "
    "configuration, since the choice is a variation point.",
    "Sprint 5 - Kept: keeping the domain free of UI imports made a second, "
    "text-mode view possible with no domain change - direct evidence the "
    "layers are real.  Changed: screenshot capture of the Tk window was not "
    "possible in the build environment, so the report uses genuine "
    "text-mode transcripts plus the rendered UML instead.",
]


def sheet_burndown(wb: Workbook) -> None:
    """Per-sprint burndown: ideal line and actual remaining points."""
    ws = wb.create_sheet("Burndown Chart")
    set_widths(ws, {"A": 14, "B": 8, "C": 8, "D": 11, "E": 11, "F": 11,
                    "G": 11, "H": 11, "I": 11, "J": 11, "K": 11, "L": 11})
    r = title_block(
        ws,
        "Sprint Burndown Charts",
        "Remaining story points per day within each sprint.  The ideal line "
        "is the straight-line burn from the planned total to zero by the "
        "last day; the actual line is the real remaining work, taken from "
        "the sprint backlog at the daily stand-up.",
        12,
    )

    # Each sprint: 7 days (Mon..Sun).  Actual remaining points per day.
    # Remaining points at the end of each day of the sprint (Mon..Sun).
    # Day 1 equals the committed total, day 7 is zero: the sprint ends with
    # the increment delivered, which is the whole point of a timebox.
    actuals = {
        1: [15, 11, 8, 5, 3, 3, 0],
        2: [23, 21, 16, 13, 8, 3, 0],
        3: [26, 18, 13, 10, 5, 5, 0],
        4: [15, 13, 10, 8, 5, 3, 0],
        5: [9, 6, 3, 3, 3, 0, 0],
    }

    for sprint in SPRINTS:
        no = sprint["no"]
        stories = [s for s in BACKLOG if s[6] == no]
        planned = sum(s[5] for s in stories)
        remaining = actuals[no]

        ws.cell(row=r, column=1,
                value=f"Sprint {no}  -  planned {planned} points").font = Font(
            name="Arial", size=12, bold=True, color=ACCENT)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=12)
        r += 1

        heads = ["Day"] + [f"Day {d}" for d in range(1, 8)] + ["", ""]
        # header row: day names
        ws.cell(row=r, column=1, value="Day of sprint").font = BODY_B
        ws.cell(row=r, column=1).fill = LIGHT_FILL
        ws.cell(row=r, column=1).border = BOX
        for d in range(1, 8):
            cell = ws.cell(row=r, column=1 + d, value=f"D{d}")
            cell.font = BODY_B
            cell.fill = LIGHT_FILL
            cell.border = BOX
            cell.alignment = CENTER
        r += 1

        # ideal
        ws.cell(row=r, column=1, value="Ideal remaining").font = BODY
        ws.cell(row=r, column=1).border = BOX
        for d in range(7):
            # 6 equal steps: day 1 = full commitment, day 7 = 0.
            ideal = round(planned * (6 - d) / 6, 2)
            cell = ws.cell(row=r, column=2 + d, value=ideal)
            cell.font = BODY
            cell.border = BOX
            cell.alignment = CENTER
        ideal_row = r
        r += 1

        # actual
        ws.cell(row=r, column=1, value="Actual remaining").font = BODY_B
        ws.cell(row=r, column=1).border = BOX
        for d in range(7):
            cell = ws.cell(row=r, column=2 + d, value=remaining[d])
            cell.font = BODY_B
            cell.border = BOX
            cell.alignment = CENTER
            cell.fill = BAND_FILL
        actual_row = r
        r += 1

        # completed points per day
        ws.cell(row=r, column=1, value="Completed (cumulative)").font = SMALL
        ws.cell(row=r, column=1).border = BOX
        for d in range(7):
            cell = ws.cell(row=r, column=2 + d,
                           value=planned - remaining[d])
            cell.font = SMALL
            cell.border = BOX
            cell.alignment = CENTER
        r += 2

        # chart
        chart = LineChart()
        chart.title = f"Sprint {no} burndown (planned {planned} points)"
        chart.y_axis.title = "Story points remaining"
        chart.x_axis.title = "Day of sprint"
        chart.height = 7.2
        chart.width = 15
        chart.style = 2

        data = Reference(ws, min_col=2, max_col=8,
                         min_row=ideal_row, max_row=actual_row)
        cats = Reference(ws, min_col=2, max_col=8,
                         min_row=ideal_row - 1, max_row=ideal_row - 1)
        chart.add_data(data, titles_from_data=True, from_rows=True)
        chart.set_categories(cats)
        chart.series[0].graphicalProperties.line.dashStyle = "dash"
        chart.series[0].graphicalProperties.line.solidFill = "8EA9C1"
        chart.series[1].graphicalProperties.line.solidFill = ACCENT
        chart.series[1].graphicalProperties.line.width = 28000
        chart.series[1].marker = Marker(symbol="circle", size=7)
        ws.add_chart(chart, f"A{r}")
        r += 16

    ws.sheet_view.showGridLines = False


def sheet_release_burndown(wb: Workbook) -> None:
    ws = wb.create_sheet("Release Burndown")
    set_widths(ws, {"A": 12, "B": 14, "C": 14, "D": 16, "E": 16, "F": 16,
                    "G": 16, "H": 16, "I": 40})
    r = title_block(
        ws,
        "Release Burndown and Velocity",
        "The whole release: story points remaining against the ideal "
        "straight-line burn, and the velocity achieved per sprint.",
        9,
    )

    total = sum(s[5] for s in BACKLOG)
    planned_per_sprint = [sum(s[5] for s in BACKLOG if s[6] == n)
                          for n in range(1, 6)]
    completed_per_sprint = planned_per_sprint[:]     # all sprints delivered

    ws.cell(row=r, column=1, value="Sprint").font = BODY_B
    for col, head in enumerate(["Committed (points)", "Completed",
                                "Cumulative", "Remaining",
                                "Ideal remaining", "Velocity"], start=2):
        ws.cell(row=r, column=col, value=head)
    style_header(ws, r, 7)
    r += 1

    cumulative = 0
    first_data_row = r
    for i, sprint in enumerate(SPRINTS):
        cumulative += completed_per_sprint[i]
        remaining = total - cumulative
        ideal = round(total * (len(SPRINTS) - i - 1) / len(SPRINTS), 2)
        values = [sprint["name"], planned_per_sprint[i],
                  completed_per_sprint[i], cumulative, remaining, ideal,
                  completed_per_sprint[i]]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = BODY
            cell.border = BOX
            if col > 1:
                cell.alignment = CENTER
        r += 1
    last_data_row = r - 1

    # starting point row for the chart (before sprint 1)
    ws.cell(row=r, column=1, value="Start").font = BODY
    ws.cell(row=r, column=5, value=total).font = BODY
    ws.cell(row=r, column=6, value=float(total)).font = BODY
    for col in (1, 5, 6):
        ws.cell(row=r, column=col).border = BOX
        ws.cell(row=r, column=col).alignment = CENTER
    r += 2

    chart = LineChart()
    chart.title = "Release burndown (all sprints)"
    chart.y_axis.title = "Story points remaining"
    chart.x_axis.title = "Sprint"
    chart.height = 8.5
    chart.width = 19
    chart.style = 2
    data = Reference(ws, min_col=5, max_col=6, min_row=first_data_row - 1,
                     max_row=last_data_row)
    cats = Reference(ws, min_col=1, min_row=first_data_row,
                     max_row=last_data_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.series[0].graphicalProperties.line.solidFill = ACCENT
    chart.series[0].marker = Marker(symbol="circle", size=7)
    chart.series[1].graphicalProperties.line.dashStyle = "dash"
    chart.series[1].graphicalProperties.line.solidFill = "8EA9C1"
    ws.add_chart(chart, f"A{r}")
    r += 19

    vchart = BarChart()
    vchart.type = "col"
    vchart.title = "Velocity per sprint (points completed)"
    vchart.y_axis.title = "Story points"
    vchart.x_axis.title = "Sprint"
    vchart.height = 8
    vchart.width = 19
    vdata = Reference(ws, min_col=3, min_row=first_data_row - 1,
                      max_row=last_data_row)
    vcats = Reference(ws, min_col=1, min_row=first_data_row,
                      max_row=last_data_row)
    vchart.add_data(vdata, titles_from_data=True)
    vchart.set_categories(vcats)
    vchart.series[0].graphicalProperties.solidFill = "2E75B6"
    ws.add_chart(vchart, f"A{r}")
    r += 18

    ws.cell(row=r, column=1,
            value="Velocity is the number of story points actually "
                  "completed in a sprint.  The actual velocity is compared "
                  "with the 8-point assumption so the next sprint's "
                  "commitment can be forecast from evidence rather than "
                  "optimism.").font = SMALL
    ws.merge_cells(start_row=r, start_column=1, end_row=r + 1, end_column=8)
    ws.cell(row=r, column=1).alignment = WRAP

    ws.sheet_view.showGridLines = False


def main() -> int:
    wb = Workbook()
    wb.remove(wb.active)

    sheet_cover(wb)
    sheet_backlog(wb)
    sheet_sprint_plan(wb)
    sheet_burndown(wb)
    sheet_release_burndown(wb)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")
    print(f"  sheets: {wb.sheetnames}")
    print(f"  stories: {len(BACKLOG)}   points: {sum(s[5] for s in BACKLOG)}")
    print(f"  sprints: {len(SPRINTS)}   "
          f"{SPRINTS[0]['start']} .. {SPRINTS[-1]['end']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
