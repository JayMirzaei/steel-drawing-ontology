"""PDF pages -> images and text, with pypdfium2.

pypdfium2 wraps PDFium under permissive licences (Apache-2.0 / BSD-3-Clause), so rendering a
drawing at run time puts no copyleft obligation on a user of this package. Each page is rendered
to a PNG for the vision model, and its text layer (when the PDF has one) is passed along as a
reading aid: vector drawings carry exact text, scans carry none.
"""

from __future__ import annotations

import io
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

DEFAULT_MAX_EDGE = 2400
"""Longest image side in pixels: enough to read 7 pt text on an A1 sheet rendered whole."""


@dataclass(frozen=True)
class Page:
    """One rendered page. ``number`` counts from 1; sizes are in PDF points."""

    number: int
    png: bytes
    text: str
    width: float
    height: float


def page_count(pdf: str | Path) -> int:
    """Number of pages in the PDF."""
    document = pdfium.PdfDocument(str(pdf))
    try:
        return len(document)
    finally:
        document.close()


def render_pages(
    pdf: str | Path, *, pages: Sequence[int] | None = None, max_edge: int = DEFAULT_MAX_EDGE
) -> Iterator[Page]:
    """Yield the chosen pages (1-based; all by default) as PNG plus text layer.

    The scale is chosen per page so that the longer side is ``max_edge`` pixels.
    """
    document = pdfium.PdfDocument(str(pdf))
    try:
        total = len(document)
        for number in pages if pages is not None else range(1, total + 1):
            if not 1 <= number <= total:
                raise ValueError(f"page {number} is outside 1..{total}")
            page = document[number - 1]
            width, height = page.get_size()
            bitmap = page.render(scale=max_edge / max(width, height))
            buffer = io.BytesIO()
            bitmap.to_pil().save(buffer, format="PNG", optimize=True)
            text_page = page.get_textpage()
            text = text_page.get_text_range()
            text_page.close()
            page.close()
            yield Page(number, buffer.getvalue(), text.replace("\r\n", "\n"), width, height)
    finally:
        document.close()


def parse_page_ranges(spec: str) -> list[int]:
    """``"1,3-5"`` -> ``[1, 3, 4, 5]``. Raises ``ValueError`` on anything else.

    A page named twice is read once: a second reading would cost a model call and add nothing.
    """
    numbers: list[int] = []
    for part in spec.split(","):
        first, _, last = part.strip().partition("-")
        start, end = int(first), int(last or first)
        if start < 1 or end < start:
            raise ValueError(f"bad page range {part!r}")
        numbers.extend(n for n in range(start, end + 1) if n not in numbers)
    return numbers
