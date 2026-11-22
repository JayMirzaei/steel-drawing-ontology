"""Competency questions as named SPARQL queries, and a runner that returns typed rows.

Each ``.rq`` file in this folder is one vetted query. Its header comments carry the metadata::

    # id: CQ09
    # title: Requirement clauses on one topic
    # question: Which requirement clauses cover a topic (welding by default)?
    # param: topic = WeldingReq

A ``param`` line declares a SPARQL variable that the caller may bind to a term of the ontology
(a member of a controlled vocabulary); the value after ``=`` is the default. Nothing else can be
injected into a query, which keeps the set safe to expose to a natural-language front end.

Queries run over the data together with the ontology, so ``rdfs:subClassOf*`` paths work on
plain extracted data. A query about a reasoner-defined class says so in its header
(``# reasoner: required``); ``run_query`` then runs the OWL RL reasoner over the data first,
so the query asks for the class (``?sheet a steel:MarkedUpSheet``) instead of repeating the
class definition in SPARQL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from importlib import resources

from rdflib import RDF, Graph, Literal, URIRef
from rdflib.term import Node as RdfTerm

from steel_ontology.vocabulary import STEEL, load_ontology, local_name

Value = str | int | Decimal | bool | None
Row = dict[str, Value]

_HEADER = re.compile(r"^#\s*(id|title|question|param|reasoner):\s*(.+?)\s*$")


@dataclass(frozen=True)
class Query:
    """One named query: metadata from the file header plus the SPARQL text.

    ``needs_reasoner`` is true when the query asks for a reasoner-defined class.
    """

    name: str
    id: str
    title: str
    question: str
    params: dict[str, str]
    text: str
    needs_reasoner: bool = False


@dataclass(frozen=True)
class QueryResult:
    """Rows of one query run. Each row maps a column name to a Python value."""

    query: Query
    columns: tuple[str, ...]
    rows: list[Row]

    def column(self, name: str) -> list[Value]:
        """All values of one column, in row order."""
        return [row[name] for row in self.rows]


class UnknownQuery(KeyError):
    """No query with that name or id."""


@cache
def _load() -> dict[str, Query]:
    queries = {}
    for entry in sorted(resources.files(__package__).iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".rq"):
            query = _parse(entry.name.removesuffix(".rq"), entry.read_text(encoding="utf-8"))
            queries[query.name] = query
    return queries


def _parse(stem: str, text: str) -> Query:
    meta: dict[str, str] = {}
    params: dict[str, str] = {}
    for line in text.splitlines():
        match = _HEADER.match(line)
        if not match:
            continue
        key, value = match.groups()
        if key == "param":
            variable, default = (part.strip() for part in value.split("=", 1))
            params[variable] = default
        else:
            meta[key] = value
    name = stem.split("_", 1)[1].replace("_", "-")
    reasoner = meta.get("reasoner", "")
    if reasoner not in ("", "required"):
        raise ValueError(f"{stem}: 'reasoner:' must be 'required', not {reasoner!r}")
    needs_reasoner = reasoner == "required"
    return Query(name, meta["id"], meta["title"], meta["question"], params, text, needs_reasoner)


def list_queries() -> list[Query]:
    """Every query, ordered by id."""
    return sorted(_load().values(), key=lambda q: q.id)


def get_query(name: str) -> Query:
    """Find a query by name (``marked-up-sheets``) or id (``CQ01``, case-insensitive)."""
    queries = _load()
    if name in queries:
        return queries[name]
    for query in queries.values():
        if query.id.lower() == name.lower():
            return query
    raise UnknownQuery(name)


def run_query(data: Graph, name: str, **params: str) -> QueryResult:
    """Run a named query over ``data`` and return typed rows.

    ``params`` override the defaults declared in the query file. Each value is the local name of
    an ontology term, for example ``run_query(g, "requirement-clauses", topic="BoltingReq")``.
    A query that needs the reasoner gets the data with OWL RL inferences added.
    """
    query = get_query(name)
    unknown = set(params) - set(query.params)
    if unknown:
        raise ValueError(f"query {query.name} has no parameter(s) {sorted(unknown)}")
    ontology = load_ontology()
    bindings = {
        variable: _ontology_term(ontology, value)
        for variable, value in {**query.params, **params}.items()
    }
    if query.needs_reasoner:
        data = _with_inferences(data)
    result = (data + ontology).query(query.text, initBindings=bindings)
    columns = tuple(str(v) for v in result.vars or () if str(v) not in bindings)
    rows = [{column: _to_python(row[column]) for column in columns} for row in result]
    return QueryResult(query, columns, rows)


_INFERRED: dict[frozenset, Graph] = {}
_INFERRED_KEEP = 8


def _with_inferences(data: Graph) -> Graph:
    """The data plus its OWL RL inferences, reused while the same triples are asked about again.

    Keyed by the triples themselves, not the graph object, so an edited graph is reasoned over
    afresh. The cached graph is only read: ``run_query`` queries a union with the ontology.
    """
    from steel_ontology.reason import infer  # reason imports nothing from this package

    key = frozenset(data)
    if key not in _INFERRED:
        if len(_INFERRED) >= _INFERRED_KEEP:
            _INFERRED.pop(next(iter(_INFERRED)))
        _INFERRED[key] = infer(data).graph
    return _INFERRED[key]


def _ontology_term(ontology: Graph, name: str) -> URIRef:
    term = STEEL[name]
    if (term, RDF.type, None) not in ontology:
        raise ValueError(f"{name!r} is not a term of the ontology")
    return term


def _to_python(term: RdfTerm | None) -> Value:
    """Literals become Python values; ontology terms their local name; other IRIs stay whole."""
    if term is None:
        return None
    if isinstance(term, Literal):
        value = term.toPython()
        return str(term) if isinstance(value, Literal) else value
    if isinstance(term, URIRef):
        return local_name(term)
    return str(term)
