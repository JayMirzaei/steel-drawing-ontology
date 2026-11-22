"""The vocabulary files themselves: they parse, are closed where they claim to be, and are sane."""

from __future__ import annotations

from collections import Counter

from rdflib import OWL, RDF, RDFS, SH, Graph, URIRef
from rdflib.collection import Collection

from steel_ontology import vocabulary
from steel_ontology.vocabulary import CORE_IRI, STEEL, VERSION

INVERSES = {"isSheetOf", "isViewOn", "partOfAssembly", "supportedBy"}
NO_DOMAIN = {"evidencedBy", "citesStandard"} | INVERSES


def _properties(ontology: Graph) -> set[URIRef]:
    kinds = (OWL.ObjectProperty, OWL.DatatypeProperty)
    return {s for kind in kinds for s in ontology.subjects(RDF.type, kind)}


def test_ontology_parses_and_declares_its_version(ontology: Graph) -> None:
    assert (URIRef(CORE_IRI), RDF.type, OWL.Ontology) in ontology
    assert str(ontology.value(URIRef(CORE_IRI), OWL.versionInfo)) == VERSION
    assert ontology.value(URIRef(CORE_IRI), OWL.versionIRI) == URIRef(f"{CORE_IRI}/{VERSION}")


def test_vocabulary_size_is_as_documented(ontology: Graph) -> None:
    named_classes = {s for s in ontology.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    assert len(named_classes) == 108
    assert len(_properties(ontology)) == 230
    assert len(vocabulary.enumerations()) == 24
    assert len(vocabulary.defined_classes()) == 25


def test_every_term_used_is_declared(ontology: Graph) -> None:
    declared = set(ontology.subjects(RDF.type, None))
    used = {
        term
        for triple in ontology
        for term in triple
        if isinstance(term, URIRef) and str(term).startswith(str(STEEL))
    }
    assert used - declared == set()


def test_controlled_vocabularies_are_closed(ontology: Graph) -> None:
    """Each oneOf list has typed members and a matching AllDifferent axiom."""
    distinct = {
        frozenset(Collection(ontology, head))
        for head in ontology.objects(None, OWL.distinctMembers)
    }
    for name, members in vocabulary.enumerations().items():
        terms = frozenset(STEEL[m] for m in members)
        assert terms in distinct, f"{name} has no AllDifferent axiom over the same members"
        for term in terms:
            assert (term, RDF.type, STEEL[name]) in ontology, f"{term} is not typed as {name}"


def test_no_individual_belongs_to_two_vocabularies(ontology: Graph) -> None:
    counts = Counter(m for members in vocabulary.enumerations().values() for m in members)
    assert [m for m, n in counts.items() if n > 1] == []


def test_each_property_has_one_domain_and_one_range(ontology: Graph) -> None:
    """Two rdfs:domain axioms intersect in OWL, which is almost never what was meant."""
    for prop in _properties(ontology):
        name = vocabulary.local_name(prop)
        domains = list(ontology.objects(prop, RDFS.domain))
        ranges = list(ontology.objects(prop, RDFS.range))
        assert len(domains) == (0 if name in NO_DOMAIN else 1), name
        assert len(ranges) == (0 if name in INVERSES else 1), name


def test_no_xsd_date_ranges(ontology: Graph) -> None:
    """xsd:date is outside the OWL 2 datatype map; DL reasoners refuse to load it."""
    date = URIRef("http://www.w3.org/2001/XMLSchema#date")
    assert list(ontology.subjects(RDFS.range, date)) == []


def test_shapes_only_use_terms_of_the_ontology(ontology: Graph, shapes: Graph) -> None:
    declared = set(ontology.subjects(RDF.type, None))
    for predicate in (SH.path, SH.targetClass, SH["class"], SH.targetSubjectsOf):
        for term in shapes.objects(None, predicate):
            assert term in declared, f"shapes use undeclared term {term}"


def test_sparql_constraints_take_severity_from_their_shape(shapes: Graph) -> None:
    """SHACL ignores sh:severity on an sh:sparql constraint, so it must sit on the shape."""
    for shape, constraint in shapes.subject_objects(SH.sparql):
        assert shapes.value(constraint, SH.severity) is None
        assert shapes.value(shape, SH.severity) is not None
        assert len(list(shapes.objects(shape, SH.sparql))) == 1


def test_vocabulary_shapes_list_exactly_the_closed_vocabularies(
    ontology: Graph, shapes: Graph
) -> None:
    """Each sh:in list equals its owl:oneOf list, and every vocabulary property is checked."""
    for name, members in vocabulary.enumerations().items():
        shape = URIRef(f"{vocabulary.SHAPES_IRI}#{name}ValuesShape")
        properties = set(ontology.subjects(RDFS.range, STEEL[name]))
        assert set(shapes.objects(shape, SH.targetSubjectsOf)) == properties, name
        for prop_shape in shapes.objects(shape, SH.property):
            assert shapes.value(prop_shape, SH.path) in properties
            listed = list(Collection(shapes, shapes.value(prop_shape, SH["in"])))
            assert listed == [STEEL[m] for m in members], name


def test_no_shape_relies_on_sh_class_for_a_vocabulary(shapes: Graph) -> None:
    """sh:class accepts any individual typed as a member; the lists are checked with sh:in."""
    vocabularies = {STEEL[name] for name in vocabulary.enumerations()}
    assert set(shapes.objects(None, SH["class"])) & vocabularies == set()
