"""Typed objects <-> RDF.

``to_graph`` writes an ``Extraction`` as triples in the ontology's vocabulary; ``from_graph``
reads them back. The mapping is driven by the field metadata in ``steel_ontology.models``, so
there is no second list of properties to keep in step.

Round trip: ``from_graph(to_graph(x)) == x.normalised()``. RDF keeps neither order nor
duplicates, which is why the comparison is against the normalised form.
"""

from __future__ import annotations

import json
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin

from rdflib import OWL, RDF, XSD, Graph, Literal, URIRef
from rdflib.term import Node as RdfTerm

from steel_ontology.models import NODE_CLASSES, Extraction, Node, rdf_fields
from steel_ontology.vocabulary import STEEL, local_name


class GraphMappingError(ValueError):
    """The graph cannot be represented as typed objects without losing or guessing data."""


def to_graph(extraction: Extraction) -> Graph:
    """Write an extraction as RDF.

    Each object gets its most specific class as ``rdf:type``; superclasses follow from the
    ontology. Empty fields produce no triples.
    """
    graph = Graph()
    graph.bind("steel", STEEL)
    graph.bind("ex", extraction.base_iri)
    for node in extraction.nodes:
        subject = URIRef(extraction.base_iri + node.id)
        graph.add((subject, RDF.type, STEEL[type(node).__name__]))
        for name, (prop, target_class) in rdf_fields(type(node)).items():
            value = getattr(node, name)
            values = value if isinstance(value, list) else [] if value is None else [value]
            for item in values:
                graph.add((subject, STEEL[prop], _to_term(item, target_class, extraction.base_iri)))
    return graph


def from_graph(graph: Graph, base_iri: str | None = None, *, strict: bool = False) -> Extraction:
    """Read typed objects from RDF.

    ``base_iri`` is the namespace of the objects; when omitted it is taken from the data (all
    typed subjects must then share one namespace). Subjects without a class known to the models
    are skipped, which lets the ontology itself or inferred triples be present in the graph.

    With ``strict=True`` every triple about a loaded object must map to a field; anything else
    raises ``GraphMappingError``. Use it to prove that nothing was dropped.
    """
    subjects = _typed_subjects(graph)
    if base_iri is None:
        base_iri = _common_namespace(list(subjects))
    nodes = []
    for subject, cls in subjects.items():
        if not str(subject).startswith(base_iri):
            raise GraphMappingError(f"{subject} is outside the base IRI {base_iri}")
        nodes.append(_read_node(graph, subject, cls, base_iri, strict))
    extraction = Extraction(base_iri=base_iri, nodes=nodes)
    return extraction.normalised()


def _to_term(value: Any, target_class: str | None, base_iri: str) -> RdfTerm:
    if target_class is not None:
        return URIRef(base_iri + value)
    if isinstance(value, Enum):
        return STEEL[value.value]
    if isinstance(value, bool):
        return Literal(value, datatype=XSD.boolean)
    if isinstance(value, int):
        return Literal(value, datatype=XSD.integer)
    if isinstance(value, Decimal):
        return Literal(_decimal_text(value), datatype=XSD.decimal)
    return Literal(str(value))


def _decimal_text(value: Decimal) -> str:
    """Digits as given, in plain notation. Whole numbers gain ``.0``, Turtle's decimal form,
    so a graph in memory equals the same graph written to Turtle and read back."""
    text = format(value, "f")
    return text if "." in text else f"{text}.0"


def _typed_subjects(graph: Graph) -> dict[URIRef, type[Node]]:
    """Each IRI subject that has a model class, with its most specific class."""
    found: dict[URIRef, type[Node]] = {}
    for subject in set(graph.subjects(RDF.type, None)):
        if not isinstance(subject, URIRef) or str(subject).startswith(str(STEEL)):
            continue
        classes = [
            NODE_CLASSES[local_name(t)]
            for t in graph.objects(subject, RDF.type)
            if local_name(t) in NODE_CLASSES
        ]
        if not classes:
            continue
        most_specific = [
            c for c in classes if not any(o is not c and issubclass(o, c) for o in classes)
        ]
        if len(set(most_specific)) != 1:
            names = sorted(c.__name__ for c in set(most_specific))
            raise GraphMappingError(f"{subject} has unrelated classes {names}")
        found[subject] = most_specific[0]
    return found


def _common_namespace(subjects: list[URIRef]) -> str:
    if not subjects:
        raise GraphMappingError("no typed objects found, so no base IRI can be derived")
    namespaces = {_namespace_of(s) for s in subjects}
    if len(namespaces) != 1:
        raise GraphMappingError(
            f"objects live in several namespaces, pass base_iri: {sorted(namespaces)}"
        )
    return namespaces.pop()


def _namespace_of(iri: URIRef) -> str:
    text = str(iri)
    cut = max(text.rfind("#"), text.rfind("/"))
    return text[: cut + 1]


def _read_node(graph: Graph, subject: URIRef, cls: type[Node], base_iri: str, strict: bool) -> Node:
    data: dict[str, Any] = {"id": str(subject)[len(base_iri) :], "type": cls.__name__}
    consumed = set()
    for name, (prop, target_class) in rdf_fields(cls).items():
        objects = list(graph.objects(subject, STEEL[prop]))
        if not objects:
            continue
        consumed.add(STEEL[prop])
        annotation = cls.model_fields[name].annotation
        values = [_from_term(o, target_class, base_iri, subject, prop) for o in objects]
        if _is_list(annotation):
            data[name] = values
        elif len(values) == 1:
            data[name] = values[0]
        else:
            raise GraphMappingError(f"{subject} has {len(values)} values for single field {prop}")
    if strict:
        _refuse_unmapped(graph, subject, cls, consumed)
    return cls.model_validate(data)


def _from_term(
    term: RdfTerm, target_class: str | None, base_iri: str, subject: URIRef, prop: str
) -> Any:
    if target_class is not None:
        if not isinstance(term, URIRef) or not str(term).startswith(base_iri):
            raise GraphMappingError(f"{subject} {prop}: {term} is not an object under {base_iri}")
        return str(term)[len(base_iri) :]
    if isinstance(term, URIRef):
        return local_name(term)
    if isinstance(term, Literal):
        value = term.toPython()
        return str(term) if isinstance(value, Literal) else value
    raise GraphMappingError(f"{subject} {prop}: blank nodes cannot be mapped")


def _is_list(annotation: Any) -> bool:
    if get_origin(annotation) in (Union, UnionType):
        return any(_is_list(arg) for arg in get_args(annotation))
    return get_origin(annotation) is list


def _refuse_unmapped(graph: Graph, subject: URIRef, cls: type[Node], consumed: set[URIRef]) -> None:
    allowed_types = {STEEL[c.__name__] for c in cls.__mro__ if c.__name__ in NODE_CLASSES}
    allowed_types.add(OWL.NamedIndividual)
    for predicate, obj in graph.predicate_objects(subject):
        if predicate == RDF.type:
            if obj not in allowed_types:
                raise GraphMappingError(f"{subject} has unmapped type {obj}")
        elif predicate not in consumed:
            raise GraphMappingError(f"{subject} has unmapped property {predicate}")


RDF_FORMATS = {
    ".ttl": "turtle",
    ".nt": "nt",
    ".n3": "n3",
    ".rdf": "xml",
    ".owl": "xml",
    ".xml": "xml",
    ".jsonld": "json-ld",
}
"""RDF file extensions ``load_graph`` reads, and the rdflib parser used for each."""


def load_graph(path: str | Path) -> Graph:
    """Read a data file: extraction JSON (``.json``) or RDF in one of ``RDF_FORMATS``.

    The format comes from the extension, never from guessing. JSON-LD that names a remote
    ``@context`` (a URL or an ``@import``) is refused: resolving it would make this process
    fetch whatever URL the file names, which a server that accepts uploads must not do.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return to_graph(Extraction.from_json(path.read_text(encoding="utf-8")))
    if suffix not in RDF_FORMATS:
        known = ", ".join([".json", *RDF_FORMATS])
        raise ValueError(f"{path.name}: unknown file type {suffix or '(none)'}; use one of {known}")
    if RDF_FORMATS[suffix] == "json-ld":
        text = path.read_text(encoding="utf-8")
        remote = _remote_context(json.loads(text))
        if remote is not None:
            raise ValueError(f"{path.name}: remote JSON-LD contexts are not loaded ({remote})")
        return Graph().parse(data=text, format="json-ld")
    return Graph().parse(path, format=RDF_FORMATS[suffix])


def _remote_context(data: Any) -> str | None:
    """The first context reference in JSON-LD that would be fetched, or ``None``."""
    if isinstance(data, list):
        return next((found for item in data if (found := _remote_context(item))), None)
    if not isinstance(data, dict):
        return None
    for key, value in data.items():
        if key == "@context":
            contexts = value if isinstance(value, list) else [value]
            for context in contexts:
                if isinstance(context, str):
                    return context
                if isinstance(context, dict) and "@import" in context:
                    return str(context["@import"])
        found = _remote_context(value)
        if found is not None:
            return found
    return None
