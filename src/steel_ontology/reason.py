"""OWL inference over extracted data.

Two engines, one result type.

``owlrl`` (default) is a pure-Python OWL 2 RL forward chainer. It needs nothing but Python, so
it runs anywhere, and it entails every defined class of this ontology from stated facts: they
are all intersections of a named class with ``hasValue`` or ``someValuesFrom`` restrictions,
which OWL RL covers. It also applies subclass, domain, range and inverse axioms and reports
individuals that sit in two disjoint classes.

``hermit`` is a complete OWL 2 DL reasoner (run through ``owlready2``; needs Java). Use it when
you need what OWL RL cannot do:

- class-level reasoning: unsatisfiable classes and subsumption between class definitions;
- reasoning by cases over a closed vocabulary (an annotation whose origin is known not to be
  the engineer must be third-party markup, because the list has only two members);
- consequences of existential axioms (every ``ElementRow`` describes some element, even when
  that element is not named in the data).

``tests/test_reason.py`` pins down both the shared entailments and one case only HermiT finds.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import owlrl
from rdflib import OWL, RDF, Graph, URIRef
from rdflib.collection import Collection

from steel_ontology.vocabulary import STEEL, load_ontology, local_name

Engine = Literal["owlrl", "hermit"]
JAVA_ENV = "STEEL_ONTOLOGY_JAVA"
_OWLRL_ERROR = URIRef("http://www.daml.org/2002/03/agents/agent-ont#error")
_SCHEMA_TYPES = (
    OWL.Class,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.FunctionalProperty,
    OWL.Ontology,
)


class ReasonerUnavailable(RuntimeError):
    """The requested engine cannot run on this machine (no Java, or owlready2 not installed)."""


@dataclass(frozen=True)
class InferenceResult:
    """What a reasoner added to the data.

    ``graph`` is the data plus the inferred class memberships and property links of its own
    objects, ready for queries. ``inferred_types`` lists the new classes per object (full IRI ->
    sorted class local names). ``inconsistencies`` is empty when the data agrees with the
    ontology.
    """

    engine: Engine
    graph: Graph
    inferred_types: dict[str, list[str]] = field(default_factory=dict)
    inconsistencies: list[str] = field(default_factory=list)

    @property
    def consistent(self) -> bool:
        return not self.inconsistencies

    def types_of(self, iri: str) -> list[str]:
        """Inferred class names of one object (empty when nothing was inferred)."""
        return self.inferred_types.get(iri, [])


def infer(data: Graph, *, engine: Engine = "owlrl") -> InferenceResult:
    """Run a reasoner over ``data`` together with the ontology."""
    if engine == "owlrl":
        return _infer_owlrl(data)
    if engine == "hermit":
        return _infer_hermit(data)
    raise ValueError(f"unknown engine {engine!r}")


def find_java() -> str | None:
    """Path of a Java executable: ``STEEL_ONTOLOGY_JAVA``, then ``JAVA_HOME``, then ``PATH``."""
    explicit = os.environ.get(JAVA_ENV)
    if explicit:
        return explicit if Path(explicit).is_file() else None
    home = os.environ.get("JAVA_HOME")
    if home and (Path(home) / "bin" / "java").is_file():
        return str(Path(home) / "bin" / "java")
    return shutil.which("java")


def hermit_available() -> bool:
    """True when both ``owlready2`` and a Java runtime are present."""
    try:
        import owlready2  # noqa: F401
    except ImportError:
        return False
    return find_java() is not None


def _data_nodes(data: Graph) -> set[URIRef]:
    """Objects of the data: every IRI used as subject or object that is not an ontology term."""
    nodes = {s for s in data.subjects() if isinstance(s, URIRef)}
    nodes.update(o for o in data.objects() if isinstance(o, URIRef))
    return {n for n in nodes if not str(n).startswith(str(STEEL))}


def _merged(data: Graph) -> Graph:
    merged = load_ontology()
    for triple in data:
        merged.add(triple)
    return merged


def _result_graph(data: Graph) -> Graph:
    graph = Graph()
    for prefix, namespace in data.namespaces():
        graph.bind(prefix, namespace)
    graph.bind("steel", STEEL)
    for triple in data:
        graph.add(triple)
    return graph


def _infer_owlrl(data: Graph) -> InferenceResult:
    closure = _merged(data)
    owlrl.DeductiveClosure(
        owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False
    ).expand(closure)

    graph = _result_graph(data)
    inferred: dict[str, list[str]] = {}
    for subject in _data_nodes(data):
        for predicate, obj in closure.predicate_objects(subject):
            if not isinstance(obj, URIRef) or (subject, predicate, obj) in data:
                continue
            if predicate == RDF.type and str(obj).startswith(str(STEEL)):
                graph.add((subject, predicate, obj))
                inferred.setdefault(str(subject), []).append(local_name(obj))
            elif str(predicate).startswith(str(STEEL)):
                graph.add((subject, predicate, obj))
    problems = sorted(str(message) for message in closure.objects(None, _OWLRL_ERROR))
    problems += _merged_distinct_individuals(closure)
    return InferenceResult("owlrl", graph, {k: sorted(v) for k, v in inferred.items()}, problems)


def _merged_distinct_individuals(closure: Graph) -> list[str]:
    """Pairs declared different (``owl:AllDifferent``) that the closure made ``owl:sameAs``.

    This is how a functional property with two values from a closed vocabulary shows up, for
    example an annotation given both origins.
    """
    problems = set()
    for group in closure.subjects(RDF.type, OWL.AllDifferent):
        head = closure.value(group, OWL.distinctMembers)
        if head is None:
            continue
        members = list(Collection(closure, head))
        for i, first in enumerate(members):
            for second in members[i + 1 :]:
                if (first, OWL.sameAs, second) in closure or (second, OWL.sameAs, first) in closure:
                    names = sorted((local_name(first), local_name(second)))
                    problems.add(
                        f"{names[0]} and {names[1]} are declared different but the data makes "
                        "them the same (two values on a functional property)"
                    )
    return sorted(problems)


def _infer_hermit(data: Graph) -> InferenceResult:
    try:
        import owlready2
    except ImportError as error:
        raise ReasonerUnavailable("install the 'hermit' extra to get owlready2") from error
    java = find_java()
    if java is None:
        raise ReasonerUnavailable(f"no Java runtime found (set {JAVA_ENV} or JAVA_HOME)")
    owlready2.JAVA_EXE = java

    merged = _merged(data)
    _declare_individuals(merged)
    graph = _result_graph(data)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "merged.owl"
        merged.serialize(path, format="xml")
        world = owlready2.World()
        ontology = world.get_ontology(path.as_uri()).load()
        try:
            with ontology:
                owlready2.sync_reasoner_hermit(world, infer_property_values=False, debug=0)
        except owlready2.OwlReadyInconsistentOntologyError:
            return InferenceResult("hermit", graph, {}, ["the ontology and data are inconsistent"])
        problems = [
            f"class {cls.name} is unsatisfiable"
            for cls in world.inconsistent_classes()
            if cls is not owlready2.Nothing
        ]
        inferred: dict[str, list[str]] = {}
        subjects = _data_nodes(data)
        for individual in ontology.individuals():
            subject = URIRef(individual.iri)
            if subject not in subjects:
                continue
            for cls in individual.INDIRECT_is_a:
                iri = getattr(cls, "iri", None)
                if not iri or not iri.startswith(str(STEEL)):
                    continue
                if (subject, RDF.type, URIRef(iri)) not in data:
                    graph.add((subject, RDF.type, URIRef(iri)))
                    inferred.setdefault(str(subject), []).append(local_name(iri))
    return InferenceResult(
        "hermit", graph, {k: sorted(v) for k, v in inferred.items()}, sorted(problems)
    )


def _declare_individuals(graph: Graph) -> None:
    """Type every instance as ``owl:NamedIndividual`` so OWL API based tools load it as one."""
    for subject in set(graph.subjects(RDF.type, None)):
        if not isinstance(subject, URIRef):
            continue
        types = set(graph.objects(subject, RDF.type))
        if not types.intersection(_SCHEMA_TYPES):
            graph.add((subject, RDF.type, OWL.NamedIndividual))
