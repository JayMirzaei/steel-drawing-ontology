"""The synthetic example: drawing, gold extraction and broken variant stay in step."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest
from rdflib import Graph

import generate
from conftest import EXAMPLE
from generator import job
from steel_ontology import models
from steel_ontology.graph import from_graph, to_graph
from steel_ontology.models import Extraction
from steel_ontology.queries import run_query
from steel_ontology.reason import infer
from steel_ontology.validate import ValidationReport, validate

BASE = "https://example.org/kestrel-platform/"
DATA_FILES = ("gold.json", "gold.ttl", "broken.json", "broken.ttl")


@pytest.fixture(scope="module")
def gold() -> Extraction:
    return Extraction.from_json((EXAMPLE / "gold.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def broken_report() -> ValidationReport:
    return validate(Extraction.from_json((EXAMPLE / "broken.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def pages() -> list[pymupdf.Page]:
    document = pymupdf.open(EXAMPLE / "drawings.pdf")
    return list(document)


def test_committed_files_match_a_fresh_run(tmp_path: Path) -> None:
    generate.write_example(tmp_path)
    for name in DATA_FILES:
        assert (tmp_path / name).read_text() == (EXAMPLE / name).read_text(), name
    recorded = sorted(p.name for p in (EXAMPLE / "recorded").iterdir())
    assert recorded == sorted(p.name for p in (tmp_path / "recorded").iterdir())
    for name in recorded:
        fresh_text = (tmp_path / "recorded" / name).read_text()
        assert fresh_text == (EXAMPLE / "recorded" / name).read_text(), name
    fresh = [page.get_text() for page in pymupdf.open(tmp_path / "drawings.pdf")]
    committed = [page.get_text() for page in pymupdf.open(EXAMPLE / "drawings.pdf")]
    assert fresh == committed


def test_pdf_is_a_vector_set_with_the_expected_sheets(pages: list[pymupdf.Page]) -> None:
    assert len(pages) == len(job.SHEETS) == 4
    for page, sheet in zip(pages, job.SHEETS, strict=True):
        text = page.get_text()
        assert sheet.number in text
        assert sheet.title in text
        assert job.DISCLAIMER in text
        assert "ISSUED FOR CONSTRUCTION" in text
        assert page.get_images() == []  # drawn, not scanned
        assert len(page.get_drawings()) > 10


def test_printed_schedule_total_is_the_sum_of_the_rows() -> None:
    assert sum(row.weight_kg for row in job.COLUMN_ROWS) == job.COLUMN_TOTAL_KG


def test_gold_is_closed_and_json_and_turtle_agree(gold: Extraction) -> None:
    assert gold.dangling_references() == []
    from_turtle = from_graph(Graph().parse(EXAMPLE / "gold.ttl"), BASE, strict=True)
    assert from_turtle == gold.normalised()


def test_every_fact_has_evidence_except_the_set_and_the_zone(gold: Extraction) -> None:
    without = {
        n.id for n in gold.nodes if not n.evidenced_by and not isinstance(n, models.Evidence)
    }
    assert without == {"drawing-set", "zone-platform"}


def _cited_text(pages: list[pymupdf.Page], gold: Extraction, node: models.Node) -> str:
    """Text found on the sheet inside the zone that the node's evidence points at."""
    (evidence,) = gold.evidence_for(node)
    sheet = gold.get(evidence.on_sheet)
    assert isinstance(sheet, models.Sheet)
    page = pages[sheet.page_index - 1]
    x0, y0, x1, y1 = (float(v) for v in evidence.region_box.split(","))
    width, height = page.rect.width, page.rect.height
    clip = pymupdf.Rect(x0 * width - 2, y0 * height - 2, x1 * width + 2, y1 * height + 2)
    return " ".join(page.get_text(clip=clip).split())


def test_evidence_zones_contain_what_they_cite(pages: list[pymupdf.Page], gold: Extraction) -> None:
    """Follow each citation back to the PDF and read the printed value there."""
    for member in gold.of_type(models.Member):
        text = _cited_text(pages, gold, member)
        assert member.tag in text
        assert member.section_text in text
    for clause in gold.of_type(models.RequirementClause):
        assert _cited_text(pages, gold, clause).startswith(f"{clause.clause_number}. ")
    for cell in gold.of_type(models.ScheduleCell):
        assert _cited_text(pages, gold, cell) == cell.cell_text
    for revision in gold.of_type(models.Revision):
        text = _cited_text(pages, gold, revision)
        assert text.startswith(f"{revision.revision_code} {revision.revision_date}")
    schedule = gold.get("schedule-columns")
    assert str(schedule.declared_total) in _cited_text(pages, gold, schedule)
    stamp = gold.get("annotation-received-stamp")
    assert "RECEIVED" in _cited_text(pages, gold, stamp)


def test_gold_validates_with_no_finding(gold: Extraction) -> None:
    """The prohibition note prints no number, so it is not asked for a value (regression)."""
    report = validate(gold)
    assert report.conforms
    assert report.findings == ()


def test_broken_variant_fails_with_the_expected_messages(broken_report: ValidationReport) -> None:
    assert not broken_report.conforms
    violations = {
        (f.focus_node.removeprefix(BASE), f.path.rsplit("#")[-1]) for f in broken_report.violations
    }
    assert violations == {
        ("annotation-received-stamp", "annotationOrigin"),
        ("default-brace-connections", "defaultPercent"),
        ("ev-beam-B1", "confidence"),
        ("force-C1-Cf", "isFactored"),
        ("sheet-S-301", "sheetKind"),
    }
    messages = [f.message for f in broken_report.findings]
    assert "Loads must be tagged factored or unfactored; mixing them is a design error." in messages
    assert "A default percentage must be above 0 and at most 100." in messages
    assert "Every annotation must say whether the engineer or a third party drew it." in messages


def test_broken_variant_trips_the_schedule_arithmetic(broken_report: ValidationReport) -> None:
    (finding,) = [f for f in broken_report.warnings if f.focus_node == BASE + "schedule-columns"]
    assert finding.message.startswith("Printed schedule total differs from the sum of its rows")


def test_reasoner_classifies_the_gold_set(gold: Extraction) -> None:
    result = infer(to_graph(gold))
    assert result.consistent
    expected = {
        "drawing-set": "MarkedUpSet",
        "sheet-S-101": "MarkedUpSheet",
        "sheet-S-001": "SteelRelevantSheet",
        "annotation-received-stamp": "ThirdPartyMarkup",
        "connection-brace": "ConnectionToBeDesignedByOthers",
        "row-C1": "RowWithForces",
        "cell-BP1-3": "SupplierValueCell",
        "clause-4": "ProhibitionClause",
    }
    for node, cls in expected.items():
        assert cls in result.types_of(BASE + node), node
    assert "MarkedUpSheet" not in result.types_of(BASE + "sheet-S-201")
    assert "ThirdPartyMarkup" not in result.types_of(BASE + "annotation-revision-cloud")
    assert "RowWithForces" not in result.types_of(BASE + "row-P1")


def test_competency_queries_answer_on_the_gold_set(gold: Extraction) -> None:
    graph = to_graph(gold)
    marked = run_query(graph, "marked-up-sheets")
    assert set(marked.column("sheetNumber")) == {"S-101"}
    assert sorted(marked.column("markupKind")) == ["QueryNote", "ReceivedStamp", "TakeoffHighlight"]

    rule = run_query(graph, "default-rules", ruleKind="PercentOfYieldRule").rows
    assert [row["percent"] for row in rule] == [Decimal("50")]
    assert "50% OF THE TENSILE YIELD RESISTANCE" in rule[0]["text"]

    cells = run_query(graph, "schedule-cells-by-kind")
    assert cells.column("text") == ["BY FOUNDATION SUPPLIER"] * 2
    (live,) = run_query(graph, "area-loads-by-zone", loadType="LiveLoad").rows
    assert (live["zone"], live["kPa"]) == (BASE + "zone-platform", Decimal("4.8"))
    assert run_query(graph, "requirement-clauses").column("value") == ["6 mm"]
