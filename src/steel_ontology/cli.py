"""Command line: ``steel-ontology validate | reason | query | extract | ask | docs``.

Each subcommand is one ``_add_*`` function that registers its arguments and a handler, so a new
command is added by writing one more of them and listing it in ``COMMANDS``.
Data files are extraction JSON or RDF (see ``graph.RDF_FORMATS``).

Exit codes, the same for every subcommand:

- 0: done, and the data passed (conforms, is consistent, a query answered the question);
- 1: done, and the data did not pass (a SHACL violation, an inconsistency, no vetted query);
- 2: nothing to judge: bad arguments, an unreadable or invalid file, a provider error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from pypdfium2 import PdfiumError
from rdflib.plugins.parsers.notation3 import BadSyntax

from steel_ontology import reference
from steel_ontology.ask import ask, param_vocabulary
from steel_ontology.extract import PROVIDERS, Provider, ProviderError, extract_pdf, get_provider
from steel_ontology.extract.pages import parse_page_ranges
from steel_ontology.extract.providers import PROVIDER_ENV
from steel_ontology.graph import load_graph, to_graph
from steel_ontology.models import DEFAULT_BASE_IRI
from steel_ontology.queries import UnknownQuery, get_query, list_queries, run_query
from steel_ontology.reason import ReasonerUnavailable, infer
from steel_ontology.validate import validate
from steel_ontology.vocabulary import VERSION

Subparsers = argparse._SubParsersAction  # the object returned by add_subparsers()

EXIT_OK, EXIT_FAILED, EXIT_ERROR = 0, 1, 2

# What a handler may raise for bad input or an unavailable back end: reported in one line with
# exit code 2. ValueError covers pydantic validation, unknown file types and bad parameters.
INPUT_ERRORS = (
    OSError,
    ValueError,
    SyntaxError,
    BadSyntax,
    PdfiumError,
    ProviderError,
    ReasonerUnavailable,
    UnknownQuery,
)


def _add_validate(subparsers: Subparsers) -> None:
    parser = subparsers.add_parser(
        "validate", help="check a data file against the SHACL shapes (exit 1 on a violation)"
    )
    parser.add_argument("file", help="extraction JSON or RDF file")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.set_defaults(handler=_run_validate)


def _run_validate(args: argparse.Namespace) -> int:
    report = validate(load_graph(args.file))
    if args.json:
        print(json.dumps({"conforms": report.conforms, "findings": report.to_dicts()}, indent=2))
    else:
        print(report.to_text())
    return EXIT_OK if report.conforms else EXIT_FAILED


def _add_reason(subparsers: Subparsers) -> None:
    parser = subparsers.add_parser(
        "reason", help="infer class memberships (exit 1 when the data is inconsistent)"
    )
    parser.add_argument("file", help="extraction JSON or RDF file")
    parser.add_argument(
        "--engine",
        choices=["owlrl", "hermit"],
        default="owlrl",
        help="owlrl: pure Python OWL RL (default); hermit: OWL DL, needs Java and owlready2",
    )
    parser.add_argument("--output", help="write the data plus inferred triples to this Turtle file")
    parser.set_defaults(handler=_run_reason)


def _run_reason(args: argparse.Namespace) -> int:
    result = infer(load_graph(args.file), engine=args.engine)
    for problem in result.inconsistencies:
        print(f"INCONSISTENT {problem}")
    for iri in sorted(result.inferred_types):
        print(f"{iri}: {', '.join(result.inferred_types[iri])}")
    if args.output:
        result.graph.serialize(args.output, format="turtle")
    return EXIT_OK if result.consistent else EXIT_FAILED


def _add_query(subparsers: Subparsers) -> None:
    parser = subparsers.add_parser("query", help="run a named competency query")
    parser.add_argument("file", nargs="?", help="extraction JSON or RDF file")
    parser.add_argument("name", nargs="?", help="query name or id (see --list)")
    parser.add_argument("--list", action="store_true", help="list the available queries")
    parser.add_argument(
        "-p",
        "--param",
        action="append",
        default=[],
        metavar="NAME=TERM",
        help="bind a query parameter to an ontology term, e.g. -p topic=BoltingReq",
    )
    parser.add_argument("--json", action="store_true", help="print rows as JSON")
    parser.set_defaults(handler=_run_query)


def _run_query(args: argparse.Namespace) -> int:
    if args.list:
        for query in list_queries():
            params = "".join(f" [{name}={default}]" for name, default in query.params.items())
            print(f"{query.id}  {query.name}{params}\n      {query.question}")
        return EXIT_OK
    if not args.file or not args.name:
        print("error: give a data file and a query name, or use --list", file=sys.stderr)
        return EXIT_ERROR
    try:
        query = get_query(args.name)
    except UnknownQuery:
        print(f"error: no query named {args.name!r} (see --list)", file=sys.stderr)
        return EXIT_ERROR
    params = _query_params(query.name, args.param)
    result = run_query(load_graph(args.file), query.name, **params)
    if args.json:
        print(json.dumps(result.rows, indent=2, default=str))
    else:
        print(f"{query.title}: {len(result.rows)} row(s)")
        for row in result.rows:
            print("  " + "  ".join(f"{column}={row[column]}" for column in result.columns))
    return EXIT_OK


def _query_params(name: str, items: list[str]) -> dict[str, str]:
    """``-p NAME=TERM`` options as a dict; each term must belong to that parameter's vocabulary."""
    query = get_query(name)
    params = {}
    for item in items:
        variable, sep, value = item.partition("=")
        if not sep or not variable or not value:
            raise ValueError(f"parameter {item!r} is not NAME=TERM")
        if variable not in query.params:
            names = ", ".join(query.params) or "none"
            raise ValueError(f"query {query.name} has no parameter {variable!r} (it has: {names})")
        allowed = param_vocabulary(query.params[variable])
        if value not in allowed:
            raise ValueError(f"{variable}={value} is not allowed; use one of {', '.join(allowed)}")
        params[variable] = value
    return params


def _add_provider_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        help="model back end (default: $STEEL_ONTOLOGY_PROVIDER); "
        "'recorded' replays stored answers and needs no key or network",
    )
    parser.add_argument("--model", help="model id (default: the provider's own default)")
    parser.add_argument(
        "--recorded", metavar="DIR", help="folder of stored answers for --provider recorded"
    )
    parser.add_argument(
        "--refusal-fallback",
        action="store_const",
        const=True,
        default=None,
        help="anthropic only: let the API re-run a declined request on its fallback model "
        "(off unless given or STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS=1)",
    )


def _provider(args: argparse.Namespace) -> Provider:
    return get_provider(
        args.provider,
        model=args.model,
        recorded=args.recorded,
        refusal_fallback=args.refusal_fallback,
    )


def _add_extract(subparsers: Subparsers) -> None:
    parser = subparsers.add_parser(
        "extract",
        help="read a drawing PDF into typed objects with a model (exit 1 on a violation)",
    )
    parser.add_argument("pdf", help="drawing set as a PDF")
    _add_provider_options(parser)
    parser.add_argument("--pages", help="pages to read, e.g. 1,3-5 (default: all)")
    parser.add_argument("--base-iri", default=DEFAULT_BASE_IRI, help="namespace of the objects")
    parser.add_argument("--output", metavar="FILE", help="write the extraction as JSON")
    parser.add_argument("--ttl", metavar="FILE", help="write the extraction as Turtle")
    parser.add_argument(
        "--save-responses", metavar="DIR", help="keep each raw answer (replayable later)"
    )
    parser.set_defaults(handler=_run_extract)


def _run_extract(args: argparse.Namespace) -> int:
    provider = _provider(args)
    pages = parse_page_ranges(args.pages) if args.pages else None
    result = extract_pdf(
        args.pdf,
        provider,
        pages=pages,
        base_iri=args.base_iri,
        save_responses=args.save_responses,
        progress=lambda message: print(message, file=sys.stderr),
    )
    extraction = result.extraction.normalised()
    if args.output:
        Path(args.output).write_text(extraction.to_json(), encoding="utf-8")
    if args.ttl:
        to_graph(extraction).serialize(args.ttl, format="turtle")
    print(
        f"{result.provider} ({result.model}): {len(result.pages)} page(s), "
        f"{len(extraction.nodes)} object(s), {len(result.problems)} problem(s)"
    )
    for problem in result.problems:
        print(f"PROBLEM   {problem}")
    print(result.report.to_text())
    return EXIT_OK if result.report.conforms else EXIT_FAILED


def _add_ask(subparsers: Subparsers) -> None:
    parser = subparsers.add_parser(
        "ask", help="answer a plain-language question with one of the named queries"
    )
    parser.add_argument("file", help="extraction JSON or RDF file")
    parser.add_argument("question", help="the question, in quotes")
    _add_provider_options(parser)
    parser.add_argument("--json", action="store_true", help="print the answer as JSON")
    parser.set_defaults(handler=_run_ask)


def _run_ask(args: argparse.Namespace) -> int:
    graph = load_graph(args.file)
    chosen = args.provider or os.environ.get(PROVIDER_ENV)
    provider = _provider(args) if chosen else None
    answer = ask(graph, args.question, provider=provider)
    print(json.dumps(answer.to_dict(), indent=2) if args.json else answer.to_text())
    return EXIT_OK if answer.query is not None else EXIT_FAILED


def _add_docs(subparsers: Subparsers) -> None:
    parser = subparsers.add_parser(
        "docs", help="generate the vocabulary reference, or the whole static site"
    )
    parser.add_argument("--markdown", metavar="FILE", help="write the reference as Markdown")
    parser.add_argument("--html", metavar="FILE", help="write the reference as one HTML page")
    parser.add_argument("--site", metavar="DIR", help="build the static demo site into DIR")
    parser.add_argument(
        "--example",
        default="examples/kestrel-platform",
        help="example folder the site is computed from (default: %(default)s)",
    )
    parser.set_defaults(handler=_run_docs)


def _run_docs(args: argparse.Namespace) -> int:
    if not (args.markdown or args.html or args.site):
        print("error: give --markdown FILE, --html FILE or --site DIR", file=sys.stderr)
        return EXIT_ERROR
    ref = reference.build_reference()
    if args.markdown:
        Path(args.markdown).write_text(reference.to_markdown(ref), encoding="utf-8")
        print(f"wrote {args.markdown}")
    if args.html:
        Path(args.html).write_text(reference.to_html(ref), encoding="utf-8")
        print(f"wrote {args.html}")
    if args.site:
        from steel_ontology.site import build_site

        if not (Path(args.example) / "gold.json").is_file():
            print(f"error: {args.example} is not an example folder", file=sys.stderr)
            return EXIT_ERROR
        pages = build_site(args.site, args.example)
        print(f"wrote {len(pages)} pages to {args.site}")
    return EXIT_OK


COMMANDS: tuple[Callable[[Subparsers], None], ...] = (
    _add_validate,
    _add_reason,
    _add_query,
    _add_extract,
    _add_ask,
    _add_docs,
)


def build_parser() -> argparse.ArgumentParser:
    """The argument parser with every subcommand registered."""
    parser = argparse.ArgumentParser(
        prog="steel-ontology",
        description="Read, validate, reason over and query steel drawing data.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for add in COMMANDS:
        add(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``steel-ontology`` console script (exit codes: see the module text)."""
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except INPUT_ERRORS as error:
        print(f"error: {_first_line(error)}", file=sys.stderr)
        return EXIT_ERROR


def _first_line(error: BaseException) -> str:
    """A one-line description of an input error (pydantic and rdflib errors span many lines)."""
    lines = [line.strip() for line in str(error).splitlines() if line.strip()]
    if isinstance(error, UnknownQuery):
        return f"no query named {error.args[0]!r} (see --list)"
    text = " ".join(lines[:3]) if lines else type(error).__name__
    return text if len(text) <= 300 else text[:297] + "..."


if __name__ == "__main__":
    sys.exit(main())
