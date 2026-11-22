"""The recorded answers of the example: the gold extraction, split by sheet, in wire format.

IMPORTANT: this is fixture data written by this script from the gold extraction. It is NOT the
output of any language model and says nothing about how well a model reads these sheets. It
exists so that the extraction pipeline (render, decode, merge, validate) can run and be tested
offline, with answers a perfect reader would give.

How the gold objects are dealt out to pages:

- an object with evidence goes to the page its evidence cites, with that zone and confidence;
- the drawing set appears on every page, as a per-sheet reading would report it: each
  page says "the set has this sheet", and the first page carries the set-level facts, so the
  merge step has real work to do;
- anything else without evidence (the load zone) goes to the page that first links to it.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from steel_ontology import models as M
from steel_ontology.ask import ask_key

README = """\
# Recorded answers (fixture data, not model output)

The `page-NNN.json` files in this folder were written by `examples/generator/recorded.py` from
the gold extraction (`../gold.json`). They are in the wire format a model provider returns, one
file per page of `../drawings.pdf`. The `ask-*.json` file is a hand-written answer for the
question router's model fallback.

They are **not** the output of a language model, and they are not an accuracy result. They let
the pipeline run offline:

    steel-ontology extract examples/kestrel-platform/drawings.pdf \\
        --provider recorded --recorded examples/kestrel-platform/recorded

A recording of a real model run has the same layout: `steel-ontology extract ... --provider
anthropic --save-responses DIR` writes one.
"""

FALLBACK_QUESTION = "Who has to be told before coming to site?"
"""A question the keyword router does not recognise; the recorded answer routes it."""
FALLBACK_ANSWER = {  # follows steel_ontology.ask.ask_schema()
    "query": "requirement-clauses",
    "params": [{"name": "topic", "value": "InspectionReq"}],
}


def write_recording(gold: M.Extraction, folder: Path) -> None:
    """Write ``page-NNN.json`` for every sheet, the ask fallback answer and the README."""
    folder.mkdir(parents=True, exist_ok=True)
    for page, objects in sorted(_by_page(gold).items()):
        text = json.dumps({"objects": objects}, indent=1, ensure_ascii=False) + "\n"
        (folder / f"page-{page:03d}.json").write_text(text, encoding="utf-8")
    answer = json.dumps(FALLBACK_ANSWER, indent=1) + "\n"
    (folder / f"{ask_key(FALLBACK_QUESTION)}.json").write_text(answer, encoding="utf-8")
    (folder / "README.md").write_text(README, encoding="utf-8")


def _by_page(gold: M.Extraction) -> dict[int, list[dict[str, object]]]:
    sheets = {sheet.id: sheet for sheet in gold.of_type(M.Sheet)}
    pages: dict[int, list[dict[str, object]]] = {sheet.page_index: [] for sheet in sheets.values()}
    first_page = min(pages)
    for node in gold.nodes:
        if isinstance(node, M.Evidence):
            continue
        if isinstance(node, M.DrawingSet):
            for sheet in sheets.values():
                fields = _fields(node) if sheet.page_index == first_page else {}
                fields["has_sheet"] = [sheet.id]
                pages[sheet.page_index].append(_wire(node, fields, None))
            continue
        cited = gold.evidence_for(node)
        if cited:
            (evidence,) = cited
            page = sheets[evidence.on_sheet].page_index
            pages[page].append(_wire(node, _fields(node), evidence))
        else:
            pages[_page_of_first_link(gold, sheets, node.id)].append(
                _wire(node, _fields(node), None)
            )
    return pages


def _page_of_first_link(gold: M.Extraction, sheets: dict[str, M.Sheet], target: str) -> int:
    """Page of the first evidenced object that links to ``target``."""
    for node in gold.nodes:
        linked = any(
            target in (value if isinstance(value, list) else [value])
            for name, value in node
            if name not in ("id", "evidenced_by")
        )
        cited = gold.evidence_for(node)
        if linked and cited:
            return sheets[cited[0].on_sheet].page_index
    return min(sheet.page_index for sheet in sheets.values())


def _fields(node: M.Node) -> dict[str, list[str]]:
    """Every filled field of a node as a list of strings (the wire form of values)."""
    fields = {}
    for name in M.rdf_fields(type(node)):
        value = getattr(node, name)
        if name == "evidenced_by" or value is None or value == []:
            continue
        if isinstance(node, M.Sheet) and name == "page_index":
            continue  # the pipeline knows the page; a model is not asked for it
        fields[name] = [_text(item) for item in (value if isinstance(value, list) else [value])]
    return fields


def _text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return value.value if isinstance(value, Enum) else str(value)


def _wire(
    node: M.Node, fields: dict[str, list[str]], evidence: M.Evidence | None
) -> dict[str, object]:
    return {
        "id": node.id,
        "type": type(node).__name__,
        "fields": [{"name": name, "values": values} for name, values in fields.items()],
        "zone": evidence.region_box if evidence else None,
        "confidence": evidence.confidence.value if evidence else "Verified",
    }
