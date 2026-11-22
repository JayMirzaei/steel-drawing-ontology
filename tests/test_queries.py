"""The competency questions, each run against the good sample."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rdflib import Graph

from conftest import SAMPLE_NS, data_graph
from steel_ontology.queries import UnknownQuery, get_query, list_queries, run_query

# query name -> rows expected on tests/data/sample_good.ttl
EXPECTED_ROWS = {
    "marked-up-sheets": 3,
    "reference-only-sheets": 1,
    "mixed-author-packages": 1,
    "weighted-assemblies": 1,
    "responsibility-boundaries": 1,
    "field-confirm-items": 1,
    "raster-derived-sheets": 1,
    "area-loads-by-zone": 0,  # the sample's only area load is snow; the default is live load
    "requirement-clauses": 1,
    "schedule-cells-by-kind": 1,
    "reinforcing-members": 1,
    "scope-items": 1,
    "force-records-by-load-type": 1,
    "default-rules": 1,
    "construction-sequence-steps": 3,
    "tender-only-values": 1,
    "elements-by-class": 6,
    "sheet-revisions": 1,
    "annotation-texts": 8,
    "cited-standards": 1,
    "connections-designed-by-others": 0,
    "elements-by-responsibility": 0,
    "element-forces": 1,
    "schedule-totals": 1,
}


def test_there_are_twenty_four_documented_queries() -> None:
    queries = list_queries()
    assert [q.id for q in queries] == [f"CQ{i:02d}" for i in range(1, 25)]
    assert {q.name for q in queries} == set(EXPECTED_ROWS)
    for query in queries:
        assert query.title and query.question.endswith("?")


@pytest.mark.parametrize(("name", "rows"), EXPECTED_ROWS.items())
def test_each_query_answers_on_the_sample(sample_good: Graph, name: str, rows: int) -> None:
    assert len(run_query(sample_good, name).rows) == rows


def test_rows_carry_python_values(sample_good: Graph) -> None:
    (snow,) = run_query(sample_good, "area-loads-by-zone", loadType="SnowLoad").rows
    assert snow == {
        "zone": SAMPLE_NS + "z1",
        "load": SAMPLE_NS + "al1",
        "kPa": Decimal("1.3"),
        "factored": False,
    }

    marked = run_query(sample_good, "marked-up-sheets")
    assert marked.columns == ("sheet", "sheetNumber", "annotation", "markupKind")
    assert marked.rows[0] == {
        "sheet": SAMPLE_NS + "s1",
        "sheetNumber": "S101",
        "annotation": SAMPLE_NS + "a1",
        "markupKind": "TakeoffHighlight",
    }
    assert marked.column("sheetNumber") == ["S101", None, None]

    blast = run_query(sample_good, "force-records-by-load-type").rows[0]
    assert blast["factored"] is True
    assert blast["unit"] == "kN"


def test_steps_come_back_in_printed_order(sample_good: Graph) -> None:
    steps = run_query(sample_good, "construction-sequence-steps").column("step")
    assert steps == [
        "1. Shore existing structure",
        "2. Install new foundations",
        "3. Remove existing column last",
    ]


def test_parameters_change_the_answer(sample_good: Graph) -> None:
    welding = run_query(sample_good, "requirement-clauses")
    bolting = run_query(sample_good, "requirement-clauses", topic="BoltingReq")
    assert welding.column("value") == ["100% UT"]
    assert bolting.column("text") == ["Do not field burn base plate holes."]
    assert run_query(sample_good, "area-loads-by-zone", loadType="WindLoad").rows == []


def test_queries_can_be_found_by_id(sample_good: Graph) -> None:
    assert get_query("cq09") is get_query("requirement-clauses")
    assert len(run_query(sample_good, "CQ02").rows) == 1


def test_subclasses_count_without_a_reasoner() -> None:
    """A truss is an assembly; the query follows rdfs:subClassOf in the ontology."""
    graph = data_graph(
        "ex:t a steel:Truss ; steel:assemblyWeightTonnes 3.2 ; steel:hasPart ex:a , ex:b ."
    )
    assert run_query(graph, "weighted-assemblies").rows == [
        {"assembly": "https://example.org/t#t", "weightTonnes": Decimal("3.2"), "parts": 2}
    ]


def test_bad_requests_are_refused(sample_good: Graph) -> None:
    with pytest.raises(UnknownQuery):
        run_query(sample_good, "drop-everything")
    with pytest.raises(ValueError, match="no parameter"):
        run_query(sample_good, "marked-up-sheets", topic="WeldingReq")
    with pytest.raises(ValueError, match="not a term of the ontology"):
        run_query(sample_good, "requirement-clauses", topic="} DELETE WHERE {")


def test_area_loads_are_reported_per_zone_and_never_added() -> None:
    graph = data_graph(
        "ex:z1 a steel:Zone ; steel:hasAreaLoad ex:l1 .\n"
        "ex:z2 a steel:Zone ; steel:hasAreaLoad ex:l2 .\n"
        "ex:l1 steel:areaLoadType steel:SnowLoad ; steel:areaLoadKPa 1.6 .\n"
        "ex:l2 steel:areaLoadType steel:SnowLoad ; steel:areaLoadKPa 3.2 ."
    )
    rows = run_query(graph, "area-loads-by-zone", loadType="SnowLoad").rows
    assert [(r["zone"][-2:], r["kPa"]) for r in rows] == [
        ("z1", Decimal("1.6")),
        ("z2", Decimal("3.2")),
    ]


def test_reasoner_queries_ask_for_the_defined_class() -> None:
    """These queries name a reasoner-defined class instead of repeating its definition."""
    needing = {q.name for q in list_queries() if q.needs_reasoner}
    assert needing == {
        "marked-up-sheets",
        "reference-only-sheets",
        "connections-designed-by-others",
    }
    for name, cls in [
        ("marked-up-sheets", "MarkedUpSheet"),
        ("reference-only-sheets", "ReferenceOnlySheet"),
        ("connections-designed-by-others", "ConnectionToBeDesignedByOthers"),
    ]:
        assert f"a steel:{cls}" in get_query(name).text


def test_a_two_step_inference_answers_the_markup_query() -> None:
    """Markup origin -> ThirdPartyMarkup -> MarkedUpSheet: two defined classes, no SPARQL rule."""
    graph = data_graph(
        "ex:s a steel:Sheet ; steel:hasAnnotation ex:a , ex:b .\n"
        "ex:a a steel:Annotation ; steel:annotationOrigin steel:ThirdPartyOrigin .\n"
        "ex:b a steel:Annotation ; steel:annotationOrigin steel:EngineerOrigin ."
    )
    rows = run_query(graph, "marked-up-sheets").rows
    assert [(r["sheet"], r["annotation"]) for r in rows] == [
        ("https://example.org/t#s", "https://example.org/t#a")
    ]


def test_connections_designed_by_others_come_from_the_reasoner() -> None:
    graph = data_graph(
        "ex:c1 a steel:BraceConnection ; steel:responsibility steel:ByConnectionEngineer .\n"
        "ex:c2 a steel:ShearConnection ; steel:responsibility steel:ByEngineerOfRecord ."
    )
    rows = run_query(graph, "connections-designed-by-others").rows
    assert [r["connection"] for r in rows] == ["https://example.org/t#c1"]


def test_elements_by_class_lists_each_element_once_on_an_inferred_graph(sample_good: Graph) -> None:
    from steel_ontology.reason import infer

    inferred = infer(sample_good).graph
    for graph in (sample_good, inferred):
        rows = run_query(graph, "elements-by-class", elementClass="Element").rows
        keys = [(r["element"], r["location"]) for r in rows]
        assert len(keys) == len(set(keys))
    plain = run_query(sample_good, "elements-by-class").rows
    assert run_query(inferred, "elements-by-class").rows == plain


def test_element_forces_keep_values_and_units_as_printed() -> None:
    graph = data_graph(
        'ex:c a steel:Column ; steel:tag "C7" ; steel:hasForceRecord ex:f .\n'
        'ex:f a steel:ForceRecord ; steel:isFactored true ; steel:loadCase "Pf" ; '
        'steel:axialValue 117.0 ; steel:forceUnit "kip" ; steel:momentMajorValue 40.0 ; '
        'steel:momentUnit "kip.ft" .'
    )
    (row,) = run_query(graph, "element-forces").rows
    assert (row["tag"], row["axial"], row["forceUnit"]) == ("C7", Decimal("117.0"), "kip")
    assert (row["moment"], row["momentUnit"]) == (Decimal("40.0"), "kip.ft")


def test_schedule_totals_show_the_printed_total_beside_the_sum(sample_good: Graph) -> None:
    (row,) = run_query(sample_good, "schedule-totals").rows
    assert row["printedTotal"] == row["sumOfRows"]


def test_inferences_are_reused_but_never_stale() -> None:
    graph = data_graph("ex:s a steel:Sheet ; steel:hasAnnotation ex:a .\nex:a a steel:Annotation .")
    assert run_query(graph, "marked-up-sheets").rows == []
    graph.parse(
        data="@prefix steel: <https://jaymirzaei.github.io/steel-drawing-ontology/core#> .\n"
        "<https://example.org/t#a> steel:annotationOrigin steel:ThirdPartyOrigin .",
        format="turtle",
    )
    assert len(run_query(graph, "marked-up-sheets").rows) == 1
