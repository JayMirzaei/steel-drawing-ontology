"""Typed objects for one extracted drawing set: the extraction contract.

Every class here mirrors one class of ``ontology/core.ttl`` and every field mirrors one property
(the property's local name is in the field metadata). An extractor, whether a person, a rule
parser or a language model, fills these objects; ``steel_ontology.graph`` turns them into RDF
and back without loss.

Design rules
- Text is stored as printed. Dates, units and cell text are strings; nothing is parsed
  silently. Numbers are ``Decimal`` so "1209.6" stays "1209.6". A numeric field whose name
  ends in a unit (``elevation_m``) holds the number in that unit; one without (``axial_value``)
  holds the printed number, and its printed unit is in a companion field (``force_unit``).
- Objects point at each other by ``id`` (a flat list, not a tree), because one element appears
  in several views, rows and details.
- Every fact can carry ``evidenced_by``: ids of ``Evidence`` objects that say on which sheet and
  in which zone of the sheet the fact was read, and how sure the reader is.
- A field is a single value when the ontology declares the property functional or when a
  drawing prints one value per object in practice (a sheet number, a clause text). Every other
  field is a list. ``graph.from_graph`` refuses a graph that has two values for a single field.
- Mandatory fields are not enforced here. Completeness is the job of the SHACL shapes
  (``steel_ontology.validate``), so a partial extraction can still be loaded, inspected and
  reported on.
- Inverse properties and reasoner-defined classes are left out: they are inferred, not extracted.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from steel_ontology.enums import (
    AnnotationOrigin,
    AuthorRole,
    CellValueKind,
    ChangeReason,
    DefaultRuleKind,
    Discipline,
    Domain,
    ElementStatus,
    ExposureClass,
    ExtractionConfidence,
    IssuePurpose,
    LoadDirection,
    LoadType,
    MarkupKind,
    RequirementTopic,
    ResponsibilityTag,
    ReviewOutcome,
    ScheduleKind,
    SheetKind,
    SubmissionStage,
    UnitSystem,
    ViewKind,
    WorkKind,
    ZoneKind,
)
from steel_ontology.vocabulary import comments

RDF_KEY = "rdf"
RANGE_KEY = "range"
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def lit(name: str) -> Any:
    """A single literal or enumeration value for the ontology property ``name``."""
    return Field(default=None, json_schema_extra={RDF_KEY: name})


def lits(name: str) -> Any:
    """A list of literal or enumeration values for the ontology property ``name``."""
    return Field(default_factory=list, json_schema_extra={RDF_KEY: name})


def ref(name: str, target: str) -> Any:
    """The id of one object of class ``target``, linked by the ontology property ``name``."""
    return Field(default=None, json_schema_extra={RDF_KEY: name, RANGE_KEY: target})


def refs(name: str, target: str) -> Any:
    """Ids of objects of class ``target``, linked by the ontology property ``name``."""
    return Field(default_factory=list, json_schema_extra={RDF_KEY: name, RANGE_KEY: target})


class Node(BaseModel):
    """Base of every extracted object: an id plus the links any fact may carry."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identifier, unique within one extraction. Becomes the IRI.")
    cites_standard: list[str] = refs("citesStandard", "Standard")
    evidenced_by: list[str] = refs("evidencedBy", "Evidence")

    @field_validator("id")
    @classmethod
    def _id_is_iri_safe(cls, value: str) -> str:
        if not _ID_PATTERN.match(value):
            raise ValueError(f"id {value!r} must use only letters, digits, '.', '_' and '-'")
        return value


class DrawingSet(Node):
    """A bundle of sheets issued together (one PDF or one issue of a project drawing
    package)."""

    type: Literal["DrawingSet"] = "DrawingSet"
    authored_by: list[str] = refs("authoredBy", "Party")
    author_role: list[AuthorRole] = lits("authorRole")
    has_sheet: list[str] = refs("hasSheet", "Sheet")
    in_domain: Domain | None = lit("inDomain")
    owned_by: list[str] = refs("ownedBy", "Party")
    unit_system: UnitSystem | None = lit("unitSystem")
    cites_standard_notes: list[str] = refs("citesStandardNotes", "StandardDocument")
    reproduces_standard: list[str] = refs("reproducesStandard", "StandardDocument")
    datum_note: str | None = lit("datumNote")
    fabricator_job_number: str | None = lit("fabricatorJobNumber")
    issue_scope_text: str | None = lit("issueScopeText")
    numbering_scheme: str | None = lit("numberingScheme")
    review_scope_text: str | None = lit("reviewScopeText")
    revision_code_scheme: str | None = lit("revisionCodeScheme")
    transmittal_number: str | None = lit("transmittalNumber")
    project_number: str | None = lit("projectNumber")
    has_scope_item: list[str] = refs("hasScopeItem", "ScopeItem")
    has_design_parameter: list[str] = refs("hasDesignParameter", "DesignParameter")
    has_default_rule: list[str] = refs("hasDefaultRule", "DefaultRule")
    has_requirement: list[str] = refs("hasRequirement", "RequirementClause")


class Sheet(Node):
    """One drawing sheet (page) with its own sheet number and title block."""

    type: Literal["Sheet"] = "Sheet"
    author_role: list[AuthorRole] = lits("authorRole")
    cites_standard_notes: list[str] = refs("citesStandardNotes", "StandardDocument")
    consultant: list[str] = refs("consultant", "Party")
    enlargement_of: str | None = ref("enlargementOf", "Sheet")
    has_status_stamp: list[IssuePurpose] = lits("hasStatusStamp")
    has_view: list[str] = refs("hasView", "View")
    refers_to_document: list[str] = refs("refersToDocument", "Sheet")
    reproduces_standard: list[str] = refs("reproducesStandard", "StandardDocument")
    sheet_discipline: list[Discipline] = lits("sheetDiscipline")
    sheet_kind: SheetKind | None = lit("sheetKind")
    title_block_status: IssuePurpose | None = lit("titleBlockStatus")
    consultant_sheet_number: str | None = lit("consultantSheetNumber")
    derived_from_raster: bool | None = lit("derivedFromRaster")
    drawing_number_segments_text: str | None = lit("drawingNumberSegmentsText")
    is_sealed: bool | None = lit("isSealed")
    lead_time_text: str | None = lit("leadTimeText")
    page_index: int | None = lit("pageIndex")
    pricing_columns: bool | None = lit("pricingColumns")
    project_number: str | None = lit("projectNumber")
    seal_jurisdiction_text: str | None = lit("sealJurisdictionText")
    seal_scope_text: str | None = lit("sealScopeText")
    sheet_number: str | None = lit("sheetNumber")
    sheet_title: str | None = lit("sheetTitle")
    sheet_total: int | None = lit("sheetTotal")
    status_watermark_text: str | None = lit("statusWatermarkText")
    unit_conflict_text: str | None = lit("unitConflictText")
    has_revision: list[str] = refs("hasRevision", "Revision")
    has_schedule: list[str] = refs("hasSchedule", "Schedule")
    has_scope_item: list[str] = refs("hasScopeItem", "ScopeItem")
    has_design_parameter: list[str] = refs("hasDesignParameter", "DesignParameter")
    has_default_rule: list[str] = refs("hasDefaultRule", "DefaultRule")
    has_requirement: list[str] = refs("hasRequirement", "RequirementClause")
    has_annotation: list[str] = refs("hasAnnotation", "Annotation")
    has_construction_sequence: list[str] = refs("hasConstructionSequence", "ConstructionSequence")


class View(Node):
    """A drawn region on a sheet: plan, elevation, section, detail, 3D view, schedule area,
    notes block."""

    type: Literal["View"] = "View"
    callout_to: list[str] = refs("calloutTo", "View")
    shows_element: list[str] = refs("showsElement", "Element")
    view_kind: ViewKind | None = lit("viewKind")
    callout_target_sheet_text: str | None = lit("calloutTargetSheetText")
    is_guide_only: bool | None = lit("isGuideOnly")
    is_typical: bool | None = lit("isTypical")
    is_voided: bool | None = lit("isVoided")
    scale_text: str | None = lit("scaleText")
    view_code: str | None = lit("viewCode")
    needs_field_confirm: bool | None = lit("needsFieldConfirm")
    has_construction_sequence: list[str] = refs("hasConstructionSequence", "ConstructionSequence")
    is_tbd: bool | None = lit("isTBD")


class Party(Node):
    """A company or professional named on the drawing (consultant, owner, supplier, fabricator,
    architect)."""

    type: Literal["Party"] = "Party"
    party_role_text: str | None = lit("partyRoleText")


class Standard(Node):
    """A code or specification cited (CSA, ASTM, building code, owner standard)."""

    type: Literal["Standard"] = "Standard"
    standard_designation: str | None = lit("standardDesignation")


class StandardDocument(Node):
    """An owner or firm standard reproduced or cited by a set, with its revision (a
    standard-notes sheet reproduced across projects)."""

    type: Literal["StandardDocument"] = "StandardDocument"
    standard_revision_text: str | None = lit("standardRevisionText")
    standard_title_text: str | None = lit("standardTitleText")


class Revision(Node):
    """One entry in a sheet's revision/issue table."""

    type: Literal["Revision"] = "Revision"
    issue_scope_text: str | None = lit("issueScopeText")
    change_reason: ChangeReason | None = lit("changeReason")
    issue_purpose: IssuePurpose | None = lit("issuePurpose")
    issue_scope: list[Discipline] = lits("issueScope")
    submission_stage: SubmissionStage | None = lit("submissionStage")
    revision_code: str | None = lit("revisionCode")
    revision_date: str | None = lit("revisionDate")


class InclusionRow(Node):
    """Which document revision a package revision includes (work package revision matrix)."""

    type: Literal["InclusionRow"] = "InclusionRow"
    includes_sheet: str | None = ref("includesSheet", "Sheet")
    in_package_revision: str | None = ref("inPackageRevision", "Revision")
    included_revision_code: str | None = lit("includedRevisionCode")


class Schedule(Node):
    """A table on a sheet (column, pile, baseplate, member forces, lap splice, plate quantity
    ...)."""

    type: Literal["Schedule"] = "Schedule"
    is_guide_only: bool | None = lit("isGuideOnly")
    has_row: list[str] = refs("hasRow", "ScheduleRow")
    schedule_kind: ScheduleKind | None = lit("scheduleKind")
    assembly_count: int | None = lit("assemblyCount")
    declared_total: Decimal | None = lit("declaredTotal")
    hold_list_is_explicitly_empty: bool | None = lit("holdListIsExplicitlyEmpty")
    is_information_only: bool | None = lit("isInformationOnly")


class ScheduleRow(Node):
    """One row of a schedule."""

    type: Literal["ScheduleRow"] = "ScheduleRow"
    has_cell: list[str] = refs("hasCell", "ScheduleCell")
    row_refers_to_sheet: list[str] = refs("rowRefersToSheet", "Sheet")
    is_tender_only: bool | None = lit("isTenderOnly")
    component_value: list[Decimal] = lits("componentValue")
    is_voided_row: bool | None = lit("isVoidedRow")
    library_drawing_number: str | None = lit("libraryDrawingNumber")
    library_drawing_rev: str | None = lit("libraryDrawingRev")
    row_total: Decimal | None = lit("rowTotal")
    row_value: Decimal | None = lit("rowValue")
    revised_in_this_issue: bool | None = lit("revisedInThisIssue")


class ElementRow(ScheduleRow):
    """A row that tabulates one tagged element (column, pile, joist ...)."""

    type: Literal["ElementRow"] = "ElementRow"
    describes_element: str | None = ref("describesElement", "Element")


class DrawingListRow(ScheduleRow):
    """A row of a drawing list / master drawing list: names a sheet and its status per issue."""

    type: Literal["DrawingListRow"] = "DrawingListRow"
    lists_sheet: str | None = ref("listsSheet", "Sheet")
    legacy_sheet_note: str | None = lit("legacySheetNote")
    stage_revision_text: list[str] = lits("stageRevisionText")


class ScheduleCell(Node):
    type: Literal["ScheduleCell"] = "ScheduleCell"
    cell_value_kind: CellValueKind | None = lit("cellValueKind")
    cell_text: str | None = lit("cellText")
    cell_unit_text: str | None = lit("cellUnitText")
    column_header_text: str | None = lit("columnHeaderText")
    is_tender_only: bool | None = lit("isTenderOnly")


class SelectionTable(Node):
    """A reusable lookup table printed on a standard drawing: key range -> values."""

    type: Literal["SelectionTable"] = "SelectionTable"
    has_selection_row: list[str] = refs("hasSelectionRow", "SelectionRow")
    selection_table_of: str | None = ref("selectionTableOf", "Sheet")
    table_title: str | None = lit("tableTitle")


class SelectionRow(Node):
    type: Literal["SelectionRow"] = "SelectionRow"
    row_key_text: str | None = lit("rowKeyText")
    row_values_text: str | None = lit("rowValuesText")


class Element(Node):
    """A physical item shown or specified on the drawing."""

    type: Literal["Element"] = "Element"
    is_guide_only: bool | None = lit("isGuideOnly")
    element_status: ElementStatus | None = lit("elementStatus")
    exposure_class: ExposureClass | None = lit("exposureClass")
    has_type: str | None = ref("hasType", "ElementType")
    reinforces: list[str] = refs("reinforces", "Element")
    supports: list[str] = refs("supports", "Element")
    baseplate_type_text: str | None = lit("baseplateTypeText")
    cut_length_mm: Decimal | None = lit("cutLengthMm")
    elevation_kind: str | None = lit("elevationKind")
    existing_marker_text: str | None = lit("existingMarkerText")
    heat_number: list[str] = lits("heatNumber")
    installation_constraint_text: str | None = lit("installationConstraintText")
    is_abandoned: bool | None = lit("isAbandoned")
    is_design_open: bool | None = lit("isDesignOpen")
    is_shipped_loose: bool | None = lit("isShippedLoose")
    is_stick_built: bool | None = lit("isStickBuilt")
    is_temporary: bool | None = lit("isTemporary")
    mark_class_text: str | None = lit("markClassText")
    needs_field_confirm: bool | None = lit("needsFieldConfirm")
    qty_per_assembly: int | None = lit("qtyPerAssembly")
    required_quantity: int | None = lit("requiredQuantity")
    revised_in_this_issue: bool | None = lit("revisedInThisIssue")
    tag: str | None = lit("tag")
    grid_location_text: list[str] = lits("gridLocationText")
    elevation_m: Decimal | None = lit("elevationM")
    responsibility: list[ResponsibilityTag] = lits("responsibility")
    responsible_package: str | None = ref("responsiblePackage", "DrawingSet")
    work_kind: WorkKind | None = lit("workKind")
    requires_sealed_design: bool | None = lit("requiresSealedDesign")
    has_force_record: list[str] = refs("hasForceRecord", "ForceRecord")
    in_zone: str | None = ref("inZone", "Zone")
    is_tbd: bool | None = lit("isTBD")


class ElementType(Node):
    """A reusable type printed on drawings (base plate BP3, support type 2A, pile type A): the
    type/instance pattern. Types are placed many times with different locations."""

    type: Literal["ElementType"] = "ElementType"
    tag_prefix: str | None = lit("tagPrefix")
    type_tag: str | None = lit("typeTag")


class Member(Element):
    """A linear structural member (beam, column, brace, joist, stringer, post)."""

    type: Literal["Member"] = "Member"
    handedness_text: str | None = lit("handednessText")
    material_text: str | None = lit("materialText")
    section_text: str | None = lit("sectionText")
    top_of_steel_offset_mm: Decimal | None = lit("topOfSteelOffsetMm")


class Beam(Member):
    type: Literal["Beam"] = "Beam"
    camber_mm: Decimal | None = lit("camberMm")
    is_transport_beam: bool | None = lit("isTransportBeam")
    stud_count: int | None = lit("studCount")


class Girt(Beam):
    """Horizontal wall-framing member (cold-formed or HSS girt); is-a test: a girt is a beam
    that carries wall cladding load."""

    type: Literal["Girt"] = "Girt"


class Column(Member):
    type: Literal["Column"] = "Column"


class Brace(Member):
    type: Literal["Brace"] = "Brace"


class Joist(Member):
    type: Literal["Joist"] = "Joist"
    camber_mm: Decimal | None = lit("camberMm")
    stud_count: int | None = lit("studCount")
    camber_percent_dead_load: Decimal | None = lit("camberPercentDeadLoad")
    deflection_limit_text: str | None = lit("deflectionLimitText")
    depth_mm: Decimal | None = lit("depthMm")
    extra_point_load_kn: Decimal | None = lit("extraPointLoadKN")
    product_line_text: str | None = lit("productLineText")


class JoistGirder(Joist):
    type: Literal["JoistGirder"] = "JoistGirder"


class Stringer(Member):
    type: Literal["Stringer"] = "Stringer"


class Post(Member):
    type: Literal["Post"] = "Post"


class Connection(Element):
    """A joint between members or between a member and a support (shear, moment, brace, base
    plate, splice)."""

    type: Literal["Connection"] = "Connection"
    connects: list[str] = refs("connects", "Element")
    weld_pattern: str | None = lit("weldPattern")


class BasePlateConnection(Connection):
    type: Literal["BasePlateConnection"] = "BasePlateConnection"


class ShearConnection(Connection):
    type: Literal["ShearConnection"] = "ShearConnection"


class MomentConnection(Connection):
    type: Literal["MomentConnection"] = "MomentConnection"


class BraceConnection(Connection):
    type: Literal["BraceConnection"] = "BraceConnection"


class Support(Element):
    """Foundation or existing structure that carries the steel (pile, footing, pedestal,
    existing wall or column)."""

    type: Literal["Support"] = "Support"
    easting: Decimal | None = lit("easting")
    easting_text: str | None = lit("eastingText")
    northing: Decimal | None = lit("northing")
    northing_text: str | None = lit("northingText")


class Pile(Support):
    type: Literal["Pile"] = "Pile"
    design_embedment_m: Decimal | None = lit("designEmbedmentM")
    drive_energy_j: Decimal | None = lit("driveEnergyJ")
    embedment_rule_text: str | None = lit("embedmentRuleText")
    max_lateral_displacement_mm: Decimal | None = lit("maxLateralDisplacementMm")
    min_torque_ft_lbs: Decimal | None = lit("minTorqueFtLbs")


class Footing(Support):
    type: Literal["Footing"] = "Footing"


class Bearing(Support):
    """Truss/beam bearing (fixed, sliding, elastomeric)."""

    type: Literal["Bearing"] = "Bearing"


class Plate(Element):
    type: Literal["Plate"] = "Plate"
    catalogue_text: str | None = lit("catalogueText")
    section_text: str | None = lit("sectionText")


class LiftingLug(Plate):
    type: Literal["LiftingLug"] = "LiftingLug"
    capacity_tonnes: Decimal | None = lit("capacityTonnes")


class KeeperPlate(Plate):
    """Plate welded to a cantilever pipe support to keep the pipe in place; is-a test: a keeper
    plate is a plate."""

    type: Literal["KeeperPlate"] = "KeeperPlate"


class Fastener(Element):
    type: Literal["Fastener"] = "Fastener"
    catalogue_text: str | None = lit("catalogueText")


class Assembly(Element):
    """A shippable/liftable unit made of members, plates, connections and smaller assemblies:
    module, skid, frame, support tower."""

    type: Literal["Assembly"] = "Assembly"
    has_part: list[str] = refs("hasPart", "Element")
    assembly_weight_tonnes: Decimal | None = lit("assemblyWeightTonnes")
    cog_x: Decimal | None = lit("cogX")
    cog_y: Decimal | None = lit("cogY")
    cog_z: Decimal | None = lit("cogZ")
    weight_text: str | None = lit("weightText")
    easting: Decimal | None = lit("easting")
    easting_text: str | None = lit("eastingText")
    northing: Decimal | None = lit("northing")
    northing_text: str | None = lit("northingText")


class Truss(Assembly):
    type: Literal["Truss"] = "Truss"
    camber_mm: Decimal | None = lit("camberMm")


class Accessory(Element):
    """Non-primary steel: grating, handrail, guardrail, stair, ladder, deck, kick plate."""

    type: Literal["Accessory"] = "Accessory"
    catalogue_text: str | None = lit("catalogueText")


class Grating(Accessory):
    type: Literal["Grating"] = "Grating"


class Handrail(Accessory):
    type: Literal["Handrail"] = "Handrail"


class Stair(Accessory):
    type: Literal["Stair"] = "Stair"


class Ladder(Accessory):
    type: Literal["Ladder"] = "Ladder"


class SafetyGate(Accessory):
    type: Literal["SafetyGate"] = "SafetyGate"


class Deck(Accessory):
    type: Literal["Deck"] = "Deck"


class WorkPoint(Node):
    """Survey control or work point with coordinates and elevation (work point tables, pile
    coordinates)."""

    type: Literal["WorkPoint"] = "WorkPoint"
    easting: Decimal | None = lit("easting")
    easting_text: str | None = lit("eastingText")
    elevation_m: Decimal | None = lit("elevationM")
    northing: Decimal | None = lit("northing")
    northing_text: str | None = lit("northingText")


class ScopeItem(Node):
    """One lettered or numbered scope-of-work item (an item code with its text, such as supply
    and install piles) on a scope plan or scope table; tells the fabricator what is theirs."""

    type: Literal["ScopeItem"] = "ScopeItem"
    scope_item_work: WorkKind | None = lit("scopeItemWork")
    scope_item_id: str | None = lit("scopeItemId")
    scope_item_text: str | None = lit("scopeItemText")


class ForceRecord(Node):
    """Design forces or loads for one element and one load case, as printed on the drawing (not
    computed)."""

    type: Literal["ForceRecord"] = "ForceRecord"
    load_direction: LoadDirection | None = lit("loadDirection")
    load_type: LoadType | None = lit("loadType")
    axial_value: Decimal | None = lit("axialValue")
    compression_value: Decimal | None = lit("compressionValue")
    compression_positive: bool | None = lit("compressionPositive")
    force_group: str | None = lit("forceGroup")
    force_unit: str | None = lit("forceUnit")
    is_factored: bool | None = lit("isFactored")
    load_case: str | None = lit("loadCase")
    moment_major_value: Decimal | None = lit("momentMajorValue")
    moment_minor_value: Decimal | None = lit("momentMinorValue")
    moment_unit: str | None = lit("momentUnit")
    shear_major_value: Decimal | None = lit("shearMajorValue")
    shear_minor_value: Decimal | None = lit("shearMinorValue")
    symmetric_tension_compression: bool | None = lit("symmetricTensionCompression")
    tension_value: Decimal | None = lit("tensionValue")
    torsion_value: Decimal | None = lit("torsionValue")


class Zone(Node):
    """A region of a building or plant that carries its own data: area loads, repair type,
    status, or a column set."""

    type: Literal["Zone"] = "Zone"
    has_area_load: list[str] = refs("hasAreaLoad", "AreaLoad")
    zone_kind: ZoneKind | None = lit("zoneKind")
    zone_on_sheet: str | None = ref("zoneOnSheet", "Sheet")
    zone_status: ElementStatus | None = lit("zoneStatus")


class AreaLoad(Node):
    """A load stated per area (kPa) for a zone, not per element: snow drift, uplift zones, live
    load by room use."""

    type: Literal["AreaLoad"] = "AreaLoad"
    area_load_type: LoadType | None = lit("areaLoadType")
    area_load_factored: bool | None = lit("areaLoadFactored")
    area_load_kpa: Decimal | None = lit("areaLoadKPa")


class DesignParameter(Node):
    """A named design input printed on a notes sheet: wind pressure q, snow Ss, Sa(0.2), site
    class, importance factor."""

    type: Literal["DesignParameter"] = "DesignParameter"
    parameter_name: str | None = lit("parameterName")
    parameter_unit_text: str | None = lit("parameterUnitText")
    parameter_value_text: str | None = lit("parameterValueText")


class RequirementClause(Node):
    """One numbered clause of a notes sheet, standard or work package (e.g. 'minimum fillet weld
    1/4 in', '100% UT on member splices'). Applies by reference to every element of the stated
    kind in the set."""

    type: Literal["RequirementClause"] = "RequirementClause"
    requirement_topic: RequirementTopic | None = lit("requirementTopic")
    applies_at_elevation_text: str | None = lit("appliesAtElevationText")
    applies_to_kind_text: str | None = lit("appliesToKindText")
    clause_number: str | None = lit("clauseNumber")
    clause_text: str | None = lit("clauseText")
    clause_value: str | None = lit("clauseValue")
    coating_code_text: str | None = lit("coatingCodeText")
    consequence_text: str | None = lit("consequenceText")
    is_default_rule_clause: bool | None = lit("isDefaultRuleClause")
    is_prohibition: bool | None = lit("isProhibition")
    is_template_choice_unresolved: bool | None = lit("isTemplateChoiceUnresolved")
    notice_hours: int | None = lit("noticeHours")


class DefaultRule(Node):
    """A convention printed on the drawing that gives meaning to missing data, e.g. 'where no
    moment is shown, provide a full moment connection'."""

    type: Literal["DefaultRule"] = "DefaultRule"
    applies_for_purpose: list[IssuePurpose] = lits("appliesForPurpose")
    default_rule_kind: DefaultRuleKind | None = lit("defaultRuleKind")
    applies_to_property: str | None = lit("appliesToProperty")
    default_percent: Decimal | None = lit("defaultPercent")
    default_rule_text: str | None = lit("defaultRuleText")
    default_value_text: str | None = lit("defaultValueText")
    library_detail_ref_text: str | None = lit("libraryDetailRefText")


class Annotation(Node):
    """Anything drawn on the sheet that is not design geometry: a revision cloud, a reviewer's
    highlight, a hand note."""

    type: Literal["Annotation"] = "Annotation"
    seal_jurisdiction_text: str | None = lit("sealJurisdictionText")
    seal_scope_text: str | None = lit("sealScopeText")
    is_voided: bool | None = lit("isVoided")
    installation_constraint_text: str | None = lit("installationConstraintText")
    annotates: list[str] = refs("annotates", "Element")
    annotation_origin: AnnotationOrigin | None = lit("annotationOrigin")
    holds_zone: list[str] = refs("holdsZone", "Zone")
    markup_kind: MarkupKind | None = lit("markupKind")
    review_outcome: ReviewOutcome | None = lit("reviewOutcome")
    hold_condition: str | None = lit("holdCondition")
    is_tbd: bool | None = lit("isTBD")
    limits_design_responsibility: bool | None = lit("limitsDesignResponsibility")
    markup_meaning_text: str | None = lit("markupMeaningText")
    annotation_text: str | None = lit("annotationText")
    stamp_date: str | None = lit("stampDate")
    verbal_instruction_note: str | None = lit("verbalInstructionNote")


class ConstructionSequence(Annotation):
    """A boxed or numbered sequence on a drawing (shore, excavate, install foundations, install
    steel, remove old column last); order is content and may include a prohibition (do not
    remove the existing column before the new support is in)."""

    type: Literal["ConstructionSequence"] = "ConstructionSequence"
    sequence_step_text: list[str] = lits("sequenceStepText")


class Evidence(Node):
    """Where a fact was read: sheet, region and how sure the reader is. Every extracted fact
    should point to one (evidence-first)."""

    type: Literal["Evidence"] = "Evidence"
    confidence: ExtractionConfidence | None = lit("confidence")
    on_sheet: str | None = ref("onSheet", "Sheet")
    region_box: str | None = lit("regionBox")


AnyNode = Annotated[
    DrawingSet
    | Sheet
    | View
    | Party
    | Standard
    | StandardDocument
    | Revision
    | InclusionRow
    | Schedule
    | ScheduleRow
    | ElementRow
    | DrawingListRow
    | ScheduleCell
    | SelectionTable
    | SelectionRow
    | Element
    | ElementType
    | Member
    | Beam
    | Girt
    | Column
    | Brace
    | Joist
    | JoistGirder
    | Stringer
    | Post
    | Connection
    | BasePlateConnection
    | ShearConnection
    | MomentConnection
    | BraceConnection
    | Support
    | Pile
    | Footing
    | Bearing
    | Plate
    | LiftingLug
    | KeeperPlate
    | Fastener
    | Assembly
    | Truss
    | Accessory
    | Grating
    | Handrail
    | Stair
    | Ladder
    | SafetyGate
    | Deck
    | WorkPoint
    | ScopeItem
    | ForceRecord
    | Zone
    | AreaLoad
    | DesignParameter
    | RequirementClause
    | DefaultRule
    | Annotation
    | ConstructionSequence
    | Evidence,
    Field(discriminator="type"),
]
"""Any extracted object; the ``type`` field says which class it is."""

NODE_CLASSES: dict[str, type[Node]] = {
    "DrawingSet": DrawingSet,
    "Sheet": Sheet,
    "View": View,
    "Party": Party,
    "Standard": Standard,
    "StandardDocument": StandardDocument,
    "Revision": Revision,
    "InclusionRow": InclusionRow,
    "Schedule": Schedule,
    "ScheduleRow": ScheduleRow,
    "ElementRow": ElementRow,
    "DrawingListRow": DrawingListRow,
    "ScheduleCell": ScheduleCell,
    "SelectionTable": SelectionTable,
    "SelectionRow": SelectionRow,
    "Element": Element,
    "ElementType": ElementType,
    "Member": Member,
    "Beam": Beam,
    "Girt": Girt,
    "Column": Column,
    "Brace": Brace,
    "Joist": Joist,
    "JoistGirder": JoistGirder,
    "Stringer": Stringer,
    "Post": Post,
    "Connection": Connection,
    "BasePlateConnection": BasePlateConnection,
    "ShearConnection": ShearConnection,
    "MomentConnection": MomentConnection,
    "BraceConnection": BraceConnection,
    "Support": Support,
    "Pile": Pile,
    "Footing": Footing,
    "Bearing": Bearing,
    "Plate": Plate,
    "LiftingLug": LiftingLug,
    "KeeperPlate": KeeperPlate,
    "Fastener": Fastener,
    "Assembly": Assembly,
    "Truss": Truss,
    "Accessory": Accessory,
    "Grating": Grating,
    "Handrail": Handrail,
    "Stair": Stair,
    "Ladder": Ladder,
    "SafetyGate": SafetyGate,
    "Deck": Deck,
    "WorkPoint": WorkPoint,
    "ScopeItem": ScopeItem,
    "ForceRecord": ForceRecord,
    "Zone": Zone,
    "AreaLoad": AreaLoad,
    "DesignParameter": DesignParameter,
    "RequirementClause": RequirementClause,
    "DefaultRule": DefaultRule,
    "Annotation": Annotation,
    "ConstructionSequence": ConstructionSequence,
    "Evidence": Evidence,
}
"""Model class for each ontology class name."""

DEFAULT_BASE_IRI = "https://example.org/drawings/"


class Extraction(BaseModel):
    """Everything read from one drawing set: a flat list of typed objects.

    ``base_iri`` is the namespace the object ids live in once the extraction becomes RDF.
    """

    model_config = ConfigDict(extra="forbid")

    base_iri: str = DEFAULT_BASE_IRI
    nodes: list[AnyNode] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Extraction:
        seen: set[str] = set()
        for node in self.nodes:
            if node.id in seen:
                raise ValueError(f"duplicate id {node.id!r}")
            seen.add(node.id)
        return self

    def get(self, node_id: str) -> Node:
        """Return the object with this id; raise ``KeyError`` when there is none."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(node_id)

    def of_type[T: Node](self, cls: type[T]) -> list[T]:
        """Objects of a class, subclasses included (``of_type(Member)`` returns beams too)."""
        return [node for node in self.nodes if isinstance(node, cls)]

    def evidence_for(self, node: Node) -> list[Evidence]:
        """The ``Evidence`` objects a node points at, skipping ids that do not resolve."""
        by_id = {n.id: n for n in self.of_type(Evidence)}
        return [by_id[i] for i in node.evidenced_by if i in by_id]

    def dangling_references(self) -> list[str]:
        """Describe every link whose target is missing or is of the wrong class.

        An empty list means the extraction is closed: every id used as a link names an object
        of the class the ontology expects.
        """
        by_id = {node.id: node for node in self.nodes}
        problems = []
        for node in self.nodes:
            for name, target_class, targets in _links(node):
                for target in targets:
                    found = by_id.get(target)
                    if found is None:
                        problems.append(f"{node.id}.{name}: no object with id {target!r}")
                    elif not isinstance(found, NODE_CLASSES[target_class]):
                        actual = type(found).__name__
                        problems.append(
                            f"{node.id}.{name}: {target!r} is a {actual}, expected {target_class}"
                        )
        return problems

    def normalised(self) -> Extraction:
        """A copy with objects sorted by id and every list field sorted.

        RDF has no order and no duplicates, so this is the form that survives a round trip.
        """
        nodes = []
        for node in sorted(self.nodes, key=lambda n: n.id):
            updates = {
                name: sorted(set(value), key=str) for name, value in node if isinstance(value, list)
            }
            nodes.append(node.model_copy(update=updates))
        return Extraction(base_iri=self.base_iri, nodes=nodes)

    def to_json(self, indent: int = 2) -> str:
        """Serialise to JSON, leaving out empty fields so the file stays readable."""
        data = self.model_dump(mode="json", exclude_none=True)
        data["nodes"] = [
            {key: value for key, value in node.items() if value != []} for node in data["nodes"]
        ]
        return json.dumps(data, indent=indent, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Extraction:
        """Parse and validate the JSON written by ``to_json`` (or by an extractor)."""
        return cls.model_validate_json(text)


def rdf_fields(cls: type[Node]) -> dict[str, tuple[str, str | None]]:
    """Map each field of a model class to ``(ontology property, range class or None)``.

    The range is set for links to other objects and ``None`` for literals and enumerations.
    """
    mapped = {}
    for name, info in cls.model_fields.items():
        extra = info.json_schema_extra
        if isinstance(extra, dict) and RDF_KEY in extra:
            mapped[name] = (str(extra[RDF_KEY]), extra.get(RANGE_KEY))  # type: ignore[arg-type]
    return mapped


def _links(node: Node) -> list[tuple[str, str, list[str]]]:
    """``(field name, expected class, target ids)`` for every link field of a node."""
    links = []
    for name, (_, target_class) in rdf_fields(type(node)).items():
        if target_class is None:
            continue
        value = getattr(node, name)
        targets = value if isinstance(value, list) else [value] if value is not None else []
        links.append((name, target_class, targets))
    return links


def extraction_json_schema() -> dict[str, Any]:
    """JSON Schema of ``Extraction``, each field described by the ontology's own comment.

    This is the contract to hand to an extractor: the schema says what may be written and the
    descriptions say what each field means, in the words of ``ontology/core.ttl``.
    """
    described = comments()
    schema = Extraction.model_json_schema()
    for definition in schema.get("$defs", {}).values():
        for field in definition.get("properties", {}).values():
            text = described.get(field.get(RDF_KEY, ""))
            if text:
                field.setdefault("description", text)
    return schema
