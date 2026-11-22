"""Merge the per-sheet readings into one extraction.

A drawing set says the same thing in several places: a beam is drawn on the plan, listed in a
schedule and cut in a detail. Each sheet is read on its own, so the merge is where those
sightings meet. Objects are matched by id only (the prompt fixes the id convention); nothing is
matched by similarity, because a wrong merge is worse than a duplicate that a person can see.

- List fields are united. A single field keeps the first value read; a different value on a
  later sheet is a *conflict*, reported and not resolved, because drawings do disagree with
  themselves and that is information for the reader.
- Two sightings of one id with unrelated classes are a conflict too; the first class wins.
- Every sighting with a zone becomes an ``Evidence`` object, so a merged fact cites every
  sheet it was read on.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from steel_ontology.extract.wire import EVIDENCE_PREFIX, SheetExtraction, Sighting
from steel_ontology.models import DrawingSet, Evidence, Extraction, Node, Sheet

SET_ID = "drawing-set"


@dataclass
class MergeResult:
    """The merged extraction and what the merge had to decide."""

    extraction: Extraction
    conflicts: list[str] = field(default_factory=list)


def merge_sheets(sheets: Iterable[SheetExtraction], base_iri: str) -> MergeResult:
    """Combine sheet readings (in page order) into one ``Extraction``."""
    conflicts: list[str] = []
    merged: dict[str, Node] = {}
    evidence: dict[str, list[Evidence]] = {}
    per_page: Counter[tuple[str, int]] = Counter()
    for sheet in sorted(sheets, key=lambda s: s.page):
        sheet_node = _sheet_of(sheet, conflicts)
        merged.setdefault(sheet_node.id, sheet_node)
        for sighting in sheet.sightings:
            node = sighting.node
            known = merged.get(node.id)
            merged[node.id] = node if known is None else _combine(known, sighting, conflicts)
            if sighting.zone is not None:
                cited = evidence.setdefault(node.id, [])
                per_page[node.id, sighting.page] += 1
                number = per_page[node.id, sighting.page]
                cited.append(_evidence(sighting, sheet_node.id, first=not cited, number=number))
        merged[sheet_node.id] = merged[sheet_node.id].model_copy(update={"page_index": sheet.page})
    for node_id, cited in evidence.items():
        merged[node_id] = merged[node_id].model_copy(update={"evidenced_by": [e.id for e in cited]})
    _complete_set(merged, conflicts)
    nodes = [*merged.values(), *(e for cited in evidence.values() for e in cited)]
    return MergeResult(Extraction(base_iri=base_iri, nodes=nodes), conflicts)


def _sheet_of(sheet: SheetExtraction, conflicts: list[str]) -> Sheet:
    """The Sheet object of a page; one is made up (and reported) when the reading has none."""
    found = [s.node for s in sheet.sightings if isinstance(s.node, Sheet)]
    if len(found) > 1:
        conflicts.append(
            f"page {sheet.page}: {len(found)} Sheet objects, evidence is filed under {found[0].id}"
        )
    if found:
        return found[0]
    conflicts.append(f"page {sheet.page}: no Sheet object was reported, one was added")
    return Sheet(id=f"sheet-page-{sheet.page}")


def _combine(known: Node, sighting: Sighting, conflicts: list[str]) -> Node:
    """Fold a later sighting into the object read so far."""
    new = sighting.node
    if isinstance(new, type(known)):
        base, other = new, known  # the later sighting is the same class or a more specific one
    elif isinstance(known, type(new)):
        base, other = known, new
    else:
        conflicts.append(
            f"{known.id}: read as {type(known).__name__} and, on page {sighting.page}, as "
            f"{type(new).__name__}; kept {type(known).__name__}"
        )
        return known
    updates = {}
    for name in type(other).model_fields:
        if name in ("id", "type"):
            continue
        first, second = getattr(known, name), getattr(new, name)
        if isinstance(first, list):
            updates[name] = [*first, *(item for item in second if item not in first)]
        elif first is None:
            updates[name] = second
        else:
            updates[name] = first
            if second is not None and second != first:
                conflicts.append(
                    f"{known.id}.{name}: {str(first)!r} first, {str(second)!r} on page "
                    f"{sighting.page}; kept the first"
                )
    return base.model_copy(update=updates)


def _evidence(sighting: Sighting, sheet_id: str, *, first: bool, number: int) -> Evidence:
    """Evidence for one sighting, ``number`` counting the object's sightings on this page.

    Ids: ``ev-<id>`` for the very first sighting, ``ev-<id>-p<page>`` for the first one on a
    later page, and ``ev-<id>-p<page>-<number>`` for the second and later on the same page (a
    mark drawn at several grid lines of one plan). Object ids never start with ``ev-``
    (``wire.decode_sheet`` refuses them), so these ids cannot collide with an object.
    """
    stem = f"{EVIDENCE_PREFIX}{sighting.node.id}"
    if first:
        evidence_id = stem
    elif number == 1:
        evidence_id = f"{stem}-p{sighting.page}"
    else:
        evidence_id = f"{stem}-p{sighting.page}-{number}"
    return Evidence(
        id=evidence_id,
        on_sheet=sheet_id,
        region_box=sighting.zone,
        confidence=sighting.confidence,
    )


def _complete_set(merged: dict[str, Node], conflicts: list[str]) -> None:
    """Make sure one drawing set lists every sheet."""
    sets = [node for node in merged.values() if isinstance(node, DrawingSet)]
    sheet_ids = [node.id for node in merged.values() if isinstance(node, Sheet)]
    if len(sets) > 1:
        names = ", ".join(s.id for s in sets)
        conflicts.append(
            f"several drawing sets were reported ({names}); sheets were not reassigned"
        )
        return
    current = sets[0] if sets else DrawingSet(id=SET_ID)
    missing = [sheet_id for sheet_id in sheet_ids if sheet_id not in current.has_sheet]
    merged[current.id] = current.model_copy(update={"has_sheet": [*current.has_sheet, *missing]})
