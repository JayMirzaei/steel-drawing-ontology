"""Streamlit explorer: browse the vocabulary, load data, validate, reason, query, ask.

Run with ``uv run streamlit run app/explorer.py``. The app only calls the package's public
functions; all logic lives in ``steel_ontology``. It needs no API key: questions are routed by
the keyword router, and the example data ships with the repository.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import streamlit as st
from rdflib import Graph

from steel_ontology import reference
from steel_ontology.ask import Answer, ask, param_vocabulary
from steel_ontology.extract.pages import render_pages
from steel_ontology.graph import GraphMappingError, from_graph, load_graph
from steel_ontology.queries import list_queries, run_query
from steel_ontology.reason import InferenceResult, hermit_available, infer
from steel_ontology.site import QUESTIONS, outline_zones
from steel_ontology.validate import ValidationReport, validate
from steel_ontology.vocabulary import VERSION, defined_classes

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "kestrel-platform"
SOURCES = {
    "Example: gold extraction": "gold.json",
    "Example: broken variant": "broken.json",
    "Upload a file": None,
}
UPLOAD_TYPES = ["json", "ttl", "nt", "rdf", "xml", "jsonld"]


@st.cache_resource(show_spinner=False)
def parse_data(name: str, content: bytes) -> Graph:
    """Parse uploaded or example data (extraction JSON or RDF) into a graph."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / Path(name).name
        path.write_bytes(content)
        return load_graph(path)


@st.cache_resource(show_spinner="Validating against the SHACL shapes...")
def cached_validation(_graph: Graph, key: str) -> ValidationReport:
    return validate(_graph)


@st.cache_resource(show_spinner="Running the reasoner...")
def cached_inference(_graph: Graph, key: str, engine: str) -> InferenceResult:
    return infer(_graph, engine=engine)


@st.cache_resource(show_spinner=False)
def example_pages() -> dict[int, bytes]:
    """PNG of every sheet of the example PDF, by page number."""
    return {page.number: page.png for page in render_pages(EXAMPLE / "drawings.pdf", max_edge=1600)}


@st.cache_resource(show_spinner=False)
def vocabulary_reference() -> reference.Reference:
    return reference.build_reference()


def short(value: object) -> object:
    """Object IRIs are shown by their id; other values unchanged."""
    text = str(value)
    return text.rsplit("/", 1)[-1] if "://" in text else value


def choose_data() -> tuple[Graph | None, str, bool]:
    """Sidebar: pick the data. Returns the graph, a cache key and whether it is the example."""
    st.sidebar.header("Data")
    source = st.sidebar.radio("Source", list(SOURCES), key="source")
    file_name = SOURCES[source]
    if file_name is not None:
        content = (EXAMPLE / file_name).read_bytes()
        name = file_name
    else:
        upload = st.sidebar.file_uploader("Extraction JSON or RDF", type=UPLOAD_TYPES)
        if upload is None:
            st.sidebar.info("Upload an extraction (.json) or an RDF file (.ttl).")
            return None, "", False
        content, name = upload.getvalue(), upload.name
    key = hashlib.sha256(content).hexdigest()
    try:
        graph = parse_data(name, content)
    except Exception as error:  # any parser error is shown to the user, not raised
        st.sidebar.error(f"Could not read {name}: {error}")
        return None, "", False
    st.sidebar.caption(f"{name}: {len(graph)} triples")
    return graph, key, file_name is not None


def vocabulary_tab() -> None:
    ref = vocabulary_reference()
    st.caption(
        f"Version {ref.version}: {len(ref.classes)} classes, {len(ref.properties)} properties, "
        f"{len(ref.enumerations)} closed vocabularies, {len(ref.defined)} reasoner-defined "
        f"classes, {len(ref.shapes)} shapes. Generated from the Turtle files."
    )
    kind = st.radio(
        "Show",
        ["Classes", "Properties", "Closed vocabularies", "Reasoner-defined classes", "Shapes"],
        horizontal=True,
        key="vocabulary_kind",
    )
    needle = st.text_input("Filter", key="vocabulary_filter", placeholder="e.g. weld").lower()
    tables = {
        "Classes": [
            {"class": c.name, "subclass of": ", ".join(c.parents), "meaning": c.comment}
            for c in ref.classes
        ],
        "Properties": [
            {
                "property": p.name,
                "kind": p.kind + (", functional" if p.functional else ""),
                "domain": p.domain,
                "range": p.range,
                "meaning": p.comment,
            }
            for p in ref.properties
        ],
        "Closed vocabularies": [
            {"vocabulary": e.name, "members": ", ".join(m for m, _ in e.members)}
            for e in ref.enumerations
        ],
        "Reasoner-defined classes": [
            {"class": d.name, "definition": d.definition, "why": d.comment} for d in ref.defined
        ],
        "Shapes": [
            {
                "shape": s.name,
                "applies to": s.target,
                "severity": sev,
                "check": what,
                "message": msg,
            }
            for s in ref.shapes
            for sev, what, msg in s.checks
        ],
    }
    rows = [row for row in tables[kind] if not needle or needle in " ".join(row.values()).lower()]
    st.caption(f"{len(rows)} of {len(tables[kind])}")
    st.dataframe(rows, hide_index=True, width="stretch")


def data_tab(graph: Graph, is_example: bool) -> None:
    try:
        extraction = from_graph(graph)
    except GraphMappingError as error:
        st.warning(f"The graph loads, but not as typed objects: {error}")
        return
    counts: dict[str, int] = {}
    for node in extraction.nodes:
        counts[type(node).__name__] = counts.get(type(node).__name__, 0) + 1
    st.caption(f"{len(extraction.nodes)} objects in {len(counts)} classes.")
    chosen = st.selectbox("Class", sorted(counts, key=lambda name: (-counts[name], name)))
    rows = [
        {k: (", ".join(map(str, v)) if isinstance(v, list) else v) for k, v in node.items()}
        for node in extraction.model_dump(mode="json", exclude_none=True)["nodes"]
        if node["type"] == chosen
    ]
    st.dataframe(rows, hide_index=True, width="stretch")
    if is_example:
        st.subheader("The sheets (synthetic)")
        pages = example_pages()
        page = st.select_slider("Page", options=sorted(pages), key="sheet_page")
        st.image(pages[page], width="stretch")


def validate_tab(graph: Graph, key: str) -> None:
    report = cached_validation(graph, key)
    summary = f"{len(report.violations)} violation(s), {len(report.warnings)} warning(s)"
    if report.conforms:
        st.success(f"Conforms: {summary}")
    else:
        st.error(f"Does not conform: {summary}")
    st.dataframe(
        [
            {
                "severity": f.severity.value,
                "object": short(f.focus_node),
                "property": (f.path or "").rsplit("#", 1)[-1],
                "message": f.message,
            }
            for f in report.findings
        ],
        hide_index=True,
        width="stretch",
    )


def reason_tab(graph: Graph, key: str) -> None:
    engines = ["owlrl", "hermit"] if hermit_available() else ["owlrl"]
    engine = st.radio("Engine", engines, horizontal=True, key="engine")
    st.caption(
        "owlrl is pure Python (OWL RL). hermit is a full OWL DL reasoner and is offered only "
        "when Java and owlready2 are present."
    )
    if not st.button("Run the reasoner", key="run_reasoner"):
        return
    result = cached_inference(graph, key, engine)
    if result.consistent:
        st.success("The data is consistent with the ontology.")
    for problem in result.inconsistencies:
        st.error(problem)
    interesting = set(defined_classes())
    rows = [
        {"object": short(iri), "inferred classes": ", ".join(found)}
        for iri in sorted(result.inferred_types)
        if (found := [n for n in result.inferred_types[iri] if n in interesting])
    ]
    st.caption(f"{len(rows)} object(s) gained a reasoner-defined class.")
    st.dataframe(rows, hide_index=True, width="stretch")


def queries_tab(graph: Graph) -> None:
    queries = {f"{q.id} {q.title}": q for q in list_queries()}
    query = queries[st.selectbox("Competency query", list(queries), key="query")]
    st.write(query.question)
    params = {}
    for variable, default in query.params.items():
        members = list(param_vocabulary(default))
        params[variable] = st.selectbox(
            variable, members, index=members.index(default), key=f"param_{query.name}_{variable}"
        )
    result = run_query(graph, query.name, **params)
    st.caption(f"{len(result.rows)} row(s)")
    st.dataframe(
        [{column: short(row[column]) for column in result.columns} for row in result.rows],
        hide_index=True,
        width="stretch",
    )
    with st.expander("SPARQL"):
        st.code(query.text, language="sparql")


def show_answer(answer: Answer, is_example: bool) -> None:
    if answer.query is None:
        st.warning(
            "I could not route this question to one of the vetted queries, so nothing is answered."
        )
        st.caption(answer.notes[-1])
        return
    params = " ".join(f"{name}={value}" for name, value in answer.params.items())
    st.caption(f"Routed by {answer.route} to {answer.query.id} {answer.query.name} {params}")
    for note in answer.notes:
        st.caption(note)
    filled = [
        c for c in answer.columns if any(row.values.get(c) not in (None, "") for row in answer.rows)
    ]
    st.dataframe(
        [
            {
                **{name: short(row.values[name]) for name in filled},
                "evidence": "; ".join(c.to_text() for c in row.citations),
            }
            for row in answer.rows
        ],
        hide_index=True,
        width="stretch",
    )
    if not is_example:
        return
    zones: dict[int, list[str]] = {}
    for row in answer.rows:
        for citation in row.citations:
            if citation.page and citation.zone:
                zones.setdefault(citation.page, []).append(citation.zone)
    for page, boxes in sorted(zones.items()):
        st.image(
            outline_zones(example_pages()[page], boxes),
            caption=f"Page {page}: the zones this answer cites",
            width="stretch",
        )


def ask_tab(graph: Graph, is_example: bool) -> None:
    st.caption(
        "A question is routed to one of the vetted queries by keyword rules. No model is "
        "called and no SPARQL is generated."
    )
    suggestion = st.selectbox("Try one", ["", *QUESTIONS], key="suggestion")
    typed = st.text_input("Question", key="question", placeholder="What size is beam B3?")
    question = typed or suggestion
    if question:
        show_answer(ask(graph, question), is_example)


def main() -> None:
    st.set_page_config(page_title="Steel drawing ontology", layout="wide")
    st.title("Steel drawing ontology explorer")
    st.caption(f"Vocabulary {VERSION}. The example drawing set is synthetic.")
    graph, key, is_example = choose_data()
    names = ["Vocabulary", "Data", "Validate", "Reason", "Queries", "Ask"]
    vocabulary, data, validation, reasoning, queries, asking = st.tabs(names)
    with vocabulary:
        vocabulary_tab()
    if graph is None:
        for tab in (data, validation, reasoning, queries, asking):
            with tab:
                st.info("Choose or upload data in the sidebar.")
        return
    with data:
        data_tab(graph, is_example)
    with validation:
        validate_tab(graph, key)
    with reasoning:
        reason_tab(graph, key)
    with queries:
        queries_tab(graph)
    with asking:
        ask_tab(graph, is_example)


main()
