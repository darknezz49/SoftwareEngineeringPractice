#!/usr/bin/env python3
"""Render the report's figures.

Two families of figure are produced:

1. **Terminal transcripts** - the real text-mode POS (``pos.presentation.terminal``)
   is driven through scripted scenarios with a fixed clock, and the resulting
   transcript is drawn into a PNG styled like a point-of-sale display.  These
   are genuine program output, not mock-ups.
2. **Console reports** - the headless demo output (running total, receipts,
   stock levels) rendered the same way.

Usage::

    python docs/make_figures.py [output-dir]
"""
from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from pos.application import build_application  # noqa: E402
from pos.presentation.terminal import TerminalPOS  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screenshots"

# -- appearance --------------------------------------------------------------
BG = (18, 24, 32)          # terminal body
BAR = (38, 48, 62)         # window title bar
FG = (214, 228, 240)       # normal text
FG_DIM = (128, 148, 170)   # prompt lines
FG_OK = (126, 217, 139)    # confirmations
FG_WARN = (247, 202, 108)  # warnings / declines
FG_TOTAL = (255, 255, 255)
ACCENT = (94, 165, 235)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Courier.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
]

FIXED_NOW = datetime(2026, 10, 20, 14, 32, 7)


def _font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise SystemExit("no monospace font found")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    path = _font_path()
    try:
        return ImageFont.truetype(path, size, index=0)
    except Exception:
        return ImageFont.load_default()


def _classify(line: str) -> tuple[int, int, int]:
    stripped = line.strip()
    if stripped.startswith(("!", "!!")):
        return FG_WARN
    if stripped.startswith(("+", "  Sale ", "  Return ")) or \
            stripped.startswith("Refunded") or "complete." in stripped:
        return FG_OK
    if stripped.startswith(("Scan ", "Quantity", "Select ", "Payment",
                            "Cash tendered", "Original receipt", "Item id",
                            "Is the item", "Refund method", "Retry")):
        return FG_DIM
    if "TOTAL" in stripped or "AMOUNT DUE" in stripped or \
            "REFUND DUE" in stripped:
        return FG_TOTAL
    return FG


def render_transcript(text: str, title: str, subtitle: str = "",
                      cols: int | None = None, font_size: int = 15) -> Image.Image:
    """Draw ``text`` as a terminal window and return the image."""
    font = _load_font(font_size)
    lines = text.replace("\t", "    ").split("\n")
    cols = cols or max((len(line) for line in lines), default=80)
    cols = min(max(cols, 60), 118)

    char_w = font.getlength("M")
    line_h = int(font_size * 1.46)

    pad_x, pad_y = 22, 18
    bar_h = 46
    width = int(cols * char_w) + pad_x * 2
    height = bar_h + pad_y * 2 + line_h * len(lines)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # title bar
    draw.rectangle([0, 0, width, bar_h], fill=BAR)
    for i, colour in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 20 + i * 20
        draw.ellipse([cx - 6, bar_h // 2 - 6, cx + 6, bar_h // 2 + 6],
                     fill=colour)
    title_font = _load_font(font_size)
    draw.text((88, bar_h // 2), title, font=title_font, fill=(230, 238, 246),
              anchor="lm")
    if subtitle:
        draw.text((width - 20, bar_h // 2), subtitle, font=_load_font(12),
                  fill=(160, 180, 200), anchor="rm")

    # body
    y = bar_h + pad_y
    for line in lines:
        colour = _classify(line)
        draw.text((pad_x, y), line.rstrip(), font=font, fill=colour)
        y += line_h

    return img


def save(img: Image.Image, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    img.save(path, "PNG", optimize=True)
    return path


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------
def run_scenario(script: list[str], gateway: str = "simulated",
                 app=None) -> tuple[str, object]:
    """Run one scripted terminal session; return (transcript, application).

    A single application is threaded through the figures so that a receipt
    issued by an earlier figure really does exist for a later return to look
    up - the figures then tell one continuous story instead of six unrelated
    ones.
    """
    buf = io.StringIO()
    if app is None:
        app = build_application(gateway_kind=gateway, clock=lambda: FIXED_NOW)
    TerminalPOS(app, inputs=script, stdout=buf).run()
    return buf.getvalue(), app


SCENARIOS: list[tuple[str, str, list[str], str]] = [
    (
        "fig-01-process-sale",
        "Process Sale - text-mode POS terminal",
        ["1", "1001", "2", "1005", "1", "1008", "3", "total", "1", "30.00",
         "0"],
        "The cashier scans three products, the running total and line-item "
        "detail build up, then payment is taken in cash and change is given.",
    ),
    (
        "fig-02-handle-returns",
        "Handle Returns - text-mode POS terminal",
        #      returns, receipt from fig-01, item, qty, resellable? ...
        ["2", "S000001", "1001", "1", "Y", "1008", "2", "N", "done", "2", "0"],
        "A return is opened against receipt S000001 (issued in figure 1), one "
        "unit comes back resellable and two units damaged, and the refund "
        "goes back to the card.",
    ),
    (
        "fig-03-store-status",
        "Store Status after both use cases have run",
        ["3", "0"],
        "Stock levels after the sale and the return, plus the audit trail of "
        "system operations the two controllers recorded.",
    ),
    (
        "fig-04-declined-card",
        "Credit payment declined by the issuing bank",
        ["1", "1005", "2", "total", "2", "4000000000000002", "0", "0"],
        "The Adapter reports the decline, the sale stays open and inventory "
        "is untouched - the 'reimbursement rejected' alternate scenario from "
        "the fully dressed use case.",
    ),
]


def main() -> int:
    written: list[tuple[str, Path, str]] = []
    app = None
    for name, title, script, caption in SCENARIOS:
        text, app = run_scenario(script, app=app)
        img = render_transcript(text, title)
        path = save(img, name)
        written.append((title, path, caption))
        print(f"  {name:<26} {img.size[0]:>5}x{img.size[1]:<5} "
              f"{path.stat().st_size:>9,} B")

    # captions file, for the report writer
    (OUT / "captions.md").write_text(
        "# Figure captions\n\n"
        + "\n\n".join(f"**{t}** (`{p.name}`)\n\n{c}" for t, p, c in written)
        + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {len(written)} figures to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
