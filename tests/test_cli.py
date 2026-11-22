"""The command line: exit codes and output of each subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import Graph

from conftest import DATA, EXAMPLE
from steel_ontology.cli import main
from steel_ontology.vocabulary import STEEL, VERSION


def test_validate_passes_on_gold(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(EXAMPLE / "gold.ttl")]) == 0
    assert capsys.readouterr().out.startswith("conforms: 0 violation(s), 0 warning(s)")


def test_validate_fails_on_broken_and_reports_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(EXAMPLE / "broken.json"), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["conforms"] is False
    assert {f["severity"] for f in report["findings"]} == {"Violation", "Warning"}


def test_reason_prints_inferred_classes_and_writes_a_graph(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "inferred.ttl"
    assert main(["reason", str(DATA / "defined_classes.ttl"), "--output", str(output)]) == 0
    assert "VoidedView_yes: VoidedView" in capsys.readouterr().out
    inferred = Graph().parse(output)
    assert len(list(inferred.subjects(predicate=None, object=STEEL.VoidedView))) == 1


def test_reason_exits_1_on_inconsistent_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clash = tmp_path / "clash.ttl"
    clash.write_text(
        f"@prefix steel: <{STEEL}> . <https://example.org/x> a steel:Beam , steel:Column ."
    )
    assert main(["reason", str(clash)]) == 1
    assert capsys.readouterr().out.startswith("INCONSISTENT Disjoint classes")


def test_query_list_and_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["query", "--list"]) == 0
    listing = capsys.readouterr().out
    assert listing.count("\nCQ") + listing.startswith("CQ") == 24
    assert "requirement-clauses [topic=WeldingReq]" in listing

    gold = str(EXAMPLE / "gold.json")
    assert main(["query", gold, "cq09", "-p", "topic=InspectionReq", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [row["value"] for row in rows] == ["48 hours"]


def test_query_errors_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    gold = str(EXAMPLE / "gold.json")
    assert main(["query", gold, "no-such-query"]) == 2
    assert main(["query", gold, "cq09", "-p", "topic=Nonsense"]) == 2
    assert main(["query"]) == 2
    assert "error:" in capsys.readouterr().err


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert VERSION in capsys.readouterr().out


def test_extract_with_the_recorded_provider(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out, ttl = tmp_path / "out.json", tmp_path / "out.ttl"
    arguments = ["extract", str(EXAMPLE / "drawings.pdf"), "--provider", "recorded"]
    recorded = ["--recorded", str(EXAMPLE / "recorded")]
    options = ["--base-iri", "https://example.org/kestrel-platform/"]
    assert main([*arguments, *recorded, *options, "--output", str(out), "--ttl", str(ttl)]) == 0
    captured = capsys.readouterr()
    assert "recorded (recording:recorded): 4 page(s), 182 object(s), 0 problem(s)" in captured.out
    assert "conforms: 0 violation(s), 0 warning(s)" in captured.out
    assert "page 4 of 4: asking recorded" in captured.err
    assert out.read_text(encoding="utf-8") == (EXAMPLE / "gold.json").read_text(encoding="utf-8")
    assert len(Graph().parse(ttl)) == len(Graph().parse(EXAMPLE / "gold.ttl"))

    # One sheet alone links to objects drawn on other sheets: reported, not hidden.
    assert main([*arguments, *recorded, "--pages", "1"]) == 0
    assert "PROBLEM   dangling link: connection-brace.connects" in capsys.readouterr().out


def test_extract_errors_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    pdf = str(EXAMPLE / "drawings.pdf")
    assert main(["extract", pdf, "--provider", "recorded"]) == 2
    assert main(["extract", pdf, "--provider", "recorded", "--recorded", "nowhere"]) == 2
    recorded = ["--provider", "recorded", "--recorded", str(EXAMPLE / "recorded")]
    assert main(["extract", pdf, *recorded, "--pages", "9"]) == 2
    assert capsys.readouterr().err.count("error:") == 3


def test_ask(capsys: pytest.CaptureFixture[str]) -> None:
    gold = str(EXAMPLE / "gold.json")
    assert main(["ask", gold, "What size is beam B3?"]) == 0
    out = capsys.readouterr().out
    assert "section=W200x27" in out and "evidence: S-101 zone" in out

    assert main(["ask", gold, "Is the sky blue?"]) == 1
    assert "I could not route this question" in capsys.readouterr().out

    question = "Who has to be told before coming to site?"
    recorded = ["--provider", "recorded", "--recorded", str(EXAMPLE / "recorded")]
    assert main(["ask", gold, question, *recorded, "--json"]) == 0
    answer = json.loads(capsys.readouterr().out)
    assert (answer["route"], answer["query"]) == ("model", "requirement-clauses")
    assert answer["rows"][0]["evidence"][0]["sheet_number"] == "S-001"


def test_docs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    markdown, html = tmp_path / "v.md", tmp_path / "v.html"
    assert main(["docs", "--markdown", str(markdown), "--html", str(html)]) == 0
    assert markdown.read_text(encoding="utf-8").startswith(
        f"# Vocabulary reference (version {VERSION})"
    )
    assert '<tr id="Beam">' in html.read_text(encoding="utf-8")
    assert main(["docs"]) == 2
    assert main(["docs", "--site", str(tmp_path / "s"), "--example", str(tmp_path)]) == 2
    capsys.readouterr()


# ---- input errors: one line on stderr, exit 2 (never a traceback, never the code of a verdict)


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("missing.json", None, "No such file"),
        ("notes.md", "# not data", "unknown file type .md"),
        ("bad.json", '{"nodes": [{"id": "x", "type": "Bogus"}]}', "validation error"),
        ("bad.ttl", "this is not turtle", "error:"),
        ("remote.jsonld", '{"@context": "http://127.0.0.1:9/c.jsonld", "@id": "x"}', "remote"),
    ],
)
def test_unreadable_data_exits_2_with_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str, content: str | None, message: str
) -> None:
    path = tmp_path / name
    if content is not None:
        path.write_text(content, encoding="utf-8")
    for command in (["validate"], ["reason"], ["ask"]):
        arguments = [*command, str(path)] + (
            ["What size is beam B3?"] if command == ["ask"] else []
        )
        assert main(arguments) == 2
        err = capsys.readouterr().err
        assert err.startswith("error: ") and message in err and "Traceback" not in err
        assert err.count("\n") == 1


def test_extract_of_a_file_that_is_not_a_pdf_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    recorded = ["--provider", "recorded", "--recorded", str(EXAMPLE / "recorded")]
    assert main(["extract", str(EXAMPLE / "gold.json"), *recorded]) == 2
    assert capsys.readouterr().err.startswith("error: ")


def test_query_parameters_are_checked_against_their_vocabulary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    gold = str(EXAMPLE / "gold.json")
    assert main(["query", gold, "cq09", "-p", "topic"]) == 2
    assert "is not NAME=TERM" in capsys.readouterr().err
    assert main(["query", gold, "cq09", "-p", "topic=Beam"]) == 2  # an ontology term, wrong list
    assert "topic=Beam is not allowed; use one of WeldingReq" in capsys.readouterr().err
    assert main(["query", gold, "cq09", "-p", "colour=WeldingReq"]) == 2
    assert "has no parameter 'colour'" in capsys.readouterr().err


def test_the_provider_can_come_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("STEEL_ONTOLOGY_PROVIDER", "recorded")
    pdf, recorded = str(EXAMPLE / "drawings.pdf"), ["--recorded", str(EXAMPLE / "recorded")]
    assert main(["extract", pdf, *recorded, "--pages", "2"]) == 0
    assert capsys.readouterr().out.startswith("recorded (recording:recorded): 1 page(s)")
    monkeypatch.delenv("STEEL_ONTOLOGY_PROVIDER")
    assert main(["extract", pdf, *recorded]) == 2
    assert "no provider chosen" in capsys.readouterr().err
