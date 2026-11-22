"""SHACL validation: the good sample conforms, each mistake in the bad sample is caught."""

from __future__ import annotations

import pytest
from rdflib import Graph

from conftest import SAMPLE_NS, data_graph
from steel_ontology.validate import Severity, ValidationReport, validate
from steel_ontology.vocabulary import STEEL, STEEL_SH

TOTAL_MESSAGE = "Printed schedule total differs from the sum of its rows"
ROW_MESSAGE = "Row total differs from the sum of its components"

# (focus node, property path or None, severity, fragment of the message)
EXPECTED_IN_BAD = [
    ("s1", "sheetKind", Severity.VIOLATION, "no sheet kind"),
    ("s1", "pageIndex", Severity.VIOLATION, "exactly one page index"),
    ("s1", "sheetNumber", Severity.WARNING, "no sheet number"),
    ("a1", "annotationOrigin", Severity.VIOLATION, "engineer or a third party"),
    ("f1", "isFactored", Severity.VIOLATION, "factored or unfactored"),
    ("f1", "evidencedBy", Severity.WARNING, "needs evidence"),
    ("a3", None, Severity.WARNING, "ticked outcome (reviewOutcome)"),
    ("dl1", "listsSheet", Severity.VIOLATION, "name the sheet it lists"),
    ("m2", "assemblyWeightTonnes", Severity.VIOLATION, "one positive number"),
    ("p2", "requiredQuantity", Severity.VIOLATION, "at least 1"),
    ("z2", "zoneKind", Severity.VIOLATION, "what kind of zone"),
    ("dr2", "defaultRuleText", Severity.VIOLATION, "keep its text"),
    ("f8", "forceUnit", Severity.WARNING, "one printed force unit"),
    ("s8", None, Severity.VIOLATION, "pageIndex is larger than sheetTotal"),
    ("s8", None, Severity.WARNING, "AS BUILT"),
    ("rq2", "requirementTopic", Severity.VIOLATION, "must have a topic"),
    ("c9", "cellValueKind", Severity.VIOLATION, "what kind of value"),
    ("sr9", "rowKeyText", Severity.VIOLATION, "keep its key"),
    ("lug9", "capacityTonnes", Severity.VIOLATION, "must be positive"),
    ("rm9", None, Severity.WARNING, "how it must be installed"),
    ("sc9", "scopeItemText", Severity.VIOLATION, "must carry its text"),
    ("s12", None, Severity.WARNING, "watermark"),
    ("std9", "standardRevisionText", Severity.WARNING, "revision as printed"),
    ("seq9", "sequenceStepText", Severity.WARNING, "at least two steps"),
    ("dr9", "defaultPercent", Severity.VIOLATION, "above 0 and at most 100"),
    ("sch9", None, Severity.WARNING, TOTAL_MESSAGE),
    ("r93", None, Severity.WARNING, ROW_MESSAGE),
    ("rq9", "noticeHours", Severity.VIOLATION, "must be positive"),
]


@pytest.fixture(scope="module")
def good_report(sample_good: Graph) -> ValidationReport:
    return validate(sample_good)


@pytest.fixture(scope="module")
def bad_report(sample_bad: Graph) -> ValidationReport:
    return validate(sample_bad)


def test_good_sample_conforms_with_warnings_only(good_report: ValidationReport) -> None:
    assert good_report.conforms
    assert good_report.violations == ()
    assert {
        (f.focus_node.removeprefix(SAMPLE_NS), f.path and f.path.split("#")[1])
        for f in good_report.warnings
    } == {
        ("dr1", "defaultRuleKind"),
        ("f1", None),  # a force value without its unit
        ("rev1", "issuePurpose"),
        ("rev3", "issuePurpose"),
        ("rq4", None),  # a clause that prints a number keeps no value
        ("s10", "sheetNumber"),
        ("s3", "sheetNumber"),
        ("s9", "sheetNumber"),
    }


def test_arithmetic_checks_stay_quiet_on_correct_tables(good_report: ValidationReport) -> None:
    text = good_report.to_text()
    assert TOTAL_MESSAGE not in text
    assert ROW_MESSAGE not in text


def test_bad_sample_does_not_conform(bad_report: ValidationReport) -> None:
    assert not bad_report.conforms
    assert bad_report.to_text().startswith("does not conform")


@pytest.mark.parametrize(("node", "path", "severity", "fragment"), EXPECTED_IN_BAD)
def test_each_mistake_is_reported(
    bad_report: ValidationReport, node: str, path: str | None, severity: Severity, fragment: str
) -> None:
    matches = [
        f
        for f in bad_report.findings
        if f.focus_node == SAMPLE_NS + node
        and f.path == (str(STEEL[path]) if path else None)
        and f.severity is severity
        and fragment in f.message
    ]
    assert len(matches) == 1, bad_report.to_text()


def test_findings_name_their_shape_and_sort_violations_first(bad_report: ValidationReport) -> None:
    severities = [f.severity for f in bad_report.findings]
    assert severities == sorted(severities, key=[Severity.VIOLATION, Severity.WARNING].index)
    total = next(f for f in bad_report.findings if TOTAL_MESSAGE in f.message)
    assert total.shape == str(STEEL_SH.ScheduleTotalShape)
    origin = next(f for f in bad_report.findings if f.path == str(STEEL.annotationOrigin))
    assert origin.shape == str(STEEL_SH.AnnotationShape)
    assert origin.to_text().startswith("VIOLATION a1 . annotationOrigin: ")


def _schedule(total: str, *rows: str) -> Graph:
    names = [f"ex:r{i}" for i in range(len(rows))]
    turtle = f"ex:s a steel:Schedule ; steel:declaredTotal {total} ; "
    turtle += f"steel:hasRow {' , '.join(names)} .\n"
    turtle += "\n".join(
        f"{n} a steel:ScheduleRow ; steel:rowValue {v} ." for n, v in zip(names, rows, strict=True)
    )
    return data_graph(turtle)


@pytest.mark.parametrize(
    ("total", "rows", "warns"),
    [
        ("1249.6", ("772.8", "436.8", "40.0"), False),  # exact
        ("1250.0", ("772.8", "436.8", "40.0"), False),  # rounded total, inside 0.5 percent
        ("1294.6", ("772.8", "436.8", "40.0"), True),  # two digits swapped
        ("1209.6", ("772.8", "436.8", "40.0"), True),  # a row left out of the printed total
    ],
)
def test_schedule_total_tolerance(total: str, rows: tuple[str, ...], warns: bool) -> None:
    report = validate(_schedule(total, *rows))
    assert any(TOTAL_MESSAGE in f.message for f in report.warnings) is warns
    assert report.conforms  # an arithmetic mismatch asks for a second look, it does not reject


@pytest.mark.parametrize(("total", "warns"), [("178.0", False), ("178.4", False), ("120.0", True)])
def test_row_total_against_components(total: str, warns: bool) -> None:
    graph = data_graph(
        f"ex:r a steel:ScheduleRow ; steel:componentValue 96.0 , 82.0 ; steel:rowTotal {total} ."
    )
    report = validate(graph)
    assert any(ROW_MESSAGE in f.message for f in report.warnings) is warns


def test_shapes_apply_to_subclasses() -> None:
    """A construction sequence is an annotation, so the annotation shape covers it."""
    graph = data_graph(
        'ex:q a steel:ConstructionSequence ; steel:sequenceStepText "1. Shore" , "2. Cut" .'
    )
    report = validate(graph)
    assert [f.path for f in report.violations] == [str(STEEL.annotationOrigin)]


def test_report_as_dicts(bad_report: ValidationReport) -> None:
    first = bad_report.to_dicts()[0]
    assert set(first) == {"severity", "focus_node", "path", "value", "message", "shape"}
    assert first["severity"] == "Violation"


# ---- closed vocabularies in RDF input -------------------------------------------------------


def test_a_made_up_vocabulary_member_fails_validation() -> None:
    """Typed as a member of the class but not in its list: sh:class would let it through."""
    graph = data_graph(
        "ex:MadeUpKind a steel:SheetKind .\n"
        'ex:s a steel:Sheet ; steel:sheetNumber "S1" ; steel:pageIndex 1 ; '
        "steel:sheetKind ex:MadeUpKind ."
    )
    report = validate(graph)
    (finding,) = report.violations
    assert finding.path == str(STEEL.sheetKind)
    assert "closed vocabulary SheetKind" in finding.message
    assert finding.shape == str(STEEL_SH.SheetKindValuesShape)


@pytest.mark.parametrize(
    ("turtle", "path"),
    [
        (
            "ex:a a steel:Annotation ; steel:annotationOrigin steel:EngineerOrigin ; "
            "steel:markupKind steel:Beam .",
            "markupKind",
        ),
        ("ex:r a steel:Revision ; steel:issuePurpose ex:ForFun .", "issuePurpose"),
        ("ex:e a steel:Beam ; steel:responsibility steel:ByNobody .", "responsibility"),
    ],
)
def test_vocabulary_values_are_checked_on_every_vocabulary_property(turtle: str, path: str) -> None:
    report = validate(data_graph(turtle))
    assert any(
        f.path == str(STEEL[path]) and "closed vocabulary" in f.message for f in report.violations
    )


def test_listed_members_pass_the_vocabulary_shapes(sample_good: Graph) -> None:
    assert not [f for f in validate(sample_good).findings if "closed vocabulary" in f.message]


# ---- readable messages ----------------------------------------------------------------------


@pytest.mark.parametrize("report_name", ["bad_report"])
def test_no_finding_is_raw_shacl_text(request: pytest.FixtureRequest, report_name: str) -> None:
    from conftest import EXAMPLE
    from steel_ontology.graph import load_graph

    reports = [request.getfixturevalue(report_name), validate(load_graph(EXAMPLE / "broken.json"))]
    for report in reports:
        for finding in report.findings:
            assert "Less than" not in finding.message and "<http" not in finding.message
            assert "not >" not in finding.message and "Value " not in finding.message


def test_clause_value_is_asked_for_only_when_the_clause_prints_a_number() -> None:
    graph = data_graph(
        "ex:c1 a steel:RequirementClause ; steel:requirementTopic steel:WeldingReq ; "
        'steel:clauseText "DO NOT FIELD CUT OR BURN HOLES IN BASE PLATES." .\n'
        "ex:c2 a steel:RequirementClause ; steel:requirementTopic steel:WeldingReq ; "
        'steel:clauseText "MINIMUM FILLET WELD 6 MM." .\n'
        "ex:c3 a steel:RequirementClause ; steel:requirementTopic steel:InspectionReq ; "
        'steel:clauseText "100% UT OF SPLICES" ; steel:clauseValue "100%" .'
    )
    warned = {f.focus_node.rsplit("#", 1)[1] for f in validate(graph).warnings}
    assert warned == {"c2"}


def test_force_and_moment_values_need_their_printed_units() -> None:
    graph = data_graph(
        'ex:f a steel:ForceRecord ; steel:isFactored true ; steel:loadCase "Cf" ; '
        "steel:loadType steel:DeadLoad ; steel:evidencedBy ex:e ; "
        'steel:axialValue 117.0 ; steel:forceUnit "kip" ; steel:momentMajorValue 40.0 .\n'
        "ex:e a steel:Evidence ; steel:onSheet ex:s ; steel:confidence steel:Verified ."
    )
    messages = [f.message for f in validate(graph).warnings]
    assert messages == ["A moment or torsion value needs its printed unit in momentUnit."]
