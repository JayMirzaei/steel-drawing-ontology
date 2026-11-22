"""The vocabulary reference, generated from ``core.ttl`` and ``shapes.ttl``.

``build_reference`` reads the two files into plain records; ``to_markdown`` and ``to_html``
render them. Nothing here is written by hand, so the reference cannot drift from the ontology:
``tests/test_reference.py`` checks that ``docs/vocabulary.md`` is what this module produces.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from rdflib import OWL, RDF, RDFS, SH, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.term import Node as RdfTerm

from steel_ontology.vocabulary import (
    CORE_IRI,
    STEEL,
    VERSION,
    defined_classes,
    enumerations,
    load_ontology,
    load_shapes,
    local_name,
)


@dataclass(frozen=True)
class ClassEntry:
    """A class that data is written in (not a vocabulary, not reasoner-defined)."""

    name: str
    parents: tuple[str, ...]
    comment: str


@dataclass(frozen=True)
class PropertyEntry:
    name: str
    kind: str  # "object" or "datatype"
    functional: bool
    domain: str
    range: str
    comment: str


@dataclass(frozen=True)
class EnumerationEntry:
    """A closed vocabulary: the class and its fixed members."""

    name: str
    comment: str
    members: tuple[tuple[str, str], ...]  # (member, comment)


@dataclass(frozen=True)
class DefinedEntry:
    """A class whose membership a reasoner infers from its definition."""

    name: str
    definition: str
    comment: str


@dataclass(frozen=True)
class ShapeEntry:
    name: str
    target: str
    checks: tuple[tuple[str, str, str], ...]  # (severity, what is checked, message)


@dataclass(frozen=True)
class Reference:
    version: str
    classes: tuple[ClassEntry, ...]
    properties: tuple[PropertyEntry, ...]
    enumerations: tuple[EnumerationEntry, ...]
    defined: tuple[DefinedEntry, ...]
    shapes: tuple[ShapeEntry, ...]


def build_reference() -> Reference:
    """Read the ontology and the shapes into a ``Reference``."""
    graph = load_ontology()
    vocabularies = enumerations()
    defined = set(defined_classes())
    classes, defined_entries = [], []
    for cls in sorted(_named(graph.subjects(RDF.type, OWL.Class))):
        name = local_name(cls)
        comment = _comment(graph, cls)
        if name in defined:
            definition = graph.value(graph.value(cls, OWL.equivalentClass), OWL.intersectionOf)
            parts = [_class_expression(graph, part) for part in Collection(graph, definition)]
            defined_entries.append(DefinedEntry(name, " and ".join(parts), comment))
        elif name not in vocabularies:
            parents = sorted(local_name(p) for p in _named(graph.objects(cls, RDFS.subClassOf)))
            classes.append(ClassEntry(name, tuple(parents), comment))
    enumeration_entries = [
        EnumerationEntry(
            name,
            _comment(graph, STEEL[name]),
            tuple((member, _comment(graph, STEEL[member])) for member in members),
        )
        for name, members in sorted(vocabularies.items())
    ]
    return Reference(
        version=VERSION,
        classes=tuple(classes),
        properties=tuple(_properties(graph)),
        enumerations=tuple(enumeration_entries),
        defined=tuple(defined_entries),
        shapes=tuple(_shapes(load_shapes())),
    )


def _named(terms) -> list[URIRef]:
    return [t for t in terms if isinstance(t, URIRef) and str(t).startswith(str(STEEL))]


def _comment(graph: Graph, term: RdfTerm) -> str:
    text = graph.value(term, RDFS.comment)
    return " ".join(str(text).split()) if text is not None else ""


def _properties(graph: Graph) -> list[PropertyEntry]:
    entries = []
    for kind, rdf_type in (("object", OWL.ObjectProperty), ("datatype", OWL.DatatypeProperty)):
        for prop in _named(graph.subjects(RDF.type, rdf_type)):
            entries.append(
                PropertyEntry(
                    name=local_name(prop),
                    kind=kind,
                    functional=(prop, RDF.type, OWL.FunctionalProperty) in graph,
                    domain=_class_expression(graph, graph.value(prop, RDFS.domain)),
                    range=_class_expression(graph, graph.value(prop, RDFS.range)),
                    comment=_comment(graph, prop),
                )
            )
    return sorted(entries, key=lambda e: e.name.lower())


def _class_expression(graph: Graph, term: RdfTerm | None) -> str:
    """A class, union or restriction in a short readable form."""
    if term is None:
        return ""
    if isinstance(term, URIRef):
        return _short(term)
    union = graph.value(term, OWL.unionOf)
    if union is not None:
        return " or ".join(_class_expression(graph, part) for part in Collection(graph, union))
    prop = graph.value(term, OWL.onProperty)
    if prop is not None:
        value = graph.value(term, OWL.hasValue)
        if value is not None:
            return f"({_short(prop)} value {_short(value)})"
        some = graph.value(term, OWL.someValuesFrom)
        return f"({_short(prop)} some {_class_expression(graph, some)})"
    return "(anonymous class)"


def _short(term: RdfTerm) -> str:
    if isinstance(term, Literal):
        return str(term)
    text = str(term)
    return local_name(text) if text.startswith(str(STEEL)) else "xsd:" + text.rsplit("#", 1)[-1]


def _shapes(graph: Graph) -> list[ShapeEntry]:
    entries = []
    for shape in sorted(s for s in graph.subjects(RDF.type, SH.NodeShape) if isinstance(s, URIRef)):
        default = _severity(graph, shape, "Violation")
        checks = []
        for constraint in graph.objects(shape, SH.property):
            path = graph.value(constraint, SH.path)
            checks.append(
                (
                    _severity(graph, constraint, default),
                    f"{_short(path)}: {_constraint_summary(graph, constraint)}",
                    _message(graph, constraint),
                )
            )
        for constraint in graph.objects(shape, SH.sparql):
            checks.append((default, "SPARQL check", _message(graph, constraint)))
        entries.append(
            ShapeEntry(str(shape).rsplit("#", 1)[-1], _target(graph, shape), tuple(sorted(checks)))
        )
    return entries


def _target(graph: Graph, shape: URIRef) -> str:
    for predicate, wording in (
        (SH.targetClass, "every {}"),
        (SH.targetSubjectsOf, "anything with {}"),
        (SH.targetObjectsOf, "any value of {}"),
    ):
        targets = sorted(_short(t) for t in graph.objects(shape, predicate))
        if targets:
            return wording.format(", ".join(targets))
    return ""


def _severity(graph: Graph, node: RdfTerm, default: str) -> str:
    severity = graph.value(node, SH.severity)
    return str(severity).rsplit("#", 1)[-1] if severity is not None else default


def _message(graph: Graph, node: RdfTerm) -> str:
    return " ".join(" ".join(str(m).split()) for m in sorted(graph.objects(node, SH.message)))


_FACETS = (
    (SH.minCount, "at least {}"),
    (SH.maxCount, "at most {}"),
    (SH.datatype, "{}"),
    (SH["class"], "a {}"),
    (SH.minInclusive, ">= {}"),
    (SH.maxInclusive, "<= {}"),
    (SH.minExclusive, "> {}"),
    (SH.maxExclusive, "< {}"),
    (SH.pattern, "matches {}"),
)


def _constraint_summary(graph: Graph, constraint: RdfTerm) -> str:
    parts = [
        wording.format(_short(value))
        for predicate, wording in _FACETS
        if (value := graph.value(constraint, predicate)) is not None
    ]
    allowed = graph.value(constraint, SH["in"])
    if isinstance(allowed, BNode | URIRef):
        parts.append("one of " + ", ".join(_short(v) for v in Collection(graph, allowed)))
    return ", ".join(parts) or "constrained"


# ---------------------------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------------------------

_INTRO = (
    "Generated from `ontology/core.ttl` and `ontology/shapes.ttl` by `steel-ontology docs`. "
    "Do not edit by hand."
)


def _sections(ref: Reference) -> list[tuple[str, str, list[str], list[list[str]]]]:
    """``(title, lead, header, rows)`` for each part of the reference."""
    return [
        (
            f"Classes ({len(ref.classes)})",
            "Classes that extracted data is written in.",
            ["Class", "Subclass of", "Meaning"],
            [[c.name, ", ".join(c.parents), c.comment] for c in ref.classes],
        ),
        (
            f"Properties ({len(ref.properties)})",
            "A functional property takes one value per object. Values are stored as printed.",
            ["Property", "Kind", "Domain", "Range", "Meaning"],
            [
                [
                    p.name,
                    p.kind + (", functional" if p.functional else ""),
                    p.domain,
                    p.range,
                    p.comment,
                ]
                for p in ref.properties
            ],
        ),
        (
            f"Closed vocabularies ({len(ref.enumerations)})",
            "Each is a fixed list (owl:oneOf, all members different). "
            "A value outside the list is a validation error.",
            ["Vocabulary", "Members", "Meaning"],
            [[e.name, ", ".join(m for m, _ in e.members), e.comment] for e in ref.enumerations],
        ),
        (
            f"Reasoner-defined classes ({len(ref.defined)})",
            "Membership is inferred from the definition, never written by an extractor.",
            ["Class", "Definition", "Why it exists"],
            [[d.name, d.definition, d.comment] for d in ref.defined],
        ),
        (
            f"Shapes ({len(ref.shapes)})",
            "SHACL checks. A violation makes data non-conforming; a warning asks a person to look.",
            ["Shape", "Applies to", "Severity", "Check", "Message"],
            [
                [s.name, s.target, severity, what, message]
                for s in ref.shapes
                for severity, what, message in s.checks
            ],
        ),
    ]


def to_markdown(ref: Reference) -> str:
    """The reference as one Markdown document."""
    lines = [f"# Vocabulary reference (version {ref.version})", "", _INTRO, ""]
    lines += [f"Namespace: `{CORE_IRI}#` (prefix `steel:`).", ""]
    for title, lead, header, rows in _sections(ref):
        lines += [f"## {title}", "", lead, ""]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(" --- " for _ in header) + "|")
        for row in rows:
            cells = [cell.replace("|", "\\|") for cell in row]
            cells[0] = f"`{cells[0]}`"
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def to_html_body(ref: Reference) -> str:
    """The reference as an HTML fragment; each term gets an anchor equal to its local name.

    With the anchors, ``.../core#Beam`` lands on the row for ``Beam`` once this page is served
    at the ontology's IRI.
    """
    parts = [f"<p>Version {escape(ref.version)}. Namespace <code>{escape(CORE_IRI)}#</code>, "]
    parts.append("prefix <code>steel:</code>. Generated from the Turtle files; download ")
    parts.append('<a href="core.ttl">core.ttl</a> and <a href="shapes.ttl">shapes.ttl</a>.</p>')
    sections = _sections(ref)
    parts.append("<p>" + " · ".join(f'<a href="#{_slug(t)}">{escape(t)}</a>' for t, *_ in sections))
    parts.append("</p>")
    seen: set[str] = set()
    for title, lead, header, rows in sections:
        parts.append(f'<h2 id="{_slug(title)}">{escape(title)}</h2><p>{escape(lead)}</p>')
        parts.append("<table><thead><tr>")
        parts += [f"<th>{escape(cell)}</th>" for cell in header]
        parts.append("</tr></thead><tbody>")
        for row in rows:
            anchor = "" if row[0] in seen else f' id="{escape(row[0])}"'
            seen.add(row[0])
            parts.append(f"<tr{anchor}><td><code>{escape(row[0])}</code></td>")
            parts += [f"<td>{escape(cell)}</td>" for cell in row[1:]]
            parts.append("</tr>")
        parts.append("</tbody></table>")
    return "\n".join(parts)


def _slug(title: str) -> str:
    return "section-" + title.split(" (")[0].lower().replace(" ", "-")


def to_html(ref: Reference) -> str:
    """The reference as one self-contained HTML page (no external files)."""
    style = (
        "body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px}"
        "table{border-collapse:collapse;width:100%;font-size:14px}"
        "th,td{text-align:left;vertical-align:top;padding:4px 10px 4px 0;"
        "border-bottom:1px solid #ccc}"
        "code{font:13px ui-monospace,monospace}"
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Steel drawing ontology {escape(ref.version)}: vocabulary reference</title>"
        f"<style>{style}</style></head><body>"
        f"<h1>Vocabulary reference</h1>\n{to_html_body(ref)}\n</body></html>\n"
    )
