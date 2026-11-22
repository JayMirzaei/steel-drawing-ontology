"""Typed objects <-> RDF: nothing is lost in either direction."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal
from rdflib.compare import isomorphic

from conftest import EXAMPLE, SAMPLE_NS, data_graph
from steel_ontology import enums, models
from steel_ontology.graph import GraphMappingError, from_graph, load_graph, to_graph
from steel_ontology.models import Extraction
from steel_ontology.vocabulary import STEEL


def test_sample_graph_survives_graph_to_models_to_graph(sample_good: Graph) -> None:
    extraction = from_graph(sample_good, strict=True)
    assert extraction.base_iri == SAMPLE_NS
    assert extraction.dangling_references() == []
    assert isomorphic(to_graph(extraction), sample_good)


def test_models_survive_models_to_graph_to_models() -> None:
    gold = Extraction.from_json((EXAMPLE / "gold.json").read_text(encoding="utf-8"))
    again = from_graph(to_graph(gold), strict=True)
    assert again == gold.normalised()
    assert len(again.nodes) == len(gold.nodes)


def test_literals_are_typed_by_python_type() -> None:
    extraction = Extraction(
        base_iri="https://example.org/t#",
        nodes=[
            models.Schedule(id="s", declared_total=Decimal("1249.60"), assembly_count=2),
            models.Sheet(id="sh", is_sealed=False, sheet_kind=enums.SheetKind.PLAN_SHEET),
        ],
    )
    graph = to_graph(extraction)
    total = next(graph.objects(None, STEEL.declaredTotal))
    assert total.n3() == '"1249.60"^^<http://www.w3.org/2001/XMLSchema#decimal>'
    whole = to_graph(Extraction(nodes=[models.Schedule(id="s", declared_total=Decimal("1250"))]))
    assert str(next(whole.objects(None, STEEL.declaredTotal))) == "1250.0"
    assert next(graph.objects(None, STEEL.assemblyCount)) == Literal(2)
    assert next(graph.objects(None, STEEL.isSealed)) == Literal(False)
    assert next(graph.objects(None, STEEL.sheetKind)) == STEEL.PlanSheet


def test_only_the_most_specific_class_is_written() -> None:
    graph = to_graph(Extraction(nodes=[models.Girt(id="g")]))
    assert list(graph.objects(None, RDF.type)) == [STEEL.Girt]


def test_most_specific_class_is_read_back_from_an_inferred_graph() -> None:
    graph = data_graph("ex:g a steel:Girt , steel:Beam , steel:Member , steel:Element .")
    (node,) = from_graph(graph).nodes
    assert isinstance(node, models.Girt)


def test_unrelated_classes_are_refused() -> None:
    graph = data_graph("ex:x a steel:Sheet , steel:View .")
    with pytest.raises(GraphMappingError, match="unrelated classes"):
        from_graph(graph)


def test_two_values_for_a_single_field_are_refused() -> None:
    graph = data_graph('ex:s a steel:Sheet ; steel:sheetNumber "S-1" , "S-2" .')
    with pytest.raises(GraphMappingError, match="2 values for single field sheetNumber"):
        from_graph(graph)


def test_strict_mode_refuses_what_it_cannot_represent() -> None:
    graph = data_graph(
        "ex:r a steel:ScheduleRow ; steel:describesElement ex:c . ex:c a steel:Column ."
    )
    assert len(from_graph(graph).nodes) == 2
    with pytest.raises(GraphMappingError, match="unmapped property"):
        from_graph(graph, strict=True)


def test_ontology_and_vocabulary_members_are_not_read_as_objects(
    sample_good: Graph, ontology: Graph
) -> None:
    merged = sample_good + ontology
    assert from_graph(merged, SAMPLE_NS) == from_graph(sample_good)


def test_load_graph_reads_json_and_turtle_alike() -> None:
    assert isomorphic(load_graph(EXAMPLE / "gold.json"), load_graph(EXAMPLE / "gold.ttl"))


@pytest.mark.parametrize(
    "context",
    [
        '"http://127.0.0.1:9/ctx.jsonld"',
        '["http://127.0.0.1:9/ctx.jsonld", {"ex": "https://example.org/"}]',
        '{"@import": "http://127.0.0.1:9/ctx.jsonld"}',
    ],
)
def test_json_ld_with_a_remote_context_is_refused_without_fetching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, context: str
) -> None:
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("load_graph tried to fetch a URL")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    path = tmp_path / "upload.jsonld"
    path.write_text(f'{{"@context": {context}, "@id": "https://example.org/x"}}', encoding="utf-8")
    with pytest.raises(ValueError, match="remote JSON-LD contexts are not loaded"):
        load_graph(path)
    nested = tmp_path / "nested.jsonld"
    nested.write_text(
        f'{{"@graph": [{{"@context": {context}, "@id": "https://example.org/x"}}]}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="remote"):
        load_graph(nested)


@pytest.mark.filterwarnings("ignore:ConjunctiveGraph is deprecated:DeprecationWarning")  # rdflib
def test_json_ld_with_an_inline_context_loads(tmp_path: Path) -> None:
    path = tmp_path / "inline.jsonld"
    path.write_text(
        '{"@context": {"steel": "https://jaymirzaei.github.io/steel-drawing-ontology/core#"},'
        ' "@id": "https://example.org/x", "@type": "steel:Beam"}',
        encoding="utf-8",
    )
    assert len(load_graph(path)) == 1


def test_the_format_comes_from_the_extension(tmp_path: Path) -> None:
    unknown = tmp_path / "data.txt"
    unknown.write_text("<https://example.org/a> <https://example.org/b> <https://example.org/c> .")
    with pytest.raises(ValueError, match=r"unknown file type \.txt"):
        load_graph(unknown)
    triples = tmp_path / "data.nt"
    triples.write_text(unknown.read_text())
    assert len(load_graph(triples)) == 1
