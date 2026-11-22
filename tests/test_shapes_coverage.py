"""Every shape fires: one minimal faulty snippet per node shape, and no shape without one.

A shape that no test data ever trips may never fire at all (a typo in ``sh:path`` is silent),
so this file names each shape, gives the smallest data that breaks it, and checks that the
finding comes from that shape.
"""

from __future__ import annotations

import pytest
from rdflib import RDF, SH

from conftest import data_graph
from steel_ontology import vocabulary
from steel_ontology.validate import validate
from steel_ontology.vocabulary import STEEL_SH, load_shapes

# node shape -> Turtle that breaks it (prefixes steel:, ex:, owl: are declared by data_graph)
BREAKS = {
    "SheetShape": "ex:s a steel:Sheet ; steel:pageIndex 0 .",
    "SheetTotalShape": "ex:s a steel:Sheet ; steel:pageIndex 3 ; steel:sheetTotal 2 .",
    "TitleBlockStatusConflictShape": (
        "ex:s a steel:Sheet ; steel:titleBlockStatus steel:AsBuilt ; steel:hasRevision ex:r .\n"
        "ex:r a steel:Revision ; steel:issuePurpose steel:IssuedForConstruction ."
    ),
    "WatermarkConflictShape": (
        'ex:s a steel:Sheet ; steel:statusWatermarkText "FOR INFORMATION ONLY" ; '
        "steel:hasRevision ex:r .\n"
        "ex:r a steel:Revision ; steel:issuePurpose steel:IssuedForConstruction ."
    ),
    "RevisionShape": "ex:r a steel:Revision .",
    "InclusionRowShape": "ex:i a steel:InclusionRow .",
    "StandardDocumentShape": "ex:d a steel:StandardDocument .",
    "ElementRowShape": "ex:r a steel:ElementRow .",
    "DrawingListRowShape": "ex:r a steel:DrawingListRow .",
    "ScheduleCellShape": "ex:c a steel:ScheduleCell .",
    "SelectionRowShape": "ex:r a steel:SelectionRow .",
    "ScheduleTotalShape": (
        "ex:t a steel:Schedule ; steel:declaredTotal 100.0 ; steel:hasRow ex:r .\n"
        "ex:r a steel:ScheduleRow ; steel:rowValue 50.0 ."
    ),
    "RowTotalShape": "ex:r a steel:ScheduleRow ; steel:rowTotal 10.0 ; steel:componentValue 4.0 .",
    "AssemblyShape": "ex:a a steel:Assembly ; steel:assemblyWeightTonnes -1.0 .",
    "QuantityShape": "ex:b a steel:Beam ; steel:requiredQuantity 0 .",
    "PileCriteriaShape": "ex:p a steel:Pile ; steel:designEmbedmentM -2.0 .",
    "LiftingLugShape": "ex:l a steel:LiftingLug ; steel:capacityTonnes 0.0 .",
    "WorkPointShape": "ex:w a steel:WorkPoint .",
    "ReinforcesShape": "ex:b a steel:Beam ; steel:reinforces ex:old . ex:old a steel:Beam .",
    "ScopeItemShape": "ex:i a steel:ScopeItem .",
    "ForceRecordShape": "ex:f a steel:ForceRecord .",
    "ForceUnitShape": 'ex:f a steel:ForceRecord ; steel:forceUnit "tonnes-ish" .',
    "ForceValueUnitShape": "ex:f a steel:ForceRecord ; steel:axialValue 10.0 .",
    "MomentValueUnitShape": "ex:f a steel:ForceRecord ; steel:torsionValue 3.0 .",
    "ZoneShape": "ex:z a steel:Zone .",
    "AreaLoadShape": "ex:l a steel:AreaLoad .",
    "DesignParameterShape": "ex:d a steel:DesignParameter .",
    "RequirementClauseShape": "ex:c a steel:RequirementClause .",
    "ClauseValueShape": 'ex:c a steel:RequirementClause ; steel:clauseText "GROUT 25 MM" .',
    "NoticeHoursShape": "ex:c a steel:RequirementClause ; steel:noticeHours 0 .",
    "DefaultRuleShape": "ex:d a steel:DefaultRule .",
    "DefaultRuleKindShape": "ex:d a steel:DefaultRule ; steel:defaultPercent 120.0 .",
    "AnnotationShape": "ex:a a steel:Annotation .",
    "VendorStampShape": "ex:a a steel:Annotation ; steel:markupKind steel:VendorReviewStamp .",
    "ConstructionSequenceShape": (
        'ex:q a steel:ConstructionSequence ; steel:sequenceStepText "1." .'
    ),
    "EvidenceShape": "ex:e a steel:Evidence .",
}


def _vocabulary_breaks() -> dict[str, str]:
    """One snippet per closed-vocabulary shape: each of its properties gets a made-up value."""
    shapes = load_shapes()
    breaks = {}
    for name in vocabulary.enumerations():
        shape = STEEL_SH[f"{name}ValuesShape"]
        paths = [shapes.value(p, SH.path) for p in shapes.objects(shape, SH.property)]
        breaks[f"{name}ValuesShape"] = "\n".join(
            f"ex:x{i} <{path}> ex:NotInTheList ." for i, path in enumerate(paths)
        )
    return breaks


ALL_BREAKS = {**BREAKS, **_vocabulary_breaks()}


def test_every_node_shape_has_a_breaking_snippet() -> None:
    shapes = load_shapes()
    named = {
        str(s).rsplit("#", 1)[1] for s in shapes.subjects(RDF.type, SH.NodeShape) if "#" in str(s)
    }
    assert named == set(ALL_BREAKS)


@pytest.mark.parametrize(("shape", "turtle"), ALL_BREAKS.items())
def test_the_snippet_trips_its_shape(shape: str, turtle: str) -> None:
    report = validate(data_graph(turtle))
    fired = {f.shape for f in report.findings}
    assert str(STEEL_SH[shape]) in fired, report.to_text()


@pytest.mark.parametrize("name", vocabulary.enumerations())
def test_each_vocabulary_property_is_checked(name: str) -> None:
    shape = STEEL_SH[f"{name}ValuesShape"]
    shapes = load_shapes()
    paths = {str(shapes.value(p, SH.path)) for p in shapes.objects(shape, SH.property)}
    report = validate(data_graph(ALL_BREAKS[f"{name}ValuesShape"]))
    assert {f.path for f in report.findings if f.shape == str(shape)} == paths
