"""Drawing PDF -> validated extraction, one sheet at a time.

Stages: render each page (``pages``), ask the provider for the objects on it (``prompt``,
``providers``), decode the answer into typed nodes (``wire``), merge the sheets (``merge``),
then validate the result with the SHACL shapes. The validation report is part of the result,
not an optional extra: an extraction is only as good as what the shapes say about it.

Sheets are read one by one, not as a whole document, for three reasons: a full-resolution page
is already a large input, a failure costs one page instead of the set, and every fact gets a
page to cite.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from steel_ontology.extract.merge import merge_sheets
from steel_ontology.extract.pages import DEFAULT_MAX_EDGE, page_count, render_pages
from steel_ontology.extract.prompt import sheet_prompt, system_prompt
from steel_ontology.extract.providers.base import Provider, ProviderError, Request, parse_json
from steel_ontology.extract.wire import SHEET_SCHEMA, SHEET_SCHEMA_NAME, decode_sheet
from steel_ontology.models import DEFAULT_BASE_IRI, Evidence, Extraction
from steel_ontology.validate import ValidationReport, validate


@dataclass(frozen=True)
class ExtractionResult:
    """What ``extract_pdf`` returns.

    ``problems`` lists everything a person should know before trusting the data: answers that
    could not be used, fields that were dropped, merge conflicts and links to missing objects.
    ``report`` is the SHACL validation of ``extraction``. ``model`` names every model that
    answered, in order of first use: normally just the provider's model, but a server-side
    fallback can make another model answer some pages (each such page is also a problem).
    """

    extraction: Extraction
    report: ValidationReport
    provider: str
    model: str
    pages: tuple[int, ...]
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when the shapes report no violation and nothing had to be dropped or guessed."""
        return self.report.conforms and not self.problems

    def unevidenced(self) -> list[str]:
        """Ids of objects that cite no evidence (the set itself is expected here)."""
        return [
            node.id
            for node in self.extraction.nodes
            if not node.evidenced_by and not isinstance(node, Evidence)
        ]


def page_key(number: int) -> str:
    """The request key of a page: ``page-001``."""
    return f"page-{number:03d}"


def extract_pdf(
    pdf: str | Path,
    provider: Provider,
    *,
    pages: Sequence[int] | None = None,
    base_iri: str = DEFAULT_BASE_IRI,
    max_edge: int = DEFAULT_MAX_EDGE,
    save_responses: str | Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> ExtractionResult:
    """Read a drawing PDF into typed objects with ``provider`` and validate the result.

    ``pages`` are 1-based page numbers (default: all). ``save_responses`` is a folder that
    receives each raw answer as ``page-NNN.json``, in the layout the recorded provider replays.
    A page whose answer cannot be obtained or parsed is skipped and reported in ``problems``;
    the other pages are still merged.
    """
    total = page_count(pdf)
    problems: list[str] = []
    sheets = []
    read = []
    answered_by: list[str] = []
    system = system_prompt()
    for page in render_pages(pdf, pages=pages, max_edge=max_edge):
        read.append(page.number)
        if progress:
            progress(f"page {page.number} of {total}: asking {provider.name}")
        request = Request(
            key=page_key(page.number),
            system=system,
            prompt=sheet_prompt(page, total),
            schema=SHEET_SCHEMA,
            schema_name=SHEET_SCHEMA_NAME,
            images=(page.png,),
        )
        try:
            answer = provider.complete(request)
            payload = parse_json(answer, provider.name)
        except ProviderError as error:
            problems.append(f"page {page.number}: no usable answer ({error})")
            continue
        model = getattr(provider, "last_model", None) or provider.model
        if model not in answered_by:
            answered_by.append(model)
        if model != provider.model:
            problems.append(f"page {page.number}: answered by {model}, not {provider.model}")
        if save_responses is not None:
            folder = Path(save_responses)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{request.key}.json").write_text(answer, encoding="utf-8")
        sheet = decode_sheet(payload, page.number)
        problems.extend(sheet.problems)
        sheets.append(sheet)
    merged = merge_sheets(sheets, base_iri)
    problems.extend(merged.conflicts)
    problems.extend(f"dangling link: {text}" for text in merged.extraction.dangling_references())
    return ExtractionResult(
        extraction=merged.extraction,
        report=validate(merged.extraction),
        provider=provider.name,
        model=", ".join(answered_by) or provider.model,
        pages=tuple(read),
        problems=tuple(problems),
    )
