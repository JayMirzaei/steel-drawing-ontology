"""Natural-language questions, answered only through the vetted named queries.

A question is routed to one of the competency queries in ``steel_ontology.queries`` and that
query's parameters are filled with terms of the ontology. Nothing else ever runs: there is no
free-form SPARQL and no generated text in the answer. The answer is the query's rows, and each
row carries the evidence (sheet, zone, confidence) of the objects it names.

Routing has two stages:

1. A deterministic keyword router (``route``). It scores each query by weighted patterns and
   finds parameter values by matching the names of vocabulary members in the question
   ("bolting" -> ``BoltingReq``). Same question, same answer, no model, no network.
2. An optional model fallback, used only when no rule matches and a provider is given. The
   model may only pick a query name from the list and parameter values from the vocabulary; its
   choice is checked exactly like a rule's and refused when it names anything else.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

from rdflib import Graph, URIRef

from steel_ontology.extract.providers.base import Provider, ProviderError, Request, parse_json
from steel_ontology.models import NODE_CLASSES, Node
from steel_ontology.queries import Query, Row, UnknownQuery, get_query, list_queries, run_query
from steel_ontology.vocabulary import STEEL, enumerations, local_name

# query name -> (pattern, weight): the words that say what a question is about. A query is a
# candidate only when at least one of its own patterns matches; parameter values found in the
# question ("bolting", "column") then add to its score, but never make a query a candidate on
# their own. The highest score wins if it reaches THRESHOLD; a tie goes to the lower query id.
KEYWORDS: dict[str, tuple[tuple[str, int], ...]] = {
    "marked-up-sheets": (
        (r"mark(ed)?[ -]?ups?", 2),
        (r"highlight", 2),
        (r"third[ -]part", 2),
        (r"which sheets", 1),
    ),
    "reference-only-sheets": ((r"reference only", 3), (r"not (to )?be buil[dt]", 2)),
    "mixed-author-packages": ((r"different (authors|roles)", 3), (r"mixed", 1), (r"author", 1)),
    "weighted-assemblies": ((r"assembl", 2), (r"\bweigh", 1), (r"lift", 1), (r"shipping", 1)),
    "responsibility-boundaries": (
        (r"limits? (the )?(engineer|design)", 3),
        (r"responsibility (boundar|limit)", 3),
        (r"boundar", 1),
    ),
    "field-confirm-items": (
        (r"confirm(ed)? (on|in) (site|the field)", 3),
        (r"field[ -]?(confirm|verif|measure)", 3),
        (r"site measure", 2),
    ),
    "raster-derived-sheets": ((r"raster", 3), (r"scan(ned)?", 2), (r"inaccurate", 1)),
    "area-loads-by-zone": (
        (r"area loads?", 2),
        (r"kpa", 2),
        (r"\bloads?\b", 1),
        (r"design loads?", 1),
        (r"zones?", 1),
    ),
    "requirement-clauses": (
        (r"requirements?", 2),
        (r"\brequire", 1),
        (r"clauses?", 2),
        (r"general notes?", 2),
        (r"what (do|does) the notes? say about", 2),
        (r"specif(y|ied|ication)", 1),
    ),
    "schedule-cells-by-kind": ((r"cells?", 2), (r"schedule", 1), (r"by (the )?supplier", 1)),
    "reinforcing-members": ((r"reinforc", 3), (r"strengthen", 3)),
    "scope-items": ((r"scope", 2), (r"who (supplies|installs)", 2), (r"work items?", 1)),
    "force-records-by-load-type": (
        (r"forces?", 2),
        (r"reactions?", 2),
        (r"\bkn\b", 2),
        (r"load (type|combination)s?", 1),
    ),
    "default-rules": ((r"default", 2), (r"unless noted", 2), (r"rules?", 1)),
    "construction-sequence-steps": (
        (r"sequence", 2),
        (r"steps?", 1),
        (r"order of (work|erection)", 2),
    ),
    "tender-only-values": ((r"tender", 3), (r"\bbid", 2)),
    "elements-by-class": (
        (r"what (size|section)", 2),
        (r"how many", 2),
        (r"where (is|are)", 2),
        (r"list (the |all )", 1),
        (r"\b(are|is) there\b", 1),
        (r"elements?|members?", 1),
        (r"sizes?|sections?|quantit", 1),
    ),
    "sheet-revisions": (
        (r"revisions?", 2),
        (r"issued", 2),
        (r"sheet (list|index)", 2),
        (r"sheets? (are )?in the set", 2),
        (r"which sheets", 1),
        (r"\bwhen\b", 1),
    ),
    "annotation-texts": (
        (r"stamps?", 2),
        (r"(query|hand) notes?", 2),
        (r"annotations?", 2),
        (r"what (do|does) .* say", 1),
        (r"received", 1),
        (r"who drew", 1),
    ),
    "cited-standards": ((r"standards?", 2), (r"codes?\b", 2), (r"\b(csa|astm|aisc|cisc)\b", 2)),
    "connections-designed-by-others": (
        (r"connections?\b.*\bdesign(ed|s)? by (others|someone else|another)", 4),
        (r"design(ed|s)? by (others|someone else|another)", 2),
        (r"connection engineer", 3),
        (r"who designs? (the )?connections?", 3),
        (r"hold[ -]?points?", 2),
        (r"connections?", 1),
    ),
    "elements-by-responsibility": (
        (r"\bby others\b", 1),
        (r"responsib", 2),
        (r"who (designs|details|provides)", 2),
    ),
    "element-forces": (
        (r"\b(loads?|forces?|reactions?) (on|at|for|in)\b", 2),
        (r"\b(axial|shear|moment|tension|compression)( force| load)? (on|at|in|for)\b", 2),
        (r"\b(axial|shear|moment|tension|compression)\b", 1),
        (r"\bfactored\b", 1),
        (r"\b[ct]f\b", 1),
    ),
    "schedule-totals": (
        (r"total weight", 2),
        (r"(printed|schedule|declared) totals?", 2),
        (r"add(s)? up", 2),
        (r"\btotals?\b", 1),
    ),
}
THRESHOLD = 2

# Everyday words for vocabulary members whose own name a person would not type.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "WeldingReq": ("weld", "welds"),
    "BoltingReq": ("bolt", "bolts"),
    "CoatingReq": ("paint", "painting", "galvaniz"),
    "MaterialReq": ("grade", "steel grade"),
    "InspectionReq": ("field review", "testing"),
    "ScopeExclusionReq": ("by others", "excluded", "not in scope"),
    "SubmittalReq": ("submit", "calculations"),
    "BySupplierCell": ("by supplier", "by the supplier"),
    "PercentOfYieldRule": ("yield",),
    "LoadCombination": ("combination",),
    "Connection": ("base plate", "base plates"),
}
_SUFFIXES = {"req", "load", "cell", "rule", "kind"}
# A generic last word is not dropped when what is left is an everyday word: "other" alone must
# not name OtherLoad, nor "total" TotalLoad, nor "number" NumberCell.
_TOO_COMMON = {"other", "total", "number", "text", "blank", "full", "see"}
_MARK = re.compile(r"[A-Za-z]*\d[\w./-]*|[A-Za-z]+-\d[\w./-]*")

ASK_SCHEMA_NAME = "query_choice"
NO_QUERY = "none"


@dataclass(frozen=True)
class Citation:
    """Where one object of an answer row was read."""

    node: str
    sheet_number: str | None
    page: int | None
    zone: str | None
    confidence: str | None

    def to_text(self) -> str:
        sheet = self.sheet_number or (f"page {self.page}" if self.page else "unknown sheet")
        zone = f" zone {self.zone}" if self.zone else ""
        return f"{sheet}{zone} ({self.confidence or 'confidence not stated'})"


@dataclass(frozen=True)
class AnswerRow:
    """One result row with the evidence of every object it names."""

    values: Row
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class Answer:
    """The outcome of ``ask``.

    ``route`` says who chose the query: ``rule`` (the keyword router), ``model`` (the fallback)
    or ``none`` (nothing matched; ``rows`` is empty and ``notes`` says what can be asked).
    """

    question: str
    route: Literal["rule", "model", "none"]
    query: Query | None
    params: dict[str, str]
    columns: tuple[str, ...]
    rows: tuple[AnswerRow, ...]
    notes: tuple[str, ...]

    def to_text(self) -> str:
        """The answer as plain text: the query used, then each row with its citations."""
        if self.query is None:
            return "\n".join(
                ["I could not route this question to one of the vetted queries.", *self.notes]
            )
        params = "".join(f" {name}={value}" for name, value in self.params.items())
        lines = [
            f"{self.query.id} {self.query.name}{params} (chosen by {self.route}): "
            f"{len(self.rows)} row(s)"
        ]
        lines += [f"note: {note}" for note in self.notes]
        for row in self.rows:
            shown = {k: v for k, v in row.values.items() if v not in (None, "")}
            lines.append(
                "  " + "  ".join(f"{name}={_display(value)}" for name, value in shown.items())
            )
            lines += [f"      evidence: {citation.to_text()}" for citation in row.citations]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """A JSON-ready form of the answer."""
        return {
            "question": self.question,
            "route": self.route,
            "query": self.query.name if self.query else None,
            "params": self.params,
            "notes": list(self.notes),
            "rows": [
                {
                    "values": {name: _json_value(value) for name, value in row.values.items()},
                    "evidence": [vars(citation) for citation in row.citations],
                }
                for row in self.rows
            ],
        }


@dataclass(frozen=True)
class Route:
    """A router decision: the query, the parameters found, and remarks for the reader."""

    query: str
    params: dict[str, str]
    notes: tuple[str, ...] = ()


def route(question: str) -> Route | None:
    """Pick a query for the question with keyword rules only; ``None`` when nothing fits.

    A parameter value alone never chooses a query: "column" names a class, not a question, so
    a query needs one of its own keywords to be a candidate at all.
    """
    text = " ".join(question.lower().split())
    best: tuple[int, str, dict[str, str]] | None = None
    for query in list_queries():
        topic = sum(
            weight for pattern, weight in KEYWORDS.get(query.name, ()) if re.search(pattern, text)
        )
        if topic == 0:
            continue
        params = _find_params(query, text)
        score = topic + 2 * len(params)
        if score >= THRESHOLD and (best is None or score > best[0]):
            best = (score, query.name, params)
    if best is None:
        return None
    return Route(best[1], best[2])


def ask(graph: Graph, question: str, *, provider: Provider | None = None) -> Answer:
    """Answer a question over a data graph by running one vetted query.

    ``provider`` enables the model fallback for questions the keyword router cannot place.
    """
    decision = route(question)
    chosen_by: Literal["rule", "model", "none"] = "rule"
    notes: list[str] = []
    if decision is None and provider is not None:
        try:
            decision = _route_with_model(question, provider)
            chosen_by = "model"
        except ProviderError as error:
            notes.append(f"model fallback failed: {error}")
    if decision is None:
        notes.append(
            "These are the questions I can answer: " + "; ".join(q.question for q in list_queries())
        )
        return Answer(question, "none", None, {}, (), (), tuple(notes))
    query = get_query(decision.query)
    columns, rows, run_notes = _run(graph, query, decision.params)
    rows, filter_note = _filter_by_marks(rows, question)
    notes += [*decision.notes, *run_notes, *filter_note]
    answer_rows = tuple(AnswerRow(row, _citations(graph, row)) for row in rows)
    return Answer(question, chosen_by, query, decision.params, columns, answer_rows, tuple(notes))


def _run(
    graph: Graph, query: Query, params: dict[str, str]
) -> tuple[tuple[str, ...], list[Row], list[str]]:
    """Run the query; a vocabulary parameter the question did not name is tried for every value.

    A query's own default ("welding") would silently narrow an open question ("what do the
    notes require?"), so an unnamed parameter means "all of them": the query runs once per
    member of the vocabulary and each row says which member it belongs to. A parameter that
    names a class keeps its default, because the default class already covers its subclasses.
    """
    open_variables = [
        variable
        for variable, default in query.params.items()
        if variable not in params and default not in NODE_CLASSES
    ]
    if not open_variables:
        result = run_query(graph, query.name, **params)
        return result.columns, result.rows, []
    variable = open_variables[0]
    columns: tuple[str, ...] = ()
    rows: list[Row] = []
    for member in param_vocabulary(query.params[variable]):
        result = run_query(graph, query.name, **{**params, variable: member})
        columns = (variable, *result.columns)
        rows += [{variable: member, **row} for row in result.rows if any(row.values())]
    return columns, rows, [f"the question names no {variable}, so every {variable} was tried"]


def ask_key(question: str) -> str:
    """The provider request key of a question (stable across runs, used by recordings)."""
    normalised = " ".join(question.lower().split())
    return "ask-" + hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:12]


def ask_schema() -> dict[str, Any]:
    """The JSON Schema of the model's choice: a query name (or ``none``) and parameters."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["query", "params"],
        "properties": {
            "query": {"type": "string", "enum": [q.name for q in list_queries()] + [NO_QUERY]},
            "params": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "value"],
                    "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                },
            },
        },
    }


def _route_with_model(question: str, provider: Provider) -> Route | None:
    """Let a model choose among the vetted queries; verify everything it returns."""
    catalogue = []
    for query in list_queries():
        line = f"- {query.name}: {query.question}"
        for variable, default in query.params.items():
            allowed = ", ".join(param_vocabulary(default))
            line += f"\n    parameter {variable} (default {default}), one of: {allowed}"
        catalogue.append(line)
    system = (
        "You route a question about a steel drawing set to one of a fixed list of queries. "
        f"Answer with the query name and its parameters, or '{NO_QUERY}' when no query answers "
        "the question. You cannot write queries; you can only choose.\n\n" + "\n".join(catalogue)
    )
    request = Request(ask_key(question), system, question, ask_schema(), ASK_SCHEMA_NAME)
    choice = parse_json(provider.complete(request), provider.name)
    name = choice.get("query")
    if name == NO_QUERY:
        return None
    try:
        query = get_query(str(name))
    except UnknownQuery as error:
        raise ProviderError(f"the model chose {name!r}, which is not a vetted query") from error
    params: dict[str, str] = {}
    notes = []
    for item in choice.get("params") or []:
        variable, value = str(item.get("name")), str(item.get("value"))
        if variable in query.params and value in param_vocabulary(query.params[variable]):
            params[variable] = value
        else:
            notes.append(f"the model's parameter {variable}={value} is not allowed and was ignored")
    return Route(query.name, params, tuple(notes))


def _find_params(query: Query, text: str) -> dict[str, str]:
    """Parameter values named in the question; the longest matching phrase wins."""
    found: dict[str, str] = {}
    for variable, default in query.params.items():
        best: tuple[int, str] | None = None
        for member in param_vocabulary(default):
            for phrase in _phrases(member):
                if re.search(rf"\b{phrase}(?:s|es)?\b", text) and (
                    best is None or len(phrase) > best[0]
                ):
                    best = (len(phrase), member)
        if best is not None:
            found[variable] = best[1]
    return found


@cache
def param_vocabulary(default: str) -> tuple[str, ...]:
    """The terms a parameter may take: the default's enumeration, or its class family."""
    for members in enumerations().values():
        if default in members:
            return members
    if default in NODE_CLASSES:
        root = next(c for c in NODE_CLASSES[default].__mro__ if Node in c.__bases__)
        return tuple(name for name, cls in NODE_CLASSES.items() if issubclass(cls, root))
    return (default,)


@cache
def _phrases(member: str) -> tuple[str, ...]:
    """Regex phrases that name a vocabulary member.

    ``LiveLoad`` is named by "live load" and by "live" (the generic last word may be left
    out, unless what is left is an everyday word such as "other"); the listed synonyms count
    too.
    """
    words = [w.lower() for w in re.findall(r"[A-Z][a-z0-9]*", member)]
    shortened = len(words) > 1 and words[-1] in _SUFFIXES
    if shortened and len(words) == 2 and words[0] in _TOO_COMMON:
        shortened = False
    names = [words[:-1], words] if shortened else [words]
    own = (r"[ -]?".join(re.escape(word) for word in name) for name in names)
    return (*own, *(re.escape(s).replace(r"\ ", " ") for s in SYNONYMS.get(member, ())))


def _filter_by_marks(rows: list[Row], question: str) -> tuple[list[Row], list[str]]:
    """Keep the rows that name a mark from the question (B3, S-101), when any row does."""
    marks = {mark.upper() for mark in _MARK.findall(question)}
    if not marks:
        return rows, []
    kept = [
        row for row in rows if any(isinstance(v, str) and v.upper() in marks for v in row.values())
    ]
    if not kept:
        return rows, []
    named = ", ".join(sorted(marks & {str(v).upper() for row in kept for v in row.values()}))
    return kept, [f"rows limited to those naming {named}"]


def _citations(graph: Graph, row: Row) -> tuple[Citation, ...]:
    """Evidence of every object named in a row, read from the graph."""
    citations = []
    for value in row.values():
        if not isinstance(value, str) or "://" not in value:
            continue
        node = URIRef(value)
        for evidence in sorted(graph.objects(node, STEEL.evidencedBy)):
            sheet = graph.value(evidence, STEEL.onSheet)
            number = graph.value(sheet, STEEL.sheetNumber) if sheet is not None else None
            page = graph.value(sheet, STEEL.pageIndex) if sheet is not None else None
            zone = graph.value(evidence, STEEL.regionBox)
            confidence = graph.value(evidence, STEEL.confidence)
            citations.append(
                Citation(
                    node=value,
                    sheet_number=str(number) if number is not None else None,
                    page=int(page) if page is not None else None,
                    zone=str(zone) if zone is not None else None,
                    confidence=local_name(confidence) if confidence is not None else None,
                )
            )
    return tuple(citations)


def _display(value: Any) -> str:
    """Object IRIs are shown by their last segment; everything else as is."""
    text = str(value)
    return text.rsplit("/", 1)[-1] if "://" in text else text


def _json_value(value: Any) -> Any:
    return value if isinstance(value, str | int | bool) or value is None else str(value)
