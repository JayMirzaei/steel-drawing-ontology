"""The question router: rules first, a model only to choose among the vetted queries."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from rdflib import Graph

from conftest import EXAMPLE
from steel_ontology.ask import NO_QUERY, ask, ask_key, ask_schema, param_vocabulary, route
from steel_ontology.extract.providers import ProviderError, RecordedProvider, Request
from steel_ontology.graph import load_graph
from steel_ontology.queries import list_queries


@pytest.fixture(scope="module")
def graph() -> Graph:
    return load_graph(EXAMPLE / "gold.json")


ROUTES = [
    ("What size is beam B3?", "elements-by-class", {"elementClass": "Beam"}),
    ("Where are the columns?", "elements-by-class", {"elementClass": "Column"}),
    ("How many braces are there?", "elements-by-class", {"elementClass": "Brace"}),
    ("List the base plates", "elements-by-class", {"elementClass": "Connection"}),
    ("list all members", "elements-by-class", {"elementClass": "Member"}),
    ("What do the notes say about bolting?", "requirement-clauses", {"topic": "BoltingReq"}),
    ("what welding requirements apply", "requirement-clauses", {"topic": "WeldingReq"}),
    ("Is there a clause about painting?", "requirement-clauses", {"topic": "CoatingReq"}),
    ("Which requirements are there?", "requirement-clauses", {}),
    ("Which sheets have third-party markup?", "marked-up-sheets", {}),
    ("Which sheets are for reference only?", "reference-only-sheets", {}),
    ("What does the query note say?", "annotation-texts", {}),
    ("What stamps are on the drawings?", "annotation-texts", {}),
    ("What is the default rule for connections?", "default-rules", {}),
    ("What is the live load?", "area-loads-by-zone", {"loadType": "LiveLoad"}),
    ("What is the total dead load?", "area-loads-by-zone", {"loadType": "DeadLoad"}),
    ("What are the snow area loads in kPa?", "area-loads-by-zone", {"loadType": "SnowLoad"}),
    ("What are the factored forces?", "force-records-by-load-type", {}),
    (
        "Which forces are load combinations?",
        "force-records-by-load-type",
        {"loadType": "LoadCombination"},
    ),
    ("Which standards are cited?", "cited-standards", {}),
    ("When was S-101 issued?", "sheet-revisions", {}),
    ("which sheets are in the set?", "sheet-revisions", {}),
    ("Which cells are by supplier?", "schedule-cells-by-kind", {"cellKind": "BySupplierCell"}),
    ("Which members reinforce existing steel?", "reinforcing-members", {}),
    ("Which values are for tender only?", "tender-only-values", {}),
    ("What is the construction sequence?", "construction-sequence-steps", {}),
    ("What must be field verified before fabrication?", "field-confirm-items", {}),
    ("Which sheets were made from raster scans?", "raster-derived-sheets", {}),
    ("What is in the scope: supply and install?", "scope-items", {"workKind": "SupplyAndInstall"}),
    # Questions that once went to the wrong query on a single word ("others", "factored").
    ("Which connections are designed by others?", "connections-designed-by-others", {}),
    ("Who designs the connections?", "connections-designed-by-others", {}),
    ("Is anything by others?", "elements-by-responsibility", {"responsibility": "ByOthers"}),
    (
        "Which beams are designed by others?",
        "elements-by-responsibility",
        {"responsibility": "ByOthers", "elementClass": "Beam"},
    ),
    (
        "Who is responsible for the grating?",
        "elements-by-responsibility",
        {"elementClass": "Grating"},
    ),
    ("What is the factored load on C2?", "element-forces", {}),
    ("What is the axial load on column C1?", "element-forces", {}),
    ("What are the loads on column C1?", "element-forces", {}),
    ("What is the shear on B2?", "element-forces", {}),
    ("What is the total weight?", "schedule-totals", {}),
    ("What does the schedule total add up to?", "schedule-totals", {}),
    ("Which connections are there?", "elements-by-class", {"elementClass": "Connection"}),
]


@pytest.mark.parametrize(("question", "query", "params"), ROUTES)
def test_router_picks_the_query_and_its_parameters(
    question: str, query: str, params: dict[str, str]
) -> None:
    decision = route(question)
    assert decision is not None, question
    assert (decision.query, decision.params) == (query, params)


@pytest.mark.parametrize(
    "question",
    [
        "Is the sky blue?",
        "",
        "Who has to be told before coming to site?",
        "hello",
        "42",
        # A vocabulary word alone names a value, not a question.
        "column",
        "beam B3",
        "other",
        "factored",
        "What is the moment of inertia?",
        "Is the total right?",
        "What colour is the other one?",
    ],
)
def test_router_does_not_guess(question: str) -> None:
    assert route(question) is None


def test_every_query_can_be_reached_by_some_rule() -> None:
    reached = {query for _, query, _ in ROUTES}
    missing = {q.name for q in list_queries()} - reached
    assert missing <= {"mixed-author-packages", "weighted-assemblies", "responsibility-boundaries"}
    assert route("Which packages mix different authors?").query == "mixed-author-packages"
    assert route("Which assemblies state a lifting weight?").query == "weighted-assemblies"
    assert route("What limits the engineer's responsibility?").query == "responsibility-boundaries"


def test_router_is_deterministic_and_ignores_case_and_spacing() -> None:
    assert route("WHAT   SIZE is Beam b3 ?") == route("what size is beam B3?")


def test_misrouted_questions_now_get_the_right_rows(graph: Graph) -> None:
    """The questions a single parameter word used to send to the area-load query."""
    factored = ask(graph, "What is the factored load on C2?")
    (row,) = factored.rows
    assert (row.values["tag"], row.values["compression"], row.values["forceUnit"]) == (
        "C2",
        Decimal("520.0"),
        "kN",
    )
    assert row.values["factored"] is True
    assert {c.sheet_number for c in row.citations} == {"S-201"}
    axial = ask(graph, "What is the axial load on column C1?")
    assert [r.values["compression"] for r in axial.rows] == [Decimal("310.0")]
    others = ask(graph, "Which connections are designed by others?")
    assert [r.values["connection"].rsplit("/", 1)[-1] for r in others.rows] == ["connection-brace"]
    anything = ask(graph, "Is anything by others?")
    assert [r.values["element"].rsplit("/", 1)[-1] for r in anything.rows] == ["anchor-rods"]
    weight = ask(graph, "What is the total weight?")
    (total,) = weight.rows
    assert total.values["printedTotal"] == total.values["sumOfRows"] == Decimal("1249.6")


def test_answer_rows_cite_sheet_zone_and_confidence(graph: Graph) -> None:
    answer = ask(graph, "What size is beam B3?")
    assert (answer.route, answer.query.name) == ("rule", "elements-by-class")
    assert answer.notes == ("rows limited to those naming B3",)
    (row,) = answer.rows
    assert (row.values["tag"], row.values["section"], row.values["quantity"]) == (
        "B3",
        "W200x27",
        2,
    )
    (citation,) = row.citations
    assert (citation.sheet_number, citation.page, citation.confidence) == ("S-101", 2, "Verified")
    assert len(citation.zone.split(",")) == 4
    assert citation.node.endswith("/beam-B3")
    text = answer.to_text()
    assert "CQ17 elements-by-class elementClass=Beam (chosen by rule): 1 row(s)" in text
    assert "evidence: S-101 zone" in text
    assert json.dumps(answer.to_dict())  # JSON-ready


def test_an_unnamed_vocabulary_parameter_means_all_values(graph: Graph) -> None:
    answer = ask(graph, "What do the general notes require?")
    assert answer.query.name == "requirement-clauses"
    assert answer.columns[0] == "topic"
    assert len(answer.rows) == 9  # all nine notes of the example, each with its topic
    assert {row.values["topic"] for row in answer.rows} >= {"WeldingReq", "InspectionReq"}
    assert answer.notes == ("the question names no topic, so every topic was tried",)
    rule = ask(graph, "What is the default rule for connections?")
    assert [row.values["ruleKind"] for row in rule.rows] == ["PercentOfYieldRule"]


def test_a_mark_that_matches_nothing_does_not_empty_the_answer(graph: Graph) -> None:
    answer = ask(graph, "What size is beam B99?")
    assert len(answer.rows) == 3 and answer.notes == ()


def test_no_match_answers_nothing_and_lists_what_can_be_asked(graph: Graph) -> None:
    answer = ask(graph, "Is the sky blue?")
    assert (answer.route, answer.query, answer.rows) == ("none", None, ())
    assert answer.notes[0].startswith("These are the questions I can answer: ")
    assert answer.to_text().startswith("I could not route this question")


# ---- model fallback -------------------------------------------------------------------------


class _Model:
    """A provider stand-in that returns a fixed choice and records the request."""

    name = "fake"
    model = "fake-1"

    def __init__(self, choice: dict | Exception) -> None:
        self.choice = choice
        self.requests: list[Request] = []

    def complete(self, request: Request) -> str:
        self.requests.append(request)
        if isinstance(self.choice, Exception):
            raise self.choice
        return json.dumps(self.choice)


QUESTION = "Who has to be told before coming to site?"


def test_fallback_is_used_only_when_no_rule_matches(graph: Graph) -> None:
    model = _Model({"query": "cited-standards", "params": []})
    assert ask(graph, "What size is beam B3?", provider=model).route == "rule"
    assert model.requests == []


def test_fallback_choice_is_run_as_a_vetted_query(graph: Graph) -> None:
    choice = {
        "query": "requirement-clauses",
        "params": [{"name": "topic", "value": "InspectionReq"}],
    }
    model = _Model(choice)
    answer = ask(graph, QUESTION, provider=model)
    assert (answer.route, answer.params) == ("model", {"topic": "InspectionReq"})
    assert [row.values["value"] for row in answer.rows] == ["48 hours"]
    assert answer.rows[0].citations[0].sheet_number == "S-001"
    (request,) = model.requests
    assert request.key == ask_key(QUESTION) and request.prompt == QUESTION
    assert request.schema == ask_schema() and request.images == ()
    assert "requirement-clauses" in request.system and "InspectionReq" in request.system


def test_fallback_cannot_leave_the_vetted_set(graph: Graph) -> None:
    invented = _Model({"query": "SELECT * WHERE { ?s ?p ?o }", "params": []})
    answer = ask(graph, QUESTION, provider=invented)
    assert answer.query is None
    assert "is not a vetted query" in answer.notes[0]

    bad_param = _Model(
        {"query": "requirement-clauses", "params": [{"name": "topic", "value": "?x } DROP"}]}
    )
    answer = ask(graph, QUESTION, provider=bad_param)
    assert answer.params == {}
    assert "is not allowed and was ignored" in " ".join(answer.notes)

    assert ask(graph, QUESTION, provider=_Model({"query": NO_QUERY, "params": []})).query is None
    failed = ask(graph, QUESTION, provider=_Model(ProviderError("offline")))
    assert failed.notes[0] == "model fallback failed: offline"


def test_recorded_fallback_answer_of_the_example(graph: Graph) -> None:
    answer = ask(graph, QUESTION, provider=RecordedProvider(EXAMPLE / "recorded"))
    assert (answer.route, answer.query.name) == ("model", "requirement-clauses")
    assert "48 HOURS NOTICE" in answer.rows[0].values["text"]


def test_ask_schema_and_keys() -> None:
    names = ask_schema()["properties"]["query"]["enum"]
    assert names[-1] == NO_QUERY and len(names) == len(list_queries()) + 1
    assert ask_key("  What   SIZE? ") == ask_key("what size?")
    assert ask_key("a") != ask_key("b") and ask_key("a").startswith("ask-")
    assert "Girt" in param_vocabulary("Member") and "Sheet" not in param_vocabulary("Member")
    assert param_vocabulary("WeldingReq")[0] == "WeldingReq"
