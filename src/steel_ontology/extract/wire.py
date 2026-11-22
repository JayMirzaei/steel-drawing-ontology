"""The wire format a model answers in, and its decoding into typed objects.

Why not hand the model the full ``Extraction`` JSON Schema? It is a union of 59 classes with
more than 200 optional fields; structured-output modes limit schema size and optional fields,
and each provider limits them differently. So the constrained schema is deliberately small and
generic: a list of objects, each with an id, a class name, name/values pairs, a zone and a
confidence. The real contract (which fields a class has, what type each one is) is stated in the
prompt and enforced here with the pydantic models, and after that by the SHACL shapes.

Decoding never guesses: an unknown field, a value of the wrong type or a malformed zone is
dropped and reported as a problem, and the rest of the object is kept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, get_origin

from pydantic import ValidationError

from steel_ontology.enums import ExtractionConfidence
from steel_ontology.models import NODE_CLASSES, Node, rdf_fields

EXTRACTABLE = tuple(name for name in NODE_CLASSES if name != "Evidence")
"""Classes a model may return. Evidence is built by the pipeline from zone and confidence."""

EVIDENCE_PREFIX = "ev-"
"""Ids with this prefix are reserved for the Evidence objects the merge step creates."""

SHEET_SCHEMA_NAME = "sheet_extraction"
SHEET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["objects"],
    "properties": {
        "objects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "type", "fields", "zone", "confidence"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": list(EXTRACTABLE)},
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "values"],
                            "properties": {
                                "name": {"type": "string"},
                                "values": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                    "zone": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "confidence": {
                        "type": "string",
                        "enum": [member.value for member in ExtractionConfidence],
                    },
                },
            },
        }
    },
}


@dataclass(frozen=True)
class Sighting:
    """One object as one sheet states it: the typed node plus where it was read."""

    node: Node
    page: int
    zone: str | None
    confidence: ExtractionConfidence


@dataclass
class SheetExtraction:
    """Everything decoded from one page's answer."""

    page: int
    sightings: list[Sighting] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def decode_sheet(payload: dict[str, Any], page: int) -> SheetExtraction:
    """Turn one page's wire answer into typed nodes; collect what had to be dropped."""
    result = SheetExtraction(page)
    objects = payload.get("objects")
    if not isinstance(objects, list):
        result.problems.append(f"page {page}: the answer has no 'objects' list")
        return result
    for raw in objects:
        sighting = _decode_object(raw, page, result.problems)
        if sighting is not None:
            result.sightings.append(sighting)
    return result


def _decode_object(raw: Any, page: int, problems: list[str]) -> Sighting | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        problems.append(f"page {page}: skipped an object without an id")
        return None
    where = f"page {page}, {raw['id']}"
    if raw["id"].startswith(EVIDENCE_PREFIX):
        problems.append(f"{where}: ids starting with {EVIDENCE_PREFIX!r} are reserved, skipped")
        return None
    cls = NODE_CLASSES.get(str(raw.get("type")))
    if cls is None or raw.get("type") == "Evidence":
        problems.append(f"{where}: unknown class {raw.get('type')!r}, object skipped")
        return None
    values = _field_values(cls, raw.get("fields"), where, problems)
    node = _build(cls, raw["id"], values, where, problems)
    if node is None:
        return None
    try:
        confidence = ExtractionConfidence(raw.get("confidence"))
    except ValueError:
        problems.append(f"{where}: confidence {raw.get('confidence')!r} read as Unverified")
        confidence = ExtractionConfidence.UNVERIFIED
    return Sighting(node, page, _zone(raw.get("zone"), where, problems), confidence)


def _field_values(cls: type[Node], fields: Any, where: str, problems: list[str]) -> dict[str, Any]:
    """Name/values pairs -> constructor arguments (a single value or a list, per the model)."""
    allowed = rdf_fields(cls)
    values: dict[str, Any] = {}
    for item in fields if isinstance(fields, list) else []:
        name = item.get("name") if isinstance(item, dict) else None
        given = item.get("values") if isinstance(item, dict) else None
        if name not in allowed or name == "evidenced_by" or not isinstance(given, list):
            problems.append(f"{where}: {cls.__name__} has no field {name!r}, dropped")
            continue
        given = [value for value in given if isinstance(value, str) and value.strip()]
        if not given:
            continue
        if get_origin(cls.model_fields[name].annotation) is list:
            values.setdefault(name, []).extend(given)
        else:
            if name in values or len(given) > 1:
                problems.append(f"{where}: {name} takes one value, kept {given[0]!r}")
            values.setdefault(name, given[0])
    return values


def _build(
    cls: type[Node], node_id: str, values: dict[str, Any], where: str, problems: list[str]
) -> Node | None:
    """Construct the node; drop exactly the fields pydantic rejects and try once more."""
    try:
        return cls(id=node_id, **values)
    except ValidationError as error:
        bad = {str(issue["loc"][0]) for issue in error.errors() if issue["loc"]}
        if "id" in bad or not bad:
            problems.append(f"{where}: invalid id, object skipped")
            return None
        for name in sorted(bad):
            problems.append(f"{where}: {name}={values.get(name)!r} is not valid, dropped")
        kept = {name: value for name, value in values.items() if name not in bad}
        return cls(id=node_id, **kept)


def _zone(raw: Any, where: str, problems: list[str]) -> str | None:
    """Check a ``"x0,y0,x1,y1"`` box (fractions of the page, origin top-left)."""
    if raw is None:
        return None
    try:
        x0, y0, x1, y1 = (float(part) for part in str(raw).split(","))
    except ValueError:
        problems.append(f"{where}: zone {raw!r} is not 'x0,y0,x1,y1', dropped")
        return None
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        problems.append(f"{where}: zone {raw!r} is not inside the page, dropped")
        return None
    return str(raw).replace(" ", "")
