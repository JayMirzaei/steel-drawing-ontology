"""The generated vocabulary reference and the static site."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import EXAMPLE, ROOT
from steel_ontology import reference, vocabulary
from steel_ontology.site import FALLBACK_QUESTION, QUESTIONS, build_site, outline_zones
from steel_ontology.vocabulary import VERSION


@pytest.fixture(scope="module")
def ref() -> reference.Reference:
    return reference.build_reference()


def test_reference_covers_the_whole_vocabulary(ref: reference.Reference) -> None:
    assert len(ref.properties) == len(vocabulary.properties())
    assert {e.name for e in ref.enumerations} == set(vocabulary.enumerations())
    assert tuple(d.name for d in ref.defined) == vocabulary.defined_classes()
    assert len(ref.classes) + len(ref.enumerations) + len(ref.defined) == 108
    assert len(ref.shapes) == 60  # 36 checks plus one per closed vocabulary


def test_reference_reads_definitions_and_checks(ref: reference.Reference) -> None:
    defined = {d.name: d.definition for d in ref.defined}
    assert defined["MarkedUpSheet"] == "Sheet and (hasAnnotation some ThirdPartyMarkup)"
    assert defined["CommercialSheet"] == "Sheet and (pricingColumns value true)"
    properties = {p.name: p for p in ref.properties}
    assert properties["isTBD"].domain == "Annotation or Element or View"
    assert properties["isTBD"].functional and properties["isTBD"].range == "xsd:boolean"
    shapes = {s.name: s for s in ref.shapes}
    assert shapes["SheetShape"].target == "every Sheet"
    sheet_kind = next(c for c in shapes["SheetShape"].checks if c[1].startswith("sheetKind"))
    assert sheet_kind[:2] == ("Violation", "sheetKind: at least 1")
    assert (
        shapes["SheetKindValuesShape"]
        .checks[0][1]
        .startswith("sheetKind: one of GeneralNotesSheet, ")
    )
    severity, what, message = shapes["TitleBlockStatusConflictShape"].checks[0]
    assert (severity, what) == ("Warning", "SPARQL check") and "AS BUILT" in message


def test_committed_vocabulary_reference_is_current(ref: reference.Reference) -> None:
    """``docs/vocabulary.md`` must be regenerated when the ontology changes."""
    committed = (ROOT / "docs" / "vocabulary.md").read_text(encoding="utf-8")
    assert committed == reference.to_markdown(ref), (
        "run: steel-ontology docs --markdown docs/vocabulary.md"
    )


def test_html_reference_has_one_anchor_per_term(ref: reference.Reference) -> None:
    html = reference.to_html(ref)
    ids = re.findall(r'<tr id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert {"Beam", "sectionText", "SheetKind", "MarkedUpSheet", "SheetShape"} <= set(ids)
    assert html.startswith("<!doctype html>") and "<script" not in html


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    folder = tmp_path_factory.mktemp("site")
    build_site(folder, EXAMPLE)
    return folder


def test_site_has_every_page_and_asset(site: Path) -> None:
    names = {p.name for p in site.iterdir()}
    assert names >= {
        "index.html",
        "core.html",
        "shapes.html",
        "example.html",
        "validation.html",
        "inferred.html",
        "queries.html",
        "questions.html",
        "style.css",
        "core.ttl",
        "shapes.ttl",
        "gold.json",
        "drawings.pdf",
        ".nojekyll",
    }
    images = {p.name for p in (site / "img").iterdir()}
    assert {f"sheet-{n}.png" for n in range(1, 5)} <= images
    assert "question-1-page-2.png" in images


def test_site_is_static_and_self_contained(site: Path) -> None:
    """No script, no tracker, no external resource; every internal link resolves."""
    allowed = "https://github.com/JayMirzaei/steel-drawing-ontology"
    for page in site.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert "<script" not in html and "<iframe" not in html
        for target in re.findall(r'(?:href|src)="([^"]+)"', html):
            if target.startswith("http"):
                assert target == allowed, (page.name, target)
                continue
            file_name, _, anchor = target.partition("#")
            linked = site / file_name if file_name else page
            assert linked.is_file(), (page.name, target)
            if anchor and linked.suffix == ".html":
                assert f'id="{anchor}"' in linked.read_text(encoding="utf-8"), (page.name, target)


def test_site_shows_the_real_results(site: Path) -> None:
    validation = (site / "validation.html").read_text(encoding="utf-8")
    assert "0 violation(s), 0 warning(s)" in validation
    assert "5 violation(s), 1 warning(s)" in validation
    assert "Printed schedule total differs from the sum of its rows" in validation
    assert validation.count("<table>") == 1, "only the broken variant has findings to list"
    inferred = (site / "inferred.html").read_text(encoding="utf-8")
    assert "MarkedUpSheet" in inferred and "sheet-S-101" in inferred
    queries = (site / "queries.html").read_text(encoding="utf-8")
    assert queries.count("<h2 id=") == 24
    assert "ruleKind=PercentOfYieldRule" in queries  # a parameter that has rows was chosen
    questions = (site / "questions.html").read_text(encoding="utf-8")
    for question in (*QUESTIONS, FALLBACK_QUESTION):
        assert question.replace("'", "&#x27;") in questions
    assert "W200x27" in questions and "I could not route this question" in questions
    example = (site / "example.html").read_text(encoding="utf-8")
    assert "Equal to the gold extraction</td><td>yes" in example
    assert "not the\noutput of a language model" in example


def test_site_publishes_the_version_iri(site: Path) -> None:
    """owl:versionIRI is .../core/<version>; Pages serves it from core/<version>.html."""
    page = (site / "core" / f"{VERSION}.html").read_text(encoding="utf-8")
    assert f'href="{VERSION}.ttl"' in page and 'href="../style.css"' in page
    copy = (site / "core" / f"{VERSION}.ttl").read_text(encoding="utf-8")
    assert f'owl:versionInfo "{VERSION}"' in copy


def test_outline_zones_draws_on_the_page(site: Path) -> None:
    page = (site / "img" / "sheet-2.png").read_bytes()
    marked = outline_zones(page, ["0.1,0.1,0.3,0.2"])
    assert marked.startswith(b"\x89PNG") and marked != page
