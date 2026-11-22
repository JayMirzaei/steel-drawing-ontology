"""The typed objects mirror the ontology: same classes, same properties, same closed lists."""

from __future__ import annotations

import enum
from decimal import Decimal

import pytest
from pydantic import ValidationError
from rdflib import OWL, RDF, RDFS, Graph, URIRef

from steel_ontology import enums, models, vocabulary
from steel_ontology.graph import _is_list
from steel_ontology.models import NODE_CLASSES, Extraction, rdf_fields
from steel_ontology.vocabulary import STEEL

INFERRED_ONLY = {"isSheetOf", "isViewOn", "partOfAssembly", "supportedBy"}


def _python_enums() -> dict[str, type[enum.StrEnum]]:
    return {
        name: obj
        for name, obj in vars(enums).items()
        if isinstance(obj, type) and issubclass(obj, enum.StrEnum) and obj is not enum.StrEnum
    }


def test_enumerations_match_the_ontology() -> None:
    python = {name: tuple(m.value for m in cls) for name, cls in _python_enums().items()}
    assert python == vocabulary.enumerations()


def test_every_extractable_class_has_a_model(ontology: Graph) -> None:
    named = {
        vocabulary.local_name(s)
        for s in ontology.subjects(RDF.type, OWL.Class)
        if isinstance(s, URIRef)
    }
    expected = named - set(vocabulary.enumerations()) - set(vocabulary.defined_classes())
    assert set(NODE_CLASSES) == expected


def test_model_inheritance_mirrors_subclass_axioms(ontology: Graph) -> None:
    for name, cls in NODE_CLASSES.items():
        parents = {
            vocabulary.local_name(o)
            for o in ontology.objects(STEEL[name], RDFS.subClassOf)
            if isinstance(o, URIRef)
        }
        base = cls.__mro__[1].__name__
        assert parents == ({base} if base != "Node" else set()), name


def test_every_field_maps_to_a_property_of_the_right_kind() -> None:
    properties = vocabulary.properties()
    for cls in NODE_CLASSES.values():
        for name, (prop, target) in rdf_fields(cls).items():
            assert prop in properties, f"{cls.__name__}.{name}: unknown property {prop}"
            info = properties[prop]
            annotation = cls.model_fields[name].annotation
            if info["functional"]:
                assert not _is_list(annotation), f"{cls.__name__}.{name} must be single"
            if target is not None:
                assert info["object"], f"{cls.__name__}.{name} links objects"
                assert target in NODE_CLASSES


def test_every_property_is_covered_by_some_model() -> None:
    covered = {prop for cls in NODE_CLASSES.values() for prop, _ in rdf_fields(cls).values()}
    assert set(vocabulary.properties()) - covered == INFERRED_ONLY


def test_fields_sit_on_the_domain_class(ontology: Graph) -> None:
    """A field appears on a model only when the property's domain allows that class."""
    for cls in NODE_CLASSES.values():
        ancestors = {c.__name__ for c in cls.__mro__}
        for prop, _ in rdf_fields(cls).values():
            domain = ontology.value(STEEL[prop], RDFS.domain)
            if domain is None:
                continue
            union = ontology.value(domain, OWL.unionOf)
            allowed = (
                {vocabulary.local_name(d) for d in ontology.items(union)}
                if union is not None
                else {vocabulary.local_name(domain)}
            )
            assert ancestors & allowed, f"{cls.__name__} has {prop} outside its domain"


def test_values_stay_as_printed() -> None:
    row = models.ScheduleRow(id="r1", row_value="1209.60")
    assert row.row_value == Decimal("1209.60")
    assert str(row.row_value) == "1209.60"
    revision = models.Revision(id="rev", revision_date="07/03/21")
    assert revision.revision_date == "07/03/21"


def test_ids_must_be_iri_safe_and_unique() -> None:
    with pytest.raises(ValidationError):
        models.Sheet(id="sheet 1")
    with pytest.raises(ValidationError):
        Extraction(nodes=[models.Sheet(id="s"), models.View(id="s")])


def test_unknown_fields_and_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        models.Sheet(id="s", colour="red")
    with pytest.raises(ValidationError):
        models.Sheet(id="s", sheet_kind="NotAKind")


def test_lookup_helpers() -> None:
    sheet = models.Sheet(id="s1")
    evidence = models.Evidence(id="e1", on_sheet="s1")
    girt = models.Girt(id="g1", evidenced_by=["e1", "missing"])
    extraction = Extraction(nodes=[sheet, evidence, girt])
    assert extraction.get("g1") is girt
    assert extraction.of_type(models.Member) == [girt]
    assert extraction.evidence_for(girt) == [evidence]
    with pytest.raises(KeyError):
        extraction.get("nope")


def test_dangling_references_are_reported() -> None:
    extraction = Extraction(
        nodes=[
            models.Sheet(id="s1", has_view=["v1", "ghost"], has_revision=["v1"]),
            models.View(id="v1"),
        ]
    )
    problems = extraction.dangling_references()
    assert problems == [
        "s1.has_view: no object with id 'ghost'",
        "s1.has_revision: 'v1' is a View, expected Revision",
    ]


def test_json_round_trip_and_discriminator() -> None:
    extraction = Extraction(
        nodes=[
            models.Girt(id="g1", tag="G1", camber_mm=Decimal("12.5")),
            models.Sheet(id="s1", sheet_kind=enums.SheetKind.PLAN_SHEET, page_index=1),
        ]
    )
    text = extraction.to_json()
    assert '"type": "Girt"' in text
    assert '"evidenced_by"' not in text  # empty fields are left out
    again = Extraction.from_json(text)
    assert again == extraction
    assert isinstance(again.nodes[0], models.Girt)


def test_json_schema_carries_the_ontology_comments() -> None:
    schema = models.extraction_json_schema()
    sheet = schema["$defs"]["Sheet"]["properties"]
    assert sheet["is_sealed"]["rdf"] == "isSealed"
    assert sheet["is_sealed"]["description"].startswith("Sheet bears a professional engineer")
    assert sheet["has_view"]["range"] == "View"
    assert schema["properties"]["nodes"]["items"]["discriminator"]["propertyName"] == "type"


def test_docstrings_repeat_the_ontology_comments() -> None:
    described = vocabulary.comments()
    documented = {**NODE_CLASSES, **_python_enums()}
    for name, cls in documented.items():
        if name in described:
            assert " ".join((cls.__doc__ or "").split()) == described[name], name
