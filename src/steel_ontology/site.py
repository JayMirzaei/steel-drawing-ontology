"""The static demo site: everything the package does, computed once and written as HTML.

``build_site`` runs the real pipeline on the synthetic example (render pages, replay the
recorded extraction, validate the good and the broken data, run the reasoner, run every
competency query, answer a list of questions) and writes plain HTML and CSS. There is no
JavaScript, no tracker and no external request: the pages can be opened from disk or served by
GitHub Pages.

The vocabulary reference is written to ``core.html`` with one anchor per term, so the ontology
IRI ``.../core#Beam`` lands on the right row once the site is published at that address.
"""

from __future__ import annotations

import io
import shutil
from collections.abc import Iterable, Sequence
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw

from steel_ontology import reference
from steel_ontology.ask import Answer, ask, param_vocabulary
from steel_ontology.extract import extract_pdf, get_provider
from steel_ontology.extract.pages import render_pages
from steel_ontology.graph import to_graph
from steel_ontology.models import Extraction, Sheet
from steel_ontology.queries import Query, list_queries, run_query
from steel_ontology.reason import infer
from steel_ontology.validate import ValidationReport, validate
from steel_ontology.vocabulary import VERSION, defined_classes, ontology_dir

REPOSITORY = "https://github.com/JayMirzaei/steel-drawing-ontology"
SHEET_EDGE = 1800
EVIDENCE_EDGE = 1400
EVIDENCE_COLOUR = (214, 40, 40)

QUESTIONS = (
    "What size is beam B3?",
    "Where are the columns?",
    "What do the notes say about bolting?",
    "Which sheets have third-party markup?",
    "What does the query note say?",
    "What is the default rule for connections?",
    "What is the live load?",
    "What is the factored load on C2?",
    "Which connections are designed by others?",
    "Which standards are cited?",
    "When was S-101 issued?",
    "Is the sky blue?",
)
"""Questions answered on the site by the keyword router alone."""

FALLBACK_QUESTION = "Who has to be told before coming to site?"
"""A question the router cannot place; the example's recording stands in for a model."""

NAV = (
    ("index.html", "Overview"),
    ("core.html", "Vocabulary"),
    ("example.html", "Example set"),
    ("validation.html", "Validation"),
    ("inferred.html", "Inference"),
    ("queries.html", "Queries"),
    ("questions.html", "Questions"),
)

CSS = """\
:root { --bg:#fbfaf7; --fg:#1d2126; --muted:#5b636c; --line:#d9d5cc; --accent:#9a3b1c;
  --panel:#f1eee7; --ok:#2f6f44; --warn:#8a6100; --bad:#a32020; }
@media (prefers-color-scheme: dark) { :root { --bg:#16181b; --fg:#e6e3dc; --muted:#a0a6ad;
  --line:#33373c; --accent:#e08a5f; --panel:#1f2226; --ok:#7fc494; --warn:#e0b560;
  --bad:#f08a8a; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
header, main, footer { max-width: 1080px; margin: 0 auto; padding: 0 16px; }
header { padding-top: 20px; }
header .name { font-weight: 700; letter-spacing: .02em; }
nav { display:flex; flex-wrap:wrap; gap: 4px 18px; margin: 10px 0 0; padding-bottom: 12px;
  border-bottom: 2px solid var(--fg); }
nav a { color: var(--fg); text-decoration: none; }
nav a.here { color: var(--accent); font-weight: 600; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 28px 0 8px; }
h2 { font-size: 1.25rem; margin: 34px 0 6px; }
h3 { font-size: 1.02rem; margin: 22px 0 4px; }
p, li { max-width: 72ch; }
a { color: var(--accent); }
code, pre { font: 13px/1.5 ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
pre { background: var(--panel); border: 1px solid var(--line); padding: 10px 12px;
  overflow-x: auto; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 8px 0 16px; }
th, td { text-align: left; vertical-align: top; padding: 5px 10px 5px 0;
  border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; white-space: nowrap; }
td.num { font-variant-numeric: tabular-nums; }
img { max-width: 100%; height: auto; border: 1px solid var(--line); background: #fff; }
figure { margin: 14px 0 22px; }
figcaption, .muted { color: var(--muted); font-size: 14px; }
.tag { display:inline-block; padding: 0 7px; border: 1px solid currentColor; border-radius: 3px;
  font-size: 12px; font-weight: 600; }
.Violation, .bad { color: var(--bad); } .Warning { color: var(--warn); } .ok { color: var(--ok); }
.note { border-left: 3px solid var(--accent); padding: 2px 0 2px 12px; margin: 14px 0; }
.flow { display:flex; flex-wrap:wrap; gap: 6px; padding: 0; list-style: none; max-width: none; }
.flow li { border: 1px solid var(--fg); padding: 6px 10px; background: var(--panel);
  font-size: 14px; }
.flow li + li::before { content: "\\2192"; margin: 0 8px 0 -4px; color: var(--accent); }
details { margin: 4px 0 10px; } summary { cursor: pointer; color: var(--muted); }
footer { margin-top: 48px; padding-top: 12px; padding-bottom: 32px;
  border-top: 1px solid var(--line); color: var(--muted); font-size: 14px; }
"""


def build_site(output: str | Path, example: str | Path) -> list[Path]:
    """Write the site into ``output`` from the example folder; return the HTML pages written."""
    output, example = Path(output), Path(example)
    (output / "img").mkdir(parents=True, exist_ok=True)
    gold = Extraction.from_json((example / "gold.json").read_text(encoding="utf-8"))
    broken = Extraction.from_json((example / "broken.json").read_text(encoding="utf-8"))
    graph = to_graph(gold)
    pdf = example / "drawings.pdf"
    sheets = _write_sheet_images(pdf, output / "img")
    for name in ("gold.json", "gold.ttl", "broken.json", "drawings.pdf"):
        shutil.copyfile(example / name, output / name)
    for name in ("core.ttl", "shapes.ttl"):
        shutil.copyfile(ontology_dir() / name, output / name)
    _write_version_iri(output)
    (output / "style.css").write_text(CSS, encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")

    ref = reference.build_reference()
    pages = {
        "index.html": ("Steel drawing ontology", _overview(ref, gold)),
        "core.html": ("Vocabulary reference", reference.to_html_body(ref)),
        "shapes.html": ("Shapes", _shapes_stub()),
        "example.html": ("The example drawing set", _example(example, gold, sheets)),
        "validation.html": ("Validation", _validation(validate(gold), validate(broken))),
        "inferred.html": ("Inference", _inferred(gold, ref)),
        "queries.html": ("Competency queries", _queries(graph)),
        "questions.html": ("Questions", _questions(graph, example, sheets, output / "img")),
    }
    written = []
    for name, (title, body) in pages.items():
        path = output / name
        path.write_text(_page(name, title, body), encoding="utf-8")
        written.append(path)
    return written


def _write_version_iri(output: Path) -> None:
    """Make ``owl:versionIRI`` (``.../core/<version>``) resolve: Pages serves ``<path>.html``.

    The version page links the Turtle of exactly this version, copied beside it.
    """
    folder = output / "core"
    folder.mkdir(exist_ok=True)
    shutil.copyfile(ontology_dir() / "core.ttl", folder / f"{VERSION}.ttl")
    page = (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Core vocabulary {VERSION} - steel drawing ontology</title>"
        '<link rel="stylesheet" href="../style.css"></head><body><main>'
        f"<h1>Core vocabulary, version {VERSION}</h1>"
        f'<ul><li><a href="{VERSION}.ttl">core.ttl of version {VERSION}</a> (Turtle)</li>'
        '<li><a href="../core.html">Vocabulary reference</a></li>'
        '<li><a href="../index.html">Overview</a></li></ul></main></body></html>\n'
    )
    (folder / f"{VERSION}.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Page frame and small HTML helpers
# ---------------------------------------------------------------------------------------------


def _page(name: str, title: str, body: str) -> str:
    links = "".join(
        f'<a href="{href}"{" class=here" if href == name else ""}>{escape(label)}</a>'
        for href, label in NAV
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)} - steel drawing ontology</title>"
        '<link rel="stylesheet" href="style.css"></head><body>'
        f'<header><div class="name">Steel drawing ontology {escape(VERSION)}</div>'
        f"<nav>{links}</nav></header>"
        f"<main><h1>{escape(title)}</h1>\n{body}\n</main>"
        "<footer>Built by <code>steel-ontology docs --site</code> from the synthetic example. "
        "Everything on this site is synthetic. "
        f'<a href="{REPOSITORY}">Source on GitHub</a>. MIT licence, Jay Mirzaei.</footer>'
        "</body></html>\n"
    )


def _table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    head = "".join(f"<th>{escape(str(cell))}</th>" for cell in header)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    table = f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    return f'<div class="scroll">{table}</div>'


def _text(value: object) -> str:
    """A cell value, escaped; object IRIs are shortened to their id."""
    if value is None:
        return ""
    text = str(value)
    return escape(text.rsplit("/", 1)[-1] if "://" in text else text)


# ---------------------------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------------------------


def _overview(ref: reference.Reference, gold: Extraction) -> str:
    steps = (
        "Drawing PDF",
        "Pages: image + text layer",
        "Typed objects with evidence",
        "RDF graph",
        "SHACL validation + OWL inference",
        "Named queries",
        "Answers that cite the sheet",
    )
    flow = "".join(f"<li>{escape(step)}</li>" for step in steps)
    return f"""
<p>An OWL + SHACL vocabulary for structural steel fabrication drawings, with a small pipeline
around it: a drawing set is read into typed objects, written as a graph, checked, reasoned over
and queried. Every fact keeps a pointer to the sheet and the zone it was read from.</p>
<ul class="flow">{flow}</ul>
<p class="note">Everything on this site is computed from one <a href="example.html">synthetic
four-sheet drawing set</a> that a script in the repository draws. Every project, name and
number in it is invented. The site is static: it was built once by
<code>steel-ontology docs --site</code> and nothing runs when you read it.</p>
<h2>The vocabulary in numbers</h2>
{
        _table(
            ["", "Count", ""],
            [
                [
                    "Classes for extracted data",
                    len(ref.classes),
                    "sheets, views, members, connections, schedules, clauses, evidence",
                ],
                ["Properties", len(ref.properties), "values are kept as printed"],
                [
                    "Closed vocabularies",
                    len(ref.enumerations),
                    "fixed lists: a value outside the list fails validation",
                ],
                [
                    "Reasoner-defined classes",
                    len(ref.defined),
                    "each answers a question a fabricator asks",
                ],
                ["SHACL shapes", len(ref.shapes), "completeness, ranges and table arithmetic"],
                ["Competency queries", len(list_queries()), "the only way questions are answered"],
            ],
        )
    }
<h2>What to look at</h2>
<ul>
<li><a href="core.html">Vocabulary reference</a>: every class, property, vocabulary and shape,
generated from the Turtle files.</li>
<li><a href="example.html">The example set</a>: the four sheets and the {len(gold.nodes)} objects
read from them.</li>
<li><a href="validation.html">Validation</a>: the correct extraction passes; a copy with
typical extractor mistakes fails, with readable messages.</li>
<li><a href="inferred.html">Inference</a>: classes the reasoner adds, for example which sheets
carry third-party markup.</li>
<li><a href="queries.html">Queries</a>: each competency question with its SPARQL and its
result on the example.</li>
<li><a href="questions.html">Questions</a>: plain-language questions routed to those queries,
with the evidence outlined on the sheet.</li>
</ul>
<h2>Run it yourself</h2>
<pre>git clone {REPOSITORY}
cd steel-drawing-ontology
uv sync
uv run steel-ontology validate examples/kestrel-platform/gold.json
uv run steel-ontology ask examples/kestrel-platform/gold.json "What size is beam B3?"</pre>
"""


def _shapes_stub() -> str:
    return (
        '<p>The SHACL shapes are listed in the <a href="core.html#section-shapes">vocabulary '
        'reference</a>. The source file is <a href="shapes.ttl">shapes.ttl</a>.</p>'
    )


def _write_sheet_images(pdf: Path, folder: Path) -> dict[int, bytes]:
    """Render every page for the site; return the PNG bytes by page number."""
    sheets = {}
    for page in render_pages(pdf, max_edge=SHEET_EDGE):
        (folder / f"sheet-{page.number}.png").write_bytes(page.png)
        sheets[page.number] = page.png
    return sheets


def _example(example: Path, gold: Extraction, sheets: dict[int, bytes]) -> str:
    by_page = {sheet.page_index: sheet for sheet in gold.of_type(Sheet)}
    figures = "".join(
        f'<figure><a href="img/sheet-{number}.png"><img src="img/sheet-{number}.png" '
        f'alt="Sheet {escape(by_page[number].sheet_number or "")}: synthetic drawing"></a>'
        f"<figcaption>Page {number}: {escape(by_page[number].sheet_number or '')} "
        f"{escape(by_page[number].sheet_title or '')}</figcaption></figure>"
        for number in sorted(sheets)
    )
    counts: dict[str, int] = {}
    for node in gold.nodes:
        counts[type(node).__name__] = counts.get(type(node).__name__, 0) + 1
    count_rows = [
        [f'<a href="core.html#{name}"><code>{name}</code></a>', count]
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    provider = get_provider("recorded", recorded=example / "recorded")
    result = extract_pdf(example / "drawings.pdf", provider, base_iri=gold.base_iri)
    same = result.extraction.normalised() == gold.normalised()
    return f"""
<p>An invented equipment platform, drawn as a four-sheet vector PDF by
<code>examples/generate.py</code>: general notes, a framing plan with third-party markup,
column and base plate schedules, and two connection details. Every sheet says SYNTHETIC EXAMPLE
in its title block. Downloads: <a href="drawings.pdf">drawings.pdf</a>,
<a href="gold.json">gold.json</a> (typed objects), <a href="gold.ttl">gold.ttl</a> (RDF),
<a href="broken.json">broken.json</a> (with deliberate mistakes).</p>
{figures}
<h2>What was read from it</h2>
<p>The gold extraction holds {len(gold.nodes)} objects. Every fact except the set itself and the
load zone cites an <code>Evidence</code> object: sheet, zone on the sheet, confidence.</p>
{_table(["Class", "Objects"], count_rows)}
<h2>The extraction pipeline, replayed</h2>
<p>The pipeline renders each page, asks a model provider for the objects on it, decodes the
answer into typed objects, merges the sheets and validates the result. On this site it ran with
the <em>recorded</em> provider, which replays stored answers.</p>
<p class="note">The stored answers are fixture data written from the gold extraction, not the
output of a language model. They show that the pipeline works end to end; they say nothing
about how accurately a model reads these sheets. No model was called to build this site.</p>
{
        _table(
            ["", ""],
            [
                ["Provider", escape(result.provider)],
                ["Pages read", len(result.pages)],
                ["Objects after the merge", len(result.extraction.nodes)],
                [
                    "Problems reported (dropped fields, conflicts, dangling links)",
                    len(result.problems),
                ],
                ["Equal to the gold extraction", "yes" if same else "NO"],
                ["Validation", escape(result.report.to_text().splitlines()[0])],
            ],
        )
    }
"""


def _findings(report: ValidationReport) -> str:
    rows = [
        [
            f'<span class="tag {f.severity.value}">{f.severity.value}</span>',
            _text(f.focus_node),
            _text((f.path or "").rsplit("#", 1)[-1]),
            escape(f.message),
        ]
        for f in report.findings
    ]
    verdict = "conforms" if report.conforms else "does not conform"
    css = "ok" if report.conforms else "bad"
    summary = (
        f'<p><strong class="{css}">{verdict}</strong>: {len(report.violations)} violation(s), '
        f"{len(report.warnings)} warning(s).</p>"
    )
    if not rows:
        return summary
    return summary + _table(["Severity", "Object", "Property", "Message"], rows)


def _validation(good: ValidationReport, bad: ValidationReport) -> str:
    return f"""
<p>The ontology says what things are; the SHACL shapes say what a usable extraction must
contain. A violation means the fact cannot be used as it stands. A warning asks a person to
look and does not fail the data.</p>
<h2>The gold extraction</h2>
<p><code>steel-ontology validate examples/kestrel-platform/gold.json</code></p>
{_findings(good)}
<h2>The broken variant</h2>
<p>A copy of the gold data with mistakes an extractor really makes: two digits of a schedule
total swapped, a force without its factored tag, a stamp without its origin, a sheet without
its kind, a percentage read as 500, evidence without a confidence.</p>
<p><code>steel-ontology validate examples/kestrel-platform/broken.json</code> (exit code 1)</p>
{_findings(bad)}
<p class="muted">The schedule warning is arithmetic: the printed total no longer equals the
sum of the rows. No outside data is needed to catch it.</p>
"""


def _inferred(gold: Extraction, ref: reference.Reference) -> str:
    result = infer(to_graph(gold))
    interesting = set(defined_classes())
    rows = []
    for iri in sorted(result.inferred_types):
        found = [name for name in result.inferred_types[iri] if name in interesting]
        if found:
            links = ", ".join(f'<a href="core.html#{n}"><code>{n}</code></a>' for n in found)
            rows.append([_text(iri), links])
    used = {name for names in result.inferred_types.values() for name in names} & interesting
    definitions = [
        [f"<code>{d.name}</code>", escape(d.definition), escape(d.comment)]
        for d in ref.defined
        if d.name in used
    ]
    return f"""
<p>Nobody writes "this sheet is marked up" into the data. The ontology defines that class
(a sheet with an annotation that a third party drew) and a reasoner works out the members.
This page was computed with the pure-Python OWL RL engine (<code>steel-ontology reason</code>);
HermiT can be used instead when Java is present.</p>
<p>Consistent: <strong class="{"ok" if result.consistent else "bad"}">
{"yes" if result.consistent else "no"}</strong>. Objects with an inferred defined class:
{len(rows)}.</p>
{_table(["Object", "Inferred classes"], rows)}
<h2>The definitions that fired</h2>
{_table(["Class", "Definition", "Why it exists"], definitions)}
"""


def example_run(
    graph, query: Query
) -> tuple[dict[str, str], list[dict[str, object]], tuple[str, ...]]:
    """Run a query so that the example shows rows when it can.

    A parameter's default often has no match in a small example (no blast loads on a
    platform), so the first vocabulary member that returns rows is used instead.
    """
    result = run_query(graph, query.name)
    if (result.rows and any(any(row.values()) for row in result.rows)) or not query.params:
        return dict(query.params), result.rows, result.columns
    (variable, default), *_ = query.params.items()
    for member in param_vocabulary(default):
        attempt = run_query(graph, query.name, **{variable: member})
        if any(any(row.values()) for row in attempt.rows):
            return {variable: member}, attempt.rows, attempt.columns
    return dict(query.params), result.rows, result.columns


def _queries(graph) -> str:
    parts = [
        "<p>Each competency question is one vetted SPARQL file in "
        "<code>src/steel_ontology/queries/</code>. A parameter can only be bound to a term of "
        "the ontology. Results below are from the example set; a question about something a "
        "small platform does not have (piles, blast loads) correctly returns nothing.</p>"
    ]
    for query in list_queries():
        params, rows, columns = example_run(graph, query)
        shown = "".join(f" <code>{escape(k)}={escape(v)}</code>" for k, v in params.items())
        parts.append(f'<h2 id="{query.name}">{query.id} {escape(query.title)}</h2>')
        parts.append(f"<p>{escape(query.question)}</p>")
        parts.append(f"<p class='muted'><code>{query.name}</code>{shown}: {len(rows)} row(s)</p>")
        if rows:
            parts.append(_table(columns, [[_text(row[c]) for c in columns] for row in rows]))
        sparql = "\n".join(
            line for line in query.text.splitlines() if not line.startswith("#")
        ).strip()
        parts.append(f"<details><summary>SPARQL</summary><pre>{escape(sparql)}</pre></details>")
    return "\n".join(parts)


def _questions(graph, example: Path, sheets: dict[int, bytes], images: Path) -> str:
    parts = [
        "<p>A question is routed to one of the <a href='queries.html'>vetted queries</a> by "
        "keyword rules. No model writes SPARQL or text: the answer is the query's rows, and "
        "each row cites where it was read. The boxes on the sheets are those citations.</p>"
    ]
    for index, question in enumerate(QUESTIONS, start=1):
        parts.append(_answer_block(ask(graph, question), index, sheets, images))
    recorded = get_provider("recorded", recorded=example / "recorded")
    fallback = ask(graph, FALLBACK_QUESTION, provider=recorded)
    parts.append(
        "<h2>When no rule matches</h2><p>An optional model fallback may choose among the same "
        "queries and nothing else. Here the example's recording stands in for the model "
        "(a hand-written stored answer, not a model's output), to show the path offline.</p>"
    )
    parts.append(_answer_block(fallback, len(QUESTIONS) + 1, sheets, images))
    return "\n".join(parts)


def _answer_block(answer: Answer, index: int, sheets: dict[int, bytes], images: Path) -> str:
    parts = [f"<h3>{escape(answer.question)}</h3>"]
    if answer.query is None:
        parts.append(
            '<p><span class="tag Warning">no query</span> I could not route this question to a '
            "vetted query, so nothing is answered. The router does not guess.</p>"
        )
        return "".join(parts)
    params = "".join(f" <code>{escape(k)}={escape(v)}</code>" for k, v in answer.params.items())
    parts.append(
        f'<p class="muted">Routed by {answer.route} to <a href="queries.html#{answer.query.name}">'
        f"{answer.query.id} {answer.query.name}</a>{params}. "
        + " ".join(escape(note) + "." for note in answer.notes)
        + "</p>"
    )
    columns = [
        c for c in answer.columns if any(row.values.get(c) not in (None, "") for row in answer.rows)
    ]
    rows = [
        [
            *(_text(row.values[c]) for c in columns),
            "<br>".join(escape(c.to_text()) for c in row.citations),
        ]
        for row in answer.rows
    ]
    parts.append(_table([*columns, "evidence"], rows))
    boxes: dict[int, list[str]] = {}
    for row in answer.rows:
        for citation in row.citations:
            if citation.page and citation.zone:
                boxes.setdefault(citation.page, []).append(citation.zone)
    for page, zones in sorted(boxes.items()):
        name = f"question-{index}-page-{page}.png"
        (images / name).write_bytes(outline_zones(sheets[page], zones))
        parts.append(
            f'<figure><img src="img/{name}" alt="Page {page} with the cited zones outlined">'
            f"<figcaption>Page {page}: the zones this answer cites.</figcaption></figure>"
        )
    return "".join(parts)


def outline_zones(png: bytes, zones: Iterable[str]) -> bytes:
    """Draw each ``"x0,y0,x1,y1"`` zone (fractions of the page) on a copy of a page image."""
    image = Image.open(io.BytesIO(png)).convert("RGB")
    image.thumbnail((EVIDENCE_EDGE, EVIDENCE_EDGE))
    draw = ImageDraw.Draw(image)
    for zone in sorted(set(zones)):
        x0, y0, x1, y1 = (float(part) for part in zone.split(","))
        box = (
            x0 * image.width - 5,
            y0 * image.height - 5,
            x1 * image.width + 5,
            y1 * image.height + 5,
        )
        draw.rectangle(box, outline=EVIDENCE_COLOUR, width=3)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
