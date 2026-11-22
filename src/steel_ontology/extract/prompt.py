"""The instructions given to a model for one sheet.

The system text is the same for every page of every drawing set, so a provider can cache it. It
states the reading rules and then the field catalogue, which is generated from the typed models
and therefore from the ontology: class comments and property comments are the ontology's own.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from functools import cache
from types import UnionType
from typing import Any, Union, get_args, get_origin

from steel_ontology.extract.pages import Page
from steel_ontology.extract.wire import EXTRACTABLE
from steel_ontology.models import NODE_CLASSES, Node, rdf_fields
from steel_ontology.vocabulary import comments

RULES = """\
You read one sheet of a structural steel drawing set and report what is printed on it as typed
objects. A fabricator will rely on the result, so accuracy matters more than coverage.

Rules
1. Report only what this sheet shows. Never fill a gap from memory or from what is usual.
2. Keep values as printed: dates, units, marks, cell text and clause text are copied, not
   normalised. Numbers are written as on the sheet ("1249.6").
3. Every object has an id, a class, its fields, a zone and a confidence.
   - id: lower-case class word, a hyphen, then the printed mark or number: "beam-B1",
     "column-C2", "clause-4", "sheet-S-101", "revision-S-101-A". Use only letters, digits, ".",
     "_" and "-". The same thing must get the same id on every sheet, because objects from all
     sheets are merged by id. The whole drawing set is always "drawing-set".
   - zone: where on the sheet you read it, as "x0,y0,x1,y1" in fractions of the page width and
     height, origin at the top-left corner, for example "0.12,0.30,0.25,0.34". Use null only for
     an object that has no place on the sheet (the drawing set itself, a load zone).
   - confidence: "Verified" when the text is clear and unambiguous, "Probable" when you had to
     interpret (a crowded leader, an abbreviation), "Unverified" when you are not sure.
4. Fields are name/values pairs; values are always strings. A field marked "one" takes exactly
   one value. A link field takes the ids of other objects. An enumeration field takes one of
   the listed names exactly. Booleans are "true" or "false". Leave out fields the sheet does not
   state.
5. Report exactly one Sheet object for this page (sheet number, title, kind, revisions). Add a
   "drawing-set" object carrying has_sheet with this sheet's id, plus any set-level facts this
   sheet prints.
6. Third-party markup (highlights, stamps, hand notes) is reported as Annotation objects with
   annotation_origin, never mixed into the design data.
"""


def system_prompt() -> str:
    """Reading rules plus the catalogue of classes and fields."""
    return RULES + "\nClasses and fields\n" + field_catalogue()


def sheet_prompt(page: Page, total_pages: int) -> str:
    """The per-page instruction: page position and the page's own text layer."""
    text = page.text.strip()
    layer = (
        f"Text layer of this page (exact characters, reading order not guaranteed):\n{text}"
        if text
        else "This page has no text layer (a scan): read everything from the image."
    )
    return (
        f"This is page {page.number} of {total_pages}. The image shows the whole sheet.\n"
        f"{layer}\n\nReport the objects on this sheet."
    )


@cache
def field_catalogue() -> str:
    """One block per class: its comment, its parent, and the fields it adds."""
    described = comments()
    blocks = []
    for name in EXTRACTABLE:
        cls = NODE_CLASSES[name]
        parent = cls.__mro__[1]
        inherited = set(rdf_fields(parent)) if parent is not Node else set(rdf_fields(Node))
        head = name if parent is Node else f"{name} (a {parent.__name__}: has all its fields)"
        lines = [f"{head}: {described.get(name, '')}".rstrip(": ")]
        for field_name, (prop, target) in rdf_fields(cls).items():
            if field_name in inherited or field_name == "evidenced_by":
                continue
            kind = _kind(cls.model_fields[field_name].annotation, target)
            comment = described.get(prop, "")
            lines.append(f"  {field_name} [{kind}]" + (f": {comment}" if comment else ""))
        blocks.append("\n".join(lines))
    common = "Every class also has: cites_standard [many, ids of Standard]"
    return common + "\n\n" + "\n\n".join(blocks)


def _kind(annotation: Any, target: str | None) -> str:
    """Describe a field's cardinality and value type in a few words."""
    many = get_origin(annotation) is list
    inner = get_args(annotation)[0] if many else _unwrap_optional(annotation)
    count = "many" if many else "one"
    if target is not None:
        return f"{count}, {'ids' if many else 'id'} of {target}"
    if isinstance(inner, type) and issubclass(inner, Enum):
        return f"{count} of " + " | ".join(member.value for member in inner)
    names = {str: "text", bool: "true/false", int: "whole number", Decimal: "number"}
    return f"{count}, {names.get(inner, 'text')}"


def _unwrap_optional(annotation: Any) -> Any:
    if get_origin(annotation) in (Union, UnionType):
        return next(arg for arg in get_args(annotation) if arg is not type(None))
    return annotation
