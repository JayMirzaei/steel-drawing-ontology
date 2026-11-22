"""Reasoner entailments: what OWL RL gives everywhere, and what only HermiT gives.

The HermiT tests need Java and ``owlready2``; they are skipped when either is missing.
"""

from __future__ import annotations

import pytest
from rdflib import RDF, Graph

from conftest import DATA, data_graph
from steel_ontology import vocabulary
from steel_ontology.reason import InferenceResult, ReasonerUnavailable, hermit_available, infer
from steel_ontology.vocabulary import STEEL

NS = "https://example.org/defined#"
T = "https://example.org/t#"
needs_java = pytest.mark.skipif(not hermit_available(), reason="needs Java and owlready2")
NEGATIVES = (
    "CommercialSheet",
    "ConnectionToBeDesignedByOthers",
    "ExistingElement",
    "FabricatorDesignedSealed",
    "ThirdPartyMarkup",
    "MarkedUpSheet",
    "MarkedUpSet",
    "RowWithForces",
    "UnverifiedForceRecord",
)


@pytest.fixture(scope="module")
def defined_data() -> Graph:
    return Graph().parse(DATA / "defined_classes.ttl")


@pytest.fixture(scope="module")
def owlrl_result(defined_data: Graph) -> InferenceResult:
    return infer(defined_data)


@pytest.fixture(scope="module")
def hermit_result(defined_data: Graph) -> InferenceResult:
    return infer(defined_data, engine="hermit")


def test_test_data_covers_every_defined_class(defined_data: Graph) -> None:
    subjects = {str(s) for s in defined_data.subjects()}
    for name in vocabulary.defined_classes():
        assert f"{NS}{name}_yes" in subjects


@pytest.mark.parametrize("name", vocabulary.defined_classes())
def test_owlrl_entails_every_defined_class(owlrl_result: InferenceResult, name: str) -> None:
    assert name in owlrl_result.types_of(f"{NS}{name}_yes")


@pytest.mark.parametrize("name", NEGATIVES)
def test_owlrl_does_not_overreach(owlrl_result: InferenceResult, name: str) -> None:
    assert name not in owlrl_result.types_of(f"{NS}{name}_no")


def test_owlrl_result_graph_is_the_data_plus_inferences(
    owlrl_result: InferenceResult, defined_data: Graph
) -> None:
    assert owlrl_result.consistent
    assert owlrl_result.engine == "owlrl"
    graph = owlrl_result.graph
    assert all(triple in graph for triple in defined_data)
    sheet = next(defined_data.subjects(STEEL.pricingColumns, None))
    assert (sheet, RDF.type, STEEL.CommercialSheet) in graph
    # superclasses and inverse links are materialised, the ontology itself is not copied in
    girt = data_graph("ex:g a steel:Girt . ex:set a steel:DrawingSet ; steel:hasSheet ex:s .")
    result = infer(girt)
    assert result.types_of(T + "g") == ["Beam", "Element", "Member"]
    assert (STEEL.Girt, None, None) not in result.graph
    assert len(list(result.graph.triples((None, STEEL.isSheetOf, None)))) == 1


def test_owlrl_reports_an_individual_in_two_disjoint_classes() -> None:
    result = infer(data_graph("ex:x a steel:Beam , steel:Column ."))
    assert not result.consistent
    assert "Disjoint classes" in result.inconsistencies[0]


def test_owlrl_reports_two_values_on_a_functional_vocabulary_property() -> None:
    result = infer(
        data_graph(
            "ex:a a steel:Annotation ; "
            "steel:annotationOrigin steel:EngineerOrigin , steel:ThirdPartyOrigin ."
        )
    )
    assert result.inconsistencies == [
        "EngineerOrigin and ThirdPartyOrigin are declared different but the data makes them the "
        "same (two values on a functional property)"
    ]


def test_a_voided_stamp_is_consistent() -> None:
    """Regression: isVoided once had two domains, which made a voided annotation a view."""
    result = infer(data_graph("ex:a a steel:Annotation ; steel:isVoided true ."))
    assert result.consistent
    assert "View" not in result.types_of(T + "a")


# Realistic data that domain and range axioms once made inconsistent or silently misclassified:
# in OWL a domain or range is an inference rule, not a check, so it must be wide enough.
REALISTIC = [
    ("ex:skid a steel:Assembly ; steel:hasPart ex:part . ex:part a steel:Truss .", "Truss"),
    (
        "ex:skid a steel:Assembly ; steel:hasPart ex:part . ex:part a steel:BasePlateConnection .",
        "BasePlateConnection",
    ),
    (
        "ex:skid a steel:Assembly ; steel:hasPart ex:part . ex:part a steel:LiftingLug .",
        "LiftingLug",
    ),
    ("ex:part a steel:Joist ; steel:camberMm 25.0 ; steel:studCount 12 .", "Joist"),
    ("ex:part a steel:Truss ; steel:camberMm 40.0 .", "Truss"),
    ('ex:part a steel:Plate ; steel:sectionText "PL10x200" .', "Plate"),
]


@pytest.mark.parametrize(("turtle", "cls"), REALISTIC)
def test_realistic_parts_stay_consistent_and_keep_their_class(turtle: str, cls: str) -> None:
    result = infer(data_graph(turtle))
    assert result.consistent, result.inconsistencies
    inferred = result.types_of(T + "part")
    assert "Beam" not in inferred
    if cls != "Joist":  # a joist is a member; plates, lugs, trusses and connections are not
        assert "Member" not in inferred


@needs_java
@pytest.mark.parametrize(("turtle", "cls"), REALISTIC)
def test_hermit_agrees_realistic_parts_are_consistent(turtle: str, cls: str) -> None:
    result = infer(data_graph(turtle), engine="hermit")
    assert result.consistent, result.inconsistencies
    assert "Beam" not in result.types_of(T + "part")


def test_good_sample_is_consistent(sample_good: Graph) -> None:
    result = infer(sample_good)
    assert result.consistent
    assert result.types_of("https://example.org/sample#s3") == [
        "MarkedUpSheet",
        "ReviewedVendorSheet",
        "SteelRelevantSheet",
    ]


def test_unknown_engine_is_refused(sample_good: Graph) -> None:
    with pytest.raises(ValueError, match="unknown engine"):
        infer(sample_good, engine="pellet")  # type: ignore[arg-type]


def test_hermit_without_java_says_so(monkeypatch: pytest.MonkeyPatch, sample_good: Graph) -> None:
    pytest.importorskip("owlready2")
    monkeypatch.setenv("STEEL_ONTOLOGY_JAVA", "/nonexistent/java")
    with pytest.raises(ReasonerUnavailable, match="no Java runtime"):
        infer(sample_good, engine="hermit")


# ----------------------------------------------------------------------------------- HermiT


@needs_java
def test_ontology_has_no_unsatisfiable_class() -> None:
    result = infer(Graph(), engine="hermit")
    assert result.inconsistencies == []


@needs_java
def test_hermit_and_owlrl_agree_on_defined_classes(
    hermit_result: InferenceResult, owlrl_result: InferenceResult
) -> None:
    defined = set(vocabulary.defined_classes())
    assert hermit_result.consistent
    for name in defined:
        iri = f"{NS}{name}_yes"
        assert defined.intersection(hermit_result.types_of(iri)) == defined.intersection(
            owlrl_result.types_of(iri)
        )
    for name in NEGATIVES:
        assert name not in hermit_result.types_of(f"{NS}{name}_no")


@needs_java
@pytest.mark.parametrize(
    "turtle",
    [
        "ex:x a steel:Beam , steel:Column .",
        "ex:a a steel:Annotation ; "
        "steel:annotationOrigin steel:EngineerOrigin , steel:ThirdPartyOrigin .",
    ],
)
def test_hermit_rejects_contradictions(turtle: str) -> None:
    assert not infer(data_graph(turtle), engine="hermit").consistent


@needs_java
def test_only_hermit_reasons_by_cases_over_a_closed_vocabulary() -> None:
    """The origin is unnamed but known not to be the engineer.

    The vocabulary has two members, so it must be the third party: HermiT concludes the
    annotation is third-party markup. OWL RL has no rule for that and stays silent.
    """
    graph = data_graph(
        "ex:a a steel:Annotation ; steel:annotationOrigin ex:someone .\n"
        "ex:someone owl:differentFrom steel:EngineerOrigin ."
    )
    assert "ThirdPartyMarkup" in infer(graph, engine="hermit").types_of(T + "a")
    assert "ThirdPartyMarkup" not in infer(graph).types_of(T + "a")


@pytest.mark.parametrize("status", ["demolished", "modified"])
def test_existing_element_covers_every_existing_status(
    owlrl_result: InferenceResult, status: str
) -> None:
    """Regression: ExistingElement once meant only 'existing to remain'."""
    assert "ExistingElement" in owlrl_result.types_of(f"{NS}ExistingElement_{status}")
