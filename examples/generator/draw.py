"""Draw the invented job as a four-sheet vector PDF.

Every piece of text that the gold extraction cites is drawn through ``Canvas``, which records
where it landed. Those regions become the ``Evidence`` zones, so the citations in the gold data
point at the real place on the sheet.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

import pymupdf

from generator import job

PAGE_W, PAGE_H = 1190, 842  # A3 landscape, in points
BLACK = (0, 0, 0)
GREY = (0.45, 0.45, 0.45)
RED = (0.85, 0.1, 0.1)
ORANGE = (1.0, 0.6, 0.1)
FONT = "helv"
BOLD = "hebo"

Regions = dict[str, dict[str, str]]
"""Per sheet number: region key -> normalised ``x0,y0,x1,y1`` box."""


class Canvas:
    """A page plus a record of where each keyed item was drawn."""

    def __init__(self, page: pymupdf.Page) -> None:
        self.page = page
        self._boxes: dict[str, pymupdf.Rect] = {}

    def mark(self, key: str, rect: pymupdf.Rect) -> None:
        """Remember ``rect`` under ``key``; a repeated key grows the region."""
        self._boxes[key] = self._boxes[key] | rect if key in self._boxes else pymupdf.Rect(rect)

    def text(
        self,
        x: float,
        y: float,
        content: str,
        size: float = 8,
        *,
        key: str | None = None,
        bold: bool = False,
        color: tuple[float, float, float] = BLACK,
        vertical: bool = False,
    ) -> pymupdf.Rect:
        """Write one line with its baseline starting at (x, y); return its bounding box."""
        font = BOLD if bold else FONT
        width = pymupdf.get_text_length(content, fontname=font, fontsize=size)
        self.page.insert_text(
            (x, y), content, fontsize=size, fontname=font, color=color, rotate=90 if vertical else 0
        )
        if vertical:
            rect = pymupdf.Rect(x - size, y - width, x + 0.25 * size, y)
        else:
            rect = pymupdf.Rect(x, y - size, x + width, y + 0.25 * size)
        if key:
            self.mark(key, rect)
        return rect

    def line(self, start, end, width: float = 0.7, color=BLACK, dashes: str | None = None) -> None:
        self.page.draw_line(start, end, color=color, width=width, dashes=dashes)

    def box(self, rect, width: float = 0.7, color=BLACK, fill=None, opacity: float = 1) -> None:
        self.page.draw_rect(rect, color=color, fill=fill, width=width, fill_opacity=opacity)

    def regions(self) -> dict[str, str]:
        """Every recorded region as a normalised ``x0,y0,x1,y1`` string."""
        return {
            key: f"{r.x0 / PAGE_W:.3f},{r.y0 / PAGE_H:.3f},{r.x1 / PAGE_W:.3f},{r.y1 / PAGE_H:.3f}"
            for key, r in self._boxes.items()
        }


def render(path: Path) -> Regions:
    """Write the PDF to ``path`` and return the recorded regions of every sheet."""
    document = pymupdf.open()
    regions: Regions = {}
    drawers = (_general_notes, _framing_plan, _schedules, _details)
    for index, (sheet, draw) in enumerate(zip(job.SHEETS, drawers, strict=True), start=1):
        canvas = Canvas(document.new_page(width=PAGE_W, height=PAGE_H))
        _frame_and_title_block(canvas, sheet, index)
        draw(canvas)
        regions[sheet.number] = canvas.regions()
    document.set_metadata(
        {
            "title": f"{job.PROJECT_NAME} (synthetic example drawing set)",
            "author": "steel-drawing-ontology example generator",
            "subject": job.DISCLAIMER,
            "creator": "examples/generate.py",
            "producer": "PyMuPDF",
            "creationDate": "D:20260101000000Z",
            "modDate": "D:20260101000000Z",
        }
    )
    document.save(path, garbage=4, deflate=True, no_new_id=True)
    document.close()
    return regions


# ---------------------------------------------------------------------------- shared furniture


def _frame_and_title_block(canvas: Canvas, sheet: job.SheetInfo, index: int) -> None:
    canvas.box(pymupdf.Rect(20, 20, PAGE_W - 20, PAGE_H - 20), width=1.5)
    x0, x1, y0 = 790, PAGE_W - 20, 676
    canvas.box(pymupdf.Rect(x0, y0, x1, PAGE_H - 20), width=1.2)

    row_h = 14
    columns = (x0, x0 + 40, x0 + 120, x1)
    header = ("REV", "DATE", "DESCRIPTION")
    table = [header, *((r.code, r.date, r.description) for r in job.REVISIONS)]
    for row_index, cells in enumerate(table):
        top = y0 + row_index * row_h
        canvas.line((x0, top + row_h), (x1, top + row_h), width=0.5)
        for cell, left in zip(cells, columns, strict=False):
            key = f"revision-{cells[0]}" if row_index else None
            canvas.text(left + 4, top + 10, cell, 7, key=key, bold=row_index == 0)
    for left in columns[1:-1]:
        canvas.line((left, y0), (left, y0 + row_h * len(table)), width=0.5)

    canvas.text(x0 + 8, 740, job.PROJECT_NAME, 12, key="title-block", bold=True)
    canvas.text(x0 + 8, 752, job.DISCLAIMER, 6.5, color=GREY)
    canvas.line((x0, 760), (x1, 760), width=0.5)
    canvas.text(x0 + 8, 778, sheet.title, 11, key="title-block", bold=True)
    canvas.line((x0, 788), (x1, 788), width=0.5)
    canvas.text(x0 + 8, 800, f"PROJECT NO. {job.PROJECT_NUMBER}", 7, key="title-block")
    canvas.text(x0 + 8, 812, f"SCALE {sheet.scale}", 7, key="title-block")
    canvas.text(x0 + 150, 800, "SHEET NO.", 7)
    canvas.text(x0 + 150, 816, sheet.number, 14, key="title-block", bold=True)
    canvas.text(x0 + 270, 812, f"SHEET {index} OF {len(job.SHEETS)}", 7, key="title-block")


def _table(
    canvas: Canvas,
    x: float,
    y: float,
    widths: tuple[int, ...],
    header: tuple[str, ...],
    rows: list[tuple[str, ...]],
    prefix: str,
    row_h: float = 20,
) -> float:
    """Draw a ruled table; record ``<prefix>-row-<first cell>`` and ``...-cell-<row>-<column>``.

    Returns the y coordinate of the bottom edge.
    """
    edges = [x]
    for width in widths:
        edges.append(edges[-1] + width)
    bottom = y + row_h * (len(rows) + 1)
    for row_index in range(len(rows) + 2):
        level = y + row_index * row_h
        canvas.line((x, level), (edges[-1], level), width=1.0 if row_index in (0, 1) else 0.5)
    for edge in edges:
        canvas.line((edge, y), (edge, bottom), width=0.5)
    for column, title in enumerate(header):
        canvas.text(edges[column] + 4, y + row_h - 7, title, 7, bold=True)
    for row_index, cells in enumerate(rows, start=1):
        baseline = y + row_h * (row_index + 1) - 7
        for column, cell in enumerate(cells):
            rect = canvas.text(edges[column] + 4, baseline, cell, 8)
            canvas.mark(f"{prefix}-row-{cells[0]}", rect)
            canvas.mark(f"{prefix}-cell-{cells[0]}-{column}", rect)
    return bottom


# ------------------------------------------------------------------------------ S-001 notes


def _general_notes(canvas: Canvas) -> None:
    canvas.text(60, 70, "GENERAL NOTES", 16, bold=True)
    y = 100
    heading = None
    for note in job.NOTES:
        if note.heading != heading:
            heading = note.heading
            y += 10
            canvas.text(60, y, heading, 10, bold=True)
            y += 18
        for line_index, line in enumerate(_wrap(f"{note.number}.  {note.text}", 95)):
            canvas.text(60 if line_index == 0 else 78, y, line, 9, key=f"note-{note.number}")
            y += 13
        y += 5

    x, y = 640, 110
    canvas.text(x, y, "DESIGN LOADS (UNFACTORED)", 10, bold=True)
    rows = [(label, f"{kpa} kPa") for label, _, kpa in job.AREA_LOADS]
    bottom = _table(canvas, x, y + 10, (230, 90), ("LOAD", "VALUE"), rows, "load")
    canvas.text(
        x, bottom + 22, f"IMPORTANCE CATEGORY: {job.IMPORTANCE_CATEGORY}", 9, key="importance"
    )


def _wrap(text: str, width: int) -> list[str]:
    """Break ``text`` into lines of at most ``width`` characters at spaces."""
    lines, current = [], ""
    for word in text.split(" "):
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    return [*lines, current]


# ------------------------------------------------------------------------------- S-101 plan

PLAN_X, PLAN_Y, PLAN_SCALE = 170, 520, 640 / 12000  # origin at grid A/1; points per millimetre


def _plan_point(x_mm: float, y_mm: float) -> tuple[float, float]:
    """Plan coordinates (mm, y up) to page coordinates."""
    return PLAN_X + x_mm * PLAN_SCALE, PLAN_Y - y_mm * PLAN_SCALE


def _framing_plan(canvas: Canvas) -> None:
    width_mm = max(job.GRID_LETTERS.values())
    depth_mm = max(job.GRID_NUMBERS.values())
    _grids(canvas, width_mm, depth_mm)

    beams = {beam.mark: beam for beam in job.BEAMS}
    for y_mm in job.GRID_NUMBERS.values():  # B1 along the numbered grids, one piece per bay
        for x_mm in (0, 6000):
            start, end = _plan_point(x_mm, y_mm), _plan_point(x_mm + 6000, y_mm)
            canvas.line(start, end, width=2.2)
            label = f"B1 {beams['B1'].section}"
            canvas.text(start[0] + 105, start[1] - 6, label, 8, key="beam-B1")
    for x_mm in job.GRID_LETTERS.values():  # B2 along the lettered grids
        _vertical_beam(canvas, x_mm, depth_mm, f"B2 {beams['B2'].section}", "beam-B2")
    for x_mm in (3000, 9000):  # B3 infill beams at mid-bay
        _vertical_beam(canvas, x_mm, depth_mm, f"B3 {beams['B3'].section}", "beam-B3")

    for x_mm in (0, width_mm):  # vertical bracing, dashed beside the beam on grids A and C
        start, end = _plan_point(x_mm, 0), _plan_point(x_mm, depth_mm)
        canvas.line(
            (start[0] + 7, start[1] - 14), (end[0] + 7, end[1] + 14), width=1.2, dashes="[5 3] 0"
        )
        label = f"{job.BRACE_MARK} {job.BRACE_SECTION}  {job.BRACE_FORCE_TEXT}"
        canvas.text(start[0] + 22, start[1] - 30, label, 7, key="brace-VB1", vertical=True)

    for mark, locations in job.COLUMN_LOCATIONS.items():
        for location in locations:
            letter, number = location.split("/")
            cx, cy = _plan_point(job.GRID_LETTERS[letter], job.GRID_NUMBERS[number])
            canvas.box(pymupdf.Rect(cx - 5, cy - 5, cx + 5, cy + 5), width=1, fill=(1, 1, 1))
            canvas.line((cx - 5, cy - 5), (cx + 5, cy + 5), width=0.6)
            canvas.text(cx + 8, cy + 16, mark, 8, key=f"column-{mark}", bold=True)

    _detail_callout(canvas, *_plan_point(0, 0))
    _revision_cloud_and_markup(canvas)

    canvas.text(PLAN_X, 610, "PLATFORM FRAMING PLAN", 12, key="plan-title", bold=True)
    elevation = f"T/STEEL EL. {job.TOP_OF_STEEL_M}     SCALE 1:75"
    canvas.text(PLAN_X, 624, elevation, 8, key="plan-title")
    canvas.text(PLAN_X, 646, "1. FOR GENERAL NOTES SEE S-001.", 8)
    canvas.text(PLAN_X, 658, "2. FOR COLUMN AND BASE PLATE SCHEDULES SEE S-201.", 8)
    canvas.mark("plan-view", pymupdf.Rect(90, 170, 850, 630))


def _grids(canvas: Canvas, width_mm: int, depth_mm: int) -> None:
    for letter, x_mm in job.GRID_LETTERS.items():
        top, bottom = _plan_point(x_mm, depth_mm), _plan_point(x_mm, 0)
        canvas.line((top[0], top[1] - 60), (bottom[0], bottom[1] + 30), 0.4, GREY, "[8 3 2 3] 0")
        canvas.page.draw_circle((top[0], top[1] - 72), 12, color=BLACK, width=0.8)
        canvas.text(top[0] - 4, top[1] - 68, letter, 11, bold=True)
    for number, y_mm in job.GRID_NUMBERS.items():
        left, right = _plan_point(0, y_mm), _plan_point(width_mm, y_mm)
        canvas.line((left[0] - 60, left[1]), (right[0] + 30, right[1]), 0.4, GREY, "[8 3 2 3] 0")
        canvas.page.draw_circle((left[0] - 72, left[1]), 12, color=BLACK, width=0.8)
        canvas.text(left[0] - 76, left[1] + 4, number, 11, bold=True)
    letters = list(job.GRID_LETTERS.values())
    for first, second in itertools.pairwise(letters):
        a, b = _plan_point(first, depth_mm), _plan_point(second, depth_mm)
        canvas.line((a[0], a[1] - 40), (b[0], b[1] - 40), width=0.5)
        canvas.text((a[0] + b[0]) / 2 - 10, a[1] - 44, str(second - first), 8)
    a, b = _plan_point(0, 0), _plan_point(0, depth_mm)
    canvas.line((a[0] - 40, a[1]), (b[0] - 40, b[1]), width=0.5)
    canvas.text(a[0] - 44, (a[1] + b[1]) / 2 + 10, str(depth_mm), 8, vertical=True)


def _vertical_beam(canvas: Canvas, x_mm: int, depth_mm: int, label: str, key: str) -> None:
    start, end = _plan_point(x_mm, 0), _plan_point(x_mm, depth_mm)
    canvas.line(start, end, width=2.2)
    canvas.text(start[0] - 5, start[1] - 80, label, 8, key=key, vertical=True)


def _detail_callout(canvas: Canvas, cx: float, cy: float) -> None:
    """Detail bubble '1 over S-301' with a leader to the column at grid A/1."""
    bx, by = cx - 50, cy + 60
    canvas.line((cx - 4, cy + 6), (bx + 10, by - 10), width=0.5)
    canvas.page.draw_circle((bx, by), 15, color=BLACK, width=0.8)
    canvas.line((bx - 15, by), (bx + 15, by), width=0.5)
    canvas.text(bx - 3, by - 3, "1", 9, key="callout-1", bold=True)
    canvas.text(bx - 11, by + 9, "S-301", 6.5, key="callout-1")


def _revision_cloud_and_markup(canvas: Canvas) -> None:
    """The engineer's revision cloud, then markup in the style of a fabricator's copy."""
    x, y = _plan_point(3000, 0)
    cloud = pymupdf.Rect(x - 22, y - 172, x + 12, y - 70)
    _cloud(canvas.page, cloud)
    canvas.mark("revision-cloud", cloud)
    triangle = [
        (cloud.x1 + 6, cloud.y0 + 16),
        (cloud.x1 + 22, cloud.y0 + 16),
        (cloud.x1 + 14, cloud.y0),
    ]
    canvas.page.draw_polyline([*triangle, triangle[0]], color=BLACK, width=0.7)
    canvas.text(cloud.x1 + 11.5, cloud.y0 + 13, job.REVISIONS[-1].code, 7)

    for y_mm in job.GRID_NUMBERS.values():  # take-off highlight over every B1 label
        for x_mm in (0, 6000):
            px, py = _plan_point(x_mm, y_mm)
            rect = pymupdf.Rect(px + 101, py - 17, px + 163, py - 3)
            canvas.box(rect, width=0, color=None, fill=ORANGE, opacity=0.4)
            canvas.mark("highlight-B1", rect)

    note = canvas.text(x + 40, y - 150, job.QUERY_NOTE_TEXT, 10, key="query-note", color=RED)
    canvas.line((note.x0 - 2, note.y1 - 4), (cloud.x1 + 2, cloud.y0 + 40), width=0.8, color=RED)

    stamp = pymupdf.Rect(880, 80, 1040, 140)
    canvas.box(stamp, width=1.5, color=RED)
    canvas.text(
        stamp.x0 + 38, stamp.y0 + 22, "RECEIVED", 14, key="received-stamp", bold=True, color=RED
    )
    canvas.text(stamp.x0 + 50, stamp.y0 + 38, job.RECEIVED_STAMP_DATE, 9, color=RED)
    canvas.text(stamp.x0 + 38, stamp.y0 + 52, "FABRICATOR COPY", 8, color=RED)
    canvas.mark("received-stamp", stamp)


def _cloud(page: pymupdf.Page, rect: pymupdf.Rect, radius: float = 6) -> None:
    """A revision cloud: a ring of outward arcs along the edges of ``rect``."""
    corners = [rect.tl, rect.tr, rect.br, rect.bl]
    for start, end in zip(corners, [*corners[1:], corners[0]], strict=True):
        length = math.hypot(end.x - start.x, end.y - start.y)
        count = max(1, round(length / (2 * radius)))
        step_x, step_y = (end.x - start.x) / count, (end.y - start.y) / count
        for i in range(count):
            a = pymupdf.Point(start.x + step_x * i, start.y + step_y * i)
            b = pymupdf.Point(a.x + step_x, a.y + step_y)
            page.draw_sector((a + b) / 2, b, 180, color=BLACK, width=0.8, fullSector=False)


# -------------------------------------------------------------------------- S-201 schedules


def _schedules(canvas: Canvas) -> None:
    x, y = 60, 90
    canvas.text(x, y, "COLUMN SCHEDULE", 13, key="column-schedule", bold=True)
    header = (
        "MARK",
        "SECTION",
        "QTY",
        "LENGTH (mm)",
        "BASE PLATE",
        "Cf (kN) FACTORED",
        "WEIGHT (kg)",
    )
    rows = [
        (
            row.mark,
            row.section,
            str(row.quantity),
            str(row.length_mm),
            row.base_plate or "N/A",
            str(row.factored_axial_kn) if row.factored_axial_kn is not None else "N/A",
            str(row.weight_kg),
        )
        for row in job.COLUMN_ROWS
    ]
    widths = (60, 130, 50, 90, 90, 120, 90)
    bottom = _table(canvas, x, y + 12, widths, header, rows, "column")
    total_x = x + sum(widths[:-1])
    canvas.text(total_x - 116, bottom + 16, "TOTAL WEIGHT (kg)", 8, key="column-total", bold=True)
    canvas.text(
        total_x + 4, bottom + 16, str(job.COLUMN_TOTAL_KG), 8, key="column-total", bold=True
    )
    canvas.mark("column-schedule", pymupdf.Rect(x, y - 13, x + sum(widths), bottom + 20))

    y = bottom + 80
    canvas.text(x, y, "BASE PLATE SCHEDULE", 13, key="base-plate-schedule", bold=True)
    header = ("MARK", "PLATE (mm)", "HOLES", "ANCHOR RODS", "WELD TO COLUMN (mm)")
    rows = [(r.mark, r.plate, r.holes, r.anchor_rods, r.weld_mm) for r in job.BASE_PLATE_ROWS]
    widths = (60, 120, 100, 180, 130)
    bottom = _table(canvas, x, y + 12, widths, header, rows, "base-plate")
    canvas.mark("base-plate-schedule", pymupdf.Rect(x, y - 13, x + sum(widths), bottom))


# ---------------------------------------------------------------------------- S-301 details


def _details(canvas: Canvas) -> None:
    _shear_tab_detail(canvas, 150, 150)
    _base_plate_detail(canvas, 560, 150)


def _detail_title(canvas: Canvas, x: float, y: float, number: str, title: str, key: str) -> None:
    canvas.page.draw_circle((x + 14, y), 14, color=BLACK, width=1)
    canvas.text(x + 10, y + 5, number, 13, key=key, bold=True)
    canvas.text(x + 36, y - 1, title, 10, key=key, bold=True)
    canvas.text(x + 36, y + 11, "SCALE 1:10", 7, key=key)


def _shear_tab_detail(canvas: Canvas, x: float, y: float) -> None:
    """Elevation of a beam framing into a column flange through a single shear tab."""
    canvas.line((x, y), (x, y + 300), width=1.8)
    canvas.line((x + 12, y), (x + 12, y + 300), width=1.8)
    for level in (y + 90, y + 98, y + 222, y + 230):  # beam flanges
        canvas.line((x + 22, level), (x + 330, level), width=1.2)
    canvas.box(pymupdf.Rect(x + 12, y + 115, x + 62, y + 205), width=1.2)
    for level in (y + 130, y + 160, y + 190):
        canvas.page.draw_circle((x + 42, level), 5, color=BLACK, width=0.8)
    notes = (
        ("PL10 SHEAR TAB", y + 108),
        ("3 - 20 mm DIA. A325 BOLTS", y + 164),
        ("6 mm FILLET WELD BOTH SIDES", y + 205),
    )
    for label, level in notes:
        canvas.line((x + 64, level - 3), (x + 148, level - 3), width=0.4)
        canvas.text(x + 152, level, label, 8, key="detail-1")
    canvas.text(x - 40, y + 320, f"COLUMN {job.COLUMN_ROWS[0].section}", 8)
    canvas.text(x + 200, y + 250, f"BEAM B1 {job.BEAMS[0].section}", 8, key="detail-1")
    title = "TYPICAL BEAM TO COLUMN SHEAR CONNECTION SC1"
    _detail_title(canvas, x - 40, y + 360, "1", title, "detail-1")
    canvas.mark("detail-1", pymupdf.Rect(x - 40, y, x + 340, y + 375))


def _base_plate_detail(canvas: Canvas, x: float, y: float) -> None:
    """Plan of base plate BP1 with the column section and four anchor rod holes."""
    plate = job.BASE_PLATE_ROWS[0]
    canvas.box(pymupdf.Rect(x, y + 40, x + 220, y + 260), width=1.5)
    for dx in (35, 185):
        for dy in (75, 225):
            canvas.page.draw_circle((x + dx, y + dy), 8, color=BLACK, width=0.8)
    for level in (y + 95, y + 205):  # column flanges, then the web
        canvas.box(pymupdf.Rect(x + 60, level - 4, x + 160, level + 4), width=1, fill=GREY)
    canvas.box(pymupdf.Rect(x + 107, y + 99, x + 113, y + 201), width=1, fill=GREY)
    notes = (
        (f"BASE PLATE {plate.mark}: {plate.plate}", y + 60),
        (f"{plate.holes} HOLES", y + 80),
        ("ANCHOR RODS AND 25 mm GROUT BY OTHERS", y + 100),
        (f"{plate.weld_mm} mm FILLET WELD ALL ROUND", y + 150),
    )
    for label, level in notes:
        canvas.line((x + 222, level - 3), (x + 246, level - 3), width=0.4)
        canvas.text(x + 250, level, label, 8, key="detail-2")
    _detail_title(canvas, x, y + 360, "2", f"BASE PLATE {plate.mark}", "detail-2")
    canvas.mark("detail-2", pymupdf.Rect(x, y + 40, x + 440, y + 375))
