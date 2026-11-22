"""The extraction pipeline without a model: wire decoding, merge, pages, recorded replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import EXAMPLE
from steel_ontology import models
from steel_ontology.enums import ExtractionConfidence
from steel_ontology.extract import ProviderError, Request, extract_pdf, get_provider
from steel_ontology.extract.merge import merge_sheets
from steel_ontology.extract.pages import page_count, parse_page_ranges, render_pages
from steel_ontology.extract.prompt import field_catalogue, sheet_prompt, system_prompt
from steel_ontology.extract.wire import SHEET_SCHEMA, decode_sheet
from steel_ontology.models import Extraction

PDF = EXAMPLE / "drawings.pdf"
RECORDED = EXAMPLE / "recorded"
BASE = "https://example.org/kestrel-platform/"


def wire(node_id: str, cls: str, zone: str | None = "0.1,0.1,0.2,0.2", **fields: list[str]):
    return {
        "id": node_id,
        "type": cls,
        "fields": [{"name": name, "values": values} for name, values in fields.items()],
        "zone": zone,
        "confidence": "Verified",
    }


# ---- wire format ----------------------------------------------------------------------------


def _objects(schema: dict) -> list[dict]:
    found = [schema] if schema.get("type") == "object" else []
    for value in schema.values():
        children = value if isinstance(value, list) else [value]
        for child in children:
            if isinstance(child, dict):
                found += _objects(child)
    return found


def test_sheet_schema_fits_strict_structured_output() -> None:
    """Every object closes its properties and requires all of them (the strictest provider)."""
    objects = _objects(SHEET_SCHEMA)
    assert len(objects) == 3
    for item in objects:
        assert item["additionalProperties"] is False
        assert set(item["required"]) == set(item["properties"])
    classes = SHEET_SCHEMA["properties"]["objects"]["items"]["properties"]["type"]["enum"]
    assert "Beam" in classes and "Evidence" not in classes


def test_decode_coerces_strings_to_the_model_types() -> None:
    payload = {
        "objects": [
            wire(
                "column-C1",
                "Column",
                tag=["C1"],
                required_quantity=["4"],
                cut_length_mm=["4200"],
                revised_in_this_issue=["true"],
                element_status=["NewWork"],
                grid_location_text=["A/1", "A/2"],
            )
        ]
    }
    sheet = decode_sheet(payload, page=3)
    assert sheet.problems == []
    (sighting,) = sheet.sightings
    column = sighting.node
    assert isinstance(column, models.Column)
    assert (column.required_quantity, str(column.cut_length_mm)) == (4, "4200")
    assert column.revised_in_this_issue is True
    assert column.grid_location_text == ["A/1", "A/2"]
    assert (sighting.page, sighting.zone) == (3, "0.1,0.1,0.2,0.2")
    assert sighting.confidence is ExtractionConfidence.VERIFIED


def test_decode_drops_what_it_cannot_use_and_says_so() -> None:
    payload = {
        "objects": [
            wire("beam-B1", "Beam", tag=["B1", "B9"], colour=["red"], required_quantity=["many"]),
            wire("thing-1", "Gizmo"),
            wire("ev-beam-B1", "Beam"),
            wire("beam B2", "Beam"),
            wire("beam-B3", "Beam", zone="0.5,0.5,0.4,0.9"),
            {"type": "Beam"},
            {**wire("beam-B4", "Beam"), "confidence": "Certain"},
        ]
    }
    sheet = decode_sheet(payload, page=1)
    kept = {s.node.id: s for s in sheet.sightings}
    assert set(kept) == {"beam-B1", "beam-B3", "beam-B4"}
    assert kept["beam-B1"].node.tag == "B1"
    assert kept["beam-B1"].node.required_quantity is None
    assert kept["beam-B3"].zone is None
    assert kept["beam-B4"].confidence is ExtractionConfidence.UNVERIFIED
    text = "\n".join(sheet.problems)
    for expected in (
        "tag takes one value, kept 'B1'",
        "Beam has no field 'colour'",
        "required_quantity='many' is not valid",
        "unknown class 'Gizmo'",
        "ids starting with 'ev-' are reserved",
        "beam B2: invalid id",
        "is not inside the page",
        "skipped an object without an id",
        "confidence 'Certain' read as Unverified",
    ):
        assert expected in text, expected


def test_decode_reports_an_answer_without_objects() -> None:
    assert decode_sheet({"items": []}, page=2).problems == [
        "page 2: the answer has no 'objects' list"
    ]


# ---- merge ----------------------------------------------------------------------------------


def _merge(*pages: list[dict]):
    sheets = [decode_sheet({"objects": objects}, page) for page, objects in enumerate(pages, 1)]
    return merge_sheets(sheets, BASE)


def test_merge_unites_sightings_and_cites_every_sheet() -> None:
    result = _merge(
        [
            wire("sheet-S-1", "Sheet", sheet_number=["S-1"]),
            wire("drawing-set", "DrawingSet", zone=None, has_sheet=["sheet-S-1"]),
            wire("beam-B1", "Member", tag=["B1"], grid_location_text=["A/1"]),
        ],
        [
            wire("sheet-S-2", "Sheet", sheet_number=["S-2"]),
            wire("drawing-set", "DrawingSet", zone=None, has_sheet=["sheet-S-2"]),
            wire("beam-B1", "Beam", section_text=["W310x39"], grid_location_text=["A/1", "A/2"]),
        ],
    )
    assert result.conflicts == []
    extraction = result.extraction
    beam = extraction.get("beam-B1")
    assert isinstance(beam, models.Beam)  # the more specific class wins
    assert (beam.tag, beam.section_text) == ("B1", "W310x39")
    assert beam.grid_location_text == ["A/1", "A/2"]
    assert beam.evidenced_by == ["ev-beam-B1", "ev-beam-B1-p2"]
    assert [e.on_sheet for e in extraction.evidence_for(beam)] == ["sheet-S-1", "sheet-S-2"]
    assert extraction.get("drawing-set").has_sheet == ["sheet-S-1", "sheet-S-2"]
    assert extraction.get("sheet-S-2").page_index == 2
    assert extraction.dangling_references() == []


def test_merge_reports_conflicts_instead_of_resolving_them() -> None:
    result = _merge(
        [wire("sheet-S-1", "Sheet"), wire("beam-B1", "Beam", tag=["B1"], required_quantity=["4"])],
        [wire("sheet-S-2", "Sheet"), wire("beam-B1", "Beam", required_quantity=["5"])],
        [wire("sheet-S-3", "Sheet"), wire("beam-B1", "Column")],
    )
    assert result.extraction.get("beam-B1").required_quantity == 4
    assert result.conflicts == [
        "beam-B1.required_quantity: '4' first, '5' on page 2; kept the first",
        "beam-B1: read as Beam and, on page 3, as Column; kept Beam",
    ]


def test_merge_numbers_repeated_sightings_on_one_page() -> None:
    """A mark drawn at several grid lines of one plan is one object with several sightings."""
    result = _merge(
        [wire("sheet-S-1", "Sheet"), wire("beam-B1", "Beam"), wire("beam-B1", "Beam")],
        [
            wire("sheet-S-2", "Sheet"),
            wire("beam-B1", "Beam", zone="0.1,0.1,0.2,0.2"),
            wire("beam-B1", "Beam", zone="0.5,0.5,0.6,0.6"),
            wire("beam-B1", "Beam", zone="0.7,0.7,0.8,0.8"),
        ],
    )
    beam = result.extraction.get("beam-B1")
    assert beam.evidenced_by == [
        "ev-beam-B1",
        "ev-beam-B1-p1-2",
        "ev-beam-B1-p2",
        "ev-beam-B1-p2-2",
        "ev-beam-B1-p2-3",
    ]
    zones = [e.region_box for e in result.extraction.evidence_for(beam)]
    assert zones[2:] == ["0.1,0.1,0.2,0.2", "0.5,0.5,0.6,0.6", "0.7,0.7,0.8,0.8"]


def test_merge_survives_a_page_read_twice() -> None:
    page = [wire("sheet-S-1", "Sheet"), wire("beam-B1", "Beam")]
    sheets = [decode_sheet({"objects": page}, 1) for _ in range(3)]
    beam = merge_sheets(sheets, BASE).extraction.get("beam-B1")
    assert beam.evidenced_by == ["ev-beam-B1", "ev-beam-B1-p1-2", "ev-beam-B1-p1-3"]


def test_merge_adds_a_missing_sheet_and_set() -> None:
    result = _merge([wire("beam-B1", "Beam")])
    assert result.conflicts == ["page 1: no Sheet object was reported, one was added"]
    extraction = result.extraction
    assert extraction.get("sheet-page-1").page_index == 1
    assert extraction.get("drawing-set").has_sheet == ["sheet-page-1"]
    assert extraction.evidence_for(extraction.get("beam-B1"))[0].on_sheet == "sheet-page-1"


# ---- pages ----------------------------------------------------------------------------------


def test_pages_render_to_png_with_their_text_layer() -> None:
    assert page_count(PDF) == 4
    pages = list(render_pages(PDF, pages=[2], max_edge=400))
    (page,) = pages
    assert page.number == 2
    assert page.png.startswith(b"\x89PNG")
    assert "PLATFORM FRAMING PLAN" in page.text
    assert page.width > page.height  # a landscape sheet
    with pytest.raises(ValueError, match=r"outside 1\.\.4"):
        list(render_pages(PDF, pages=[5]))


def test_page_ranges() -> None:
    assert parse_page_ranges("1,3-5") == [1, 3, 4, 5]
    assert parse_page_ranges("1,1,2-3,2") == [1, 2, 3]  # a page is read once
    for bad in ("0", "3-2", "a"):
        with pytest.raises(ValueError):
            parse_page_ranges(bad)


# ---- prompt ---------------------------------------------------------------------------------


def test_prompt_states_the_contract_in_the_ontologys_words() -> None:
    catalogue = field_catalogue()
    assert "Beam (a Member: has all its fields)" in catalogue
    assert "section_text [one, text]: Printed profile or plate designation" in catalogue
    assert "annotation_origin [one of EngineerOrigin | ThirdPartyOrigin]" in catalogue
    assert "has_view [many, ids of View]" in catalogue
    assert "evidenced_by" not in catalogue
    assert system_prompt().startswith("You read one sheet")
    (page,) = render_pages(PDF, pages=[1], max_edge=200)
    prompt = sheet_prompt(page, 4)
    assert prompt.startswith("This is page 1 of 4.")
    assert "GENERAL NOTES" in prompt


# ---- the whole pipeline, offline ------------------------------------------------------------


def test_recorded_run_reproduces_the_gold_extraction() -> None:
    provider = get_provider("recorded", recorded=RECORDED)
    result = extract_pdf(PDF, provider, base_iri=BASE)
    gold = Extraction.from_json((EXAMPLE / "gold.json").read_text(encoding="utf-8"))
    assert result.extraction.normalised() == gold.normalised()
    assert result.problems == ()
    assert result.pages == (1, 2, 3, 4)
    assert (result.provider, result.model) == ("recorded", "recording:recorded")
    assert result.report.conforms and result.report.findings == ()
    assert result.ok
    assert result.unevidenced() == ["drawing-set", "zone-platform"]


def test_recording_is_labelled_as_fixture_data() -> None:
    readme = (RECORDED / "README.md").read_text(encoding="utf-8")
    assert "not** the output of a language model" in readme
    page = json.loads((RECORDED / "page-002.json").read_text(encoding="utf-8"))
    assert {o["id"] for o in page["objects"]} >= {"sheet-S-101", "beam-B1", "drawing-set"}


class _Flaky:
    """Answers page 1 from the recording, fails on page 2 and returns bad JSON for page 3."""

    name = "flaky"
    model = "test"

    def __init__(self) -> None:
        self.requests: list[Request] = []

    def complete(self, request: Request) -> str:
        self.requests.append(request)
        if request.key == "page-002":
            raise ProviderError("boom")
        if request.key == "page-003":
            return "not json"
        return (RECORDED / f"{request.key}.json").read_text(encoding="utf-8")


def test_a_failed_page_is_reported_and_the_rest_is_kept(tmp_path: Path) -> None:
    provider = _Flaky()
    saved = tmp_path / "answers"
    result = extract_pdf(PDF, provider, pages=[1, 2, 3], base_iri=BASE, save_responses=saved)
    assert [r.key for r in provider.requests] == ["page-001", "page-002", "page-003"]
    first = provider.requests[0]
    assert first.images[0].startswith(b"\x89PNG") and first.schema is SHEET_SCHEMA
    assert result.problems[0] == "page 2: no usable answer (boom)"
    assert result.problems[1].startswith("page 3: no usable answer (flaky returned text")
    assert any(p.startswith("dangling link: ") for p in result.problems)
    assert not result.ok
    assert result.extraction.get("clause-1").clause_number == "1"
    assert [p.name for p in saved.iterdir()] == ["page-001.json"]
    replay = extract_pdf(PDF, get_provider("recorded", recorded=saved), pages=[1], base_iri=BASE)
    assert replay.extraction.get("clause-1") == result.extraction.get("clause-1")


class _FallsBack:
    """Answers from the recording; page 2 is answered by another model, as a fallback would."""

    name = "fallback-test"
    model = "chosen-model"

    def __init__(self) -> None:
        self.last_model: str | None = None

    def complete(self, request: Request) -> str:
        self.last_model = "fallback-model" if request.key == "page-002" else self.model
        return (RECORDED / f"{request.key}.json").read_text(encoding="utf-8")


def test_the_model_that_answered_is_recorded() -> None:
    result = extract_pdf(PDF, _FallsBack(), pages=[1, 2, 3], base_iri=BASE)
    assert result.model == "chosen-model, fallback-model"
    assert "page 2: answered by fallback-model, not chosen-model" in result.problems
    assert not result.ok
