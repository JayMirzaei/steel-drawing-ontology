"""Access to the ontology files: namespaces, loaders and small lookups.

The vocabulary is kept at the repository root (``ontology/``) so it is easy to find, cite and
publish. A built wheel carries a copy inside the package; ``ontology_dir`` finds whichever is
present.
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Namespace, URIRef
from rdflib.collection import Collection

CORE_IRI = "https://jaymirzaei.github.io/steel-drawing-ontology/core"
SHAPES_IRI = "https://jaymirzaei.github.io/steel-drawing-ontology/shapes"
STEEL = Namespace(CORE_IRI + "#")
STEEL_SH = Namespace(SHAPES_IRI + "#")
VERSION = "1.0.6"


def ontology_dir() -> Path:
    """Folder that holds ``core.ttl`` and ``shapes.ttl``."""
    packaged = resources.files("steel_ontology") / "ontology"
    if packaged.is_dir():
        return Path(str(packaged))
    checkout = Path(__file__).resolve().parents[2] / "ontology"
    if checkout.is_dir():
        return checkout
    raise FileNotFoundError("ontology files not found (looked in the package and the checkout)")


@cache
def _parsed(name: str) -> Graph:
    return Graph().parse(ontology_dir() / name, format="turtle")


def _copy(graph: Graph) -> Graph:
    """A private copy, so callers can add triples without touching the cached graph."""
    copy = Graph()
    for prefix, namespace in graph.namespaces():
        copy.bind(prefix, namespace)
    for triple in graph:
        copy.add(triple)
    return copy


def load_ontology() -> Graph:
    """The OWL ontology (classes, properties, controlled vocabularies, defined classes)."""
    return _copy(_parsed("core.ttl"))


def load_shapes() -> Graph:
    """The SHACL shapes (completeness, value ranges, arithmetic checks)."""
    return _copy(_parsed("shapes.ttl"))


def local_name(term: URIRef | str) -> str:
    """``steel:PlanSheet`` -> ``PlanSheet``; other IRIs are returned whole."""
    text = str(term)
    return text[len(STEEL) :] if text.startswith(str(STEEL)) else text


@cache
def comments() -> dict[str, str]:
    """``rdfs:comment`` of every documented term, by local name."""
    graph = _parsed("core.ttl")
    return {
        local_name(subject): str(text)
        for subject, text in graph.subject_objects(RDFS.comment)
        if str(subject).startswith(str(STEEL))
    }


@cache
def enumerations() -> dict[str, tuple[str, ...]]:
    """Members of every closed vocabulary (``owl:oneOf`` class), by class local name."""
    graph = _parsed("core.ttl")
    found = {}
    for cls, definition in graph.subject_objects(OWL.equivalentClass):
        members = graph.value(definition, OWL.oneOf)
        if members is not None:
            found[local_name(cls)] = tuple(local_name(m) for m in Collection(graph, members))
    return found


@cache
def defined_classes() -> tuple[str, ...]:
    """Classes whose membership a reasoner infers (``owl:equivalentClass`` intersections)."""
    graph = _parsed("core.ttl")
    names = {
        local_name(cls)
        for cls, definition in graph.subject_objects(OWL.equivalentClass)
        if graph.value(definition, OWL.intersectionOf) is not None
    }
    return tuple(sorted(names))


@cache
def properties() -> dict[str, dict[str, object]]:
    """Kind and functionality of every property, by local name.

    Each value is ``{"object": bool, "functional": bool}``.
    """
    graph = _parsed("core.ttl")
    found: dict[str, dict[str, object]] = {}
    for kind, is_object in ((OWL.ObjectProperty, True), (OWL.DatatypeProperty, False)):
        for prop in graph.subjects(RDF.type, kind):
            found[local_name(prop)] = {
                "object": is_object,
                "functional": (prop, RDF.type, OWL.FunctionalProperty) in graph,
            }
    return found
