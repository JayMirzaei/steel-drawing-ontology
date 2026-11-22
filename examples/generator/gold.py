"""The gold extraction of the example set, and a deliberately broken variant.

``build`` turns the invented job data into the typed objects a perfect reader would produce.
Each fact cites the zone of the sheet where ``draw`` put it. ``break_it`` then damages a copy in
ways an extractor really fails (a misread total, missing mandatory fields) so the shapes have
something to catch.
"""

from __future__ import annotations

from decimal import Decimal

from generator import job
from generator.draw import Regions
from steel_ontology import enums as E
from steel_ontology import models as M

BASE_IRI = "https://example.org/kestrel-platform/"
BROKEN_TOTAL_KG = Decimal("1294.6")  # the printed 1249.6 with two digits swapped


class _Builder:
    """Collects objects and creates one ``Evidence`` per cited zone."""

    def __init__(self, regions: Regions) -> None:
        self.regions = regions
        self.nodes: list[M.Node] = []

    def add[T: M.Node](self, node: T) -> T:
        self.nodes.append(node)
        return node

    def cite(self, node_id: str, sheet: str, region: str) -> list[str]:
        """Create evidence for ``node_id`` at a recorded region; return it as a link list."""
        evidence = M.Evidence(
            id=f"ev-{node_id}",
            on_sheet=_sheet_id(sheet),
            region_box=self.regions[sheet][region],
            confidence=E.ExtractionConfidence.VERIFIED,
        )
        self.add(evidence)
        return [evidence.id]


def _sheet_id(number: str) -> str:
    return f"sheet-{number}"


def build(regions: Regions) -> M.Extraction:
    """The complete, correct extraction of the example drawing set."""
    b = _Builder(regions)
    clause_ids = _notes(b)
    _design_loads(b)
    _elements(b)
    schedule_ids = _schedules(b)
    view_ids = _views(b)
    annotation_ids = _annotations(b)
    _sheets_and_set(b, clause_ids, schedule_ids, view_ids, annotation_ids)
    return M.Extraction(base_iri=BASE_IRI, nodes=b.nodes)


def _notes(b: _Builder) -> list[str]:
    ids = []
    for note in job.NOTES:
        clause_id = f"clause-{note.number}"
        b.add(
            M.RequirementClause(
                id=clause_id,
                requirement_topic=E.RequirementTopic(note.topic),
                clause_number=note.number,
                clause_text=note.text,
                clause_value=note.value,
                is_prohibition=note.prohibition or None,
                notice_hours=note.notice_hours,
                is_default_rule_clause=True if note.number == job.DEFAULT_RULE_NOTE else None,
                cites_standard=_standards(b, note),
                evidenced_by=b.cite(clause_id, "S-001", f"note-{note.number}"),
            )
        )
        ids.append(clause_id)
    rule_note = next(n for n in job.NOTES if n.number == job.DEFAULT_RULE_NOTE)
    b.add(
        M.DefaultRule(
            id="default-brace-connections",
            default_rule_text=rule_note.text,
            default_rule_kind=E.DefaultRuleKind.PERCENT_OF_YIELD_RULE,
            default_percent=job.DEFAULT_RULE_PERCENT,
            applies_to_property="brace connection design force",
            default_value_text="50% of the tensile yield resistance of the brace",
            evidenced_by=b.cite("default-brace-connections", "S-001", f"note-{rule_note.number}"),
        )
    )
    return ids


def _standards(b: _Builder, note: job.Note) -> list[str]:
    """One ``Standard`` per code a note cites, read at the note that names it."""
    ids = []
    for designation in job.CITED_STANDARDS.get(note.number, ()):
        standard_id = "standard-" + designation.replace(" ", "-").replace(".", "-")
        b.add(
            M.Standard(
                id=standard_id,
                standard_designation=designation,
                evidenced_by=b.cite(standard_id, "S-001", f"note-{note.number}"),
            )
        )
        ids.append(standard_id)
    return ids


def _design_loads(b: _Builder) -> None:
    """Area loads hang off a load zone, not off the sheet that prints them."""
    ids = []
    for label, load_type, kpa in job.AREA_LOADS:
        load_id = f"area-load-{load_type}"
        b.add(
            M.AreaLoad(
                id=load_id,
                area_load_type=E.LoadType(load_type),
                area_load_kpa=kpa,
                area_load_factored=False,
                evidenced_by=b.cite(load_id, "S-001", f"load-row-{label}"),
            )
        )
        ids.append(load_id)
    b.add(
        M.Zone(
            id="zone-platform",
            zone_kind=E.ZoneKind.LOAD_ZONE_KIND,
            zone_on_sheet=_sheet_id("S-101"),
            has_area_load=ids,
        )
    )
    b.add(
        M.DesignParameter(
            id="parameter-importance",
            parameter_name="IMPORTANCE CATEGORY",
            parameter_value_text=job.IMPORTANCE_CATEGORY,
            evidenced_by=b.cite("parameter-importance", "S-001", "importance"),
        )
    )


def _elements(b: _Builder) -> None:
    for row in job.COLUMN_ROWS:
        element_id = f"{row.kind.lower()}-{row.mark}"
        force_ids = []
        if row.factored_axial_kn is not None:
            force_id = f"force-{row.mark}-Cf"
            b.add(
                M.ForceRecord(
                    id=force_id,
                    load_case="Cf",
                    load_type=E.LoadType.LOAD_COMBINATION,
                    load_direction=E.LoadDirection.VERTICAL,
                    is_factored=True,
                    compression_value=Decimal(row.factored_axial_kn),
                    force_unit="kN",
                    evidenced_by=b.cite(force_id, "S-201", f"column-cell-{row.mark}-5"),
                )
            )
            force_ids.append(force_id)
        b.add(
            M.NODE_CLASSES[row.kind](
                id=element_id,
                tag=row.mark,
                section_text=row.section,
                required_quantity=row.quantity,
                cut_length_mm=Decimal(row.length_mm),
                grid_location_text=list(job.COLUMN_LOCATIONS.get(row.mark, ())),
                element_status=E.ElementStatus.NEW_WORK,
                responsibility=[E.ResponsibilityTag.BY_ENGINEER_OF_RECORD],
                has_force_record=force_ids,
                in_zone="zone-platform",
                evidenced_by=b.cite(element_id, "S-201", f"column-row-{row.mark}"),
            )
        )

    for beam in job.BEAMS:
        element_id = f"beam-{beam.mark}"
        b.add(
            M.Beam(
                id=element_id,
                tag=beam.mark,
                section_text=beam.section,
                required_quantity=beam.quantity,
                elevation_m=job.TOP_OF_STEEL_M,
                elevation_kind="T/STEEL",
                element_status=E.ElementStatus.NEW_WORK,
                responsibility=[E.ResponsibilityTag.BY_ENGINEER_OF_RECORD],
                revised_in_this_issue=True if beam.mark == "B3" else None,
                in_zone="zone-platform",
                evidenced_by=b.cite(element_id, "S-101", element_id),
            )
        )

    b.add(
        M.ForceRecord(
            id="force-VB1",
            load_case="Tf/Cf",
            load_type=E.LoadType.LOAD_COMBINATION,
            load_direction=E.LoadDirection.ALONG_MEMBER_AXIS,
            is_factored=True,
            symmetric_tension_compression=True,
            tension_value=Decimal(job.BRACE_FORCE_KN),
            compression_value=Decimal(job.BRACE_FORCE_KN),
            force_unit="kN",
            evidenced_by=b.cite("force-VB1", "S-101", "brace-VB1"),
        )
    )
    b.add(
        M.Brace(
            id="brace-VB1",
            tag=job.BRACE_MARK,
            section_text=job.BRACE_SECTION,
            required_quantity=2,
            element_status=E.ElementStatus.NEW_WORK,
            responsibility=[E.ResponsibilityTag.BY_ENGINEER_OF_RECORD],
            has_force_record=["force-VB1"],
            evidenced_by=b.cite("brace-VB1", "S-101", "brace-VB1"),
        )
    )
    _connections(b)


def _connections(b: _Builder) -> None:
    b.add(
        M.ShearConnection(
            id="connection-SC1",
            tag="SC1",
            connects=["beam-B1", "column-C1"],
            weld_pattern="6",
            responsibility=[E.ResponsibilityTag.BY_ENGINEER_OF_RECORD],
            evidenced_by=b.cite("connection-SC1", "S-301", "detail-1"),
        )
    )
    b.add(
        M.BraceConnection(
            id="connection-brace",
            connects=["brace-VB1", "column-C1"],
            responsibility=[E.ResponsibilityTag.BY_CONNECTION_ENGINEER],
            requires_sealed_design=True,
            is_design_open=True,
            evidenced_by=b.cite("connection-brace", "S-001", f"note-{job.CONNECTION_DESIGN_NOTE}"),
        )
    )
    columns = {row.base_plate: f"column-{row.mark}" for row in job.COLUMN_ROWS if row.base_plate}
    for plate in job.BASE_PLATE_ROWS:
        element_id = f"base-plate-{plate.mark}"
        b.add(
            M.BasePlateConnection(
                id=element_id,
                tag=plate.mark,
                connects=[columns[plate.mark]],
                supports=[columns[plate.mark]],
                weld_pattern=plate.weld_mm,
                responsibility=[E.ResponsibilityTag.BY_ENGINEER_OF_RECORD],
                evidenced_by=b.cite(element_id, "S-201", f"base-plate-row-{plate.mark}"),
            )
        )
    b.add(
        M.Fastener(
            id="anchor-rods",
            responsibility=[E.ResponsibilityTag.BY_OTHERS],
            evidenced_by=b.cite("anchor-rods", "S-001", f"note-{job.ANCHOR_ROD_NOTE}"),
        )
    )
    b.add(
        M.Grating(
            id="grating",
            responsibility=[E.ResponsibilityTag.BY_SUPPLIER],
            work_kind=E.WorkKind.INSTALL_ONLY,
            in_zone="zone-platform",
            evidenced_by=b.cite("grating", "S-001", f"note-{job.GRATING_NOTE}"),
        )
    )


def _cell(b: _Builder, cell_id: str, header: str, text: str, unit: str | None, region: str) -> str:
    """Add one schedule cell, classifying the printed text; return its id."""
    if text == "N/A":
        kind = E.CellValueKind.NOT_APPLICABLE_CELL
    elif "SUPPLIER" in text:
        kind = E.CellValueKind.BY_SUPPLIER_CELL
    elif text.replace(".", "", 1).isdigit():
        kind = E.CellValueKind.NUMBER_CELL
    else:
        kind = E.CellValueKind.TEXT_CELL
    b.add(
        M.ScheduleCell(
            id=cell_id,
            column_header_text=header,
            cell_text=text,
            cell_value_kind=kind,
            cell_unit_text=unit,
            evidenced_by=b.cite(cell_id, "S-201", region),
        )
    )
    return cell_id


def _schedules(b: _Builder) -> list[str]:
    column_headers = (
        ("MARK", None),
        ("SECTION", None),
        ("QTY", None),
        ("LENGTH (mm)", "mm"),
        ("BASE PLATE", None),
        ("Cf (kN) FACTORED", "kN"),
        ("WEIGHT (kg)", "kg"),
    )
    row_ids = []
    for row in job.COLUMN_ROWS:
        texts = (
            row.mark,
            row.section,
            str(row.quantity),
            str(row.length_mm),
            row.base_plate or "N/A",
            str(row.factored_axial_kn) if row.factored_axial_kn is not None else "N/A",
            str(row.weight_kg),
        )
        cells = [
            _cell(b, f"cell-{row.mark}-{i}", header, text, unit, f"column-cell-{row.mark}-{i}")
            for i, ((header, unit), text) in enumerate(zip(column_headers, texts, strict=True))
        ]
        row_id = f"row-{row.mark}"
        b.add(
            M.ElementRow(
                id=row_id,
                describes_element=f"{row.kind.lower()}-{row.mark}",
                row_value=row.weight_kg,
                has_cell=cells,
                evidenced_by=b.cite(row_id, "S-201", f"column-row-{row.mark}"),
            )
        )
        row_ids.append(row_id)
    b.add(
        M.Schedule(
            id="schedule-columns",
            schedule_kind=E.ScheduleKind.COLUMN_SCHEDULE,
            has_row=row_ids,
            declared_total=job.COLUMN_TOTAL_KG,
            evidenced_by=b.cite("schedule-columns", "S-201", "column-total"),
        )
    )

    plate_headers = (
        ("MARK", None),
        ("PLATE (mm)", "mm"),
        ("HOLES", "mm"),
        ("ANCHOR RODS", None),
        ("WELD TO COLUMN (mm)", "mm"),
    )
    plate_row_ids = []
    for plate in job.BASE_PLATE_ROWS:
        texts = (plate.mark, plate.plate, plate.holes, plate.anchor_rods, plate.weld_mm)
        cells = [
            _cell(
                b, f"cell-{plate.mark}-{i}", header, text, unit, f"base-plate-cell-{plate.mark}-{i}"
            )
            for i, ((header, unit), text) in enumerate(zip(plate_headers, texts, strict=True))
        ]
        row_id = f"row-{plate.mark}"
        b.add(
            M.ElementRow(
                id=row_id,
                describes_element=f"base-plate-{plate.mark}",
                has_cell=cells,
                evidenced_by=b.cite(row_id, "S-201", f"base-plate-row-{plate.mark}"),
            )
        )
        plate_row_ids.append(row_id)
    b.add(
        M.Schedule(
            id="schedule-base-plates",
            schedule_kind=E.ScheduleKind.BASE_PLATE_SCHEDULE,
            has_row=plate_row_ids,
            evidenced_by=b.cite("schedule-base-plates", "S-201", "base-plate-schedule"),
        )
    )
    return ["schedule-columns", "schedule-base-plates"]


def _views(b: _Builder) -> dict[str, list[str]]:
    """Add the views; return view ids per sheet number."""
    b.add(
        M.View(
            id="view-detail-1",
            view_kind=E.ViewKind.DETAIL_VIEW,
            view_code="1",
            scale_text="1:10",
            is_typical=True,
            shows_element=["connection-SC1", "beam-B1", "column-C1"],
            evidenced_by=b.cite("view-detail-1", "S-301", "detail-1"),
        )
    )
    b.add(
        M.View(
            id="view-detail-2",
            view_kind=E.ViewKind.DETAIL_VIEW,
            view_code="2",
            scale_text="1:10",
            shows_element=["base-plate-BP1", "anchor-rods"],
            evidenced_by=b.cite("view-detail-2", "S-301", "detail-2"),
        )
    )
    plan_elements = [f"beam-{beam.mark}" for beam in job.BEAMS]
    plan_elements += [f"column-{mark}" for mark in job.COLUMN_LOCATIONS]
    b.add(
        M.View(
            id="view-framing-plan",
            view_kind=E.ViewKind.PLAN_VIEW,
            scale_text="1:75",
            shows_element=[*plan_elements, "brace-VB1"],
            callout_to=["view-detail-1"],
            callout_target_sheet_text="S-301",
            evidenced_by=b.cite("view-framing-plan", "S-101", "plan-view"),
        )
    )
    b.add(
        M.View(
            id="view-schedules",
            view_kind=E.ViewKind.SCHEDULE_VIEW,
            evidenced_by=b.cite("view-schedules", "S-201", "column-schedule"),
        )
    )
    return {
        "S-101": ["view-framing-plan"],
        "S-201": ["view-schedules"],
        "S-301": ["view-detail-1", "view-detail-2"],
    }


def _annotations(b: _Builder) -> list[str]:
    """The engineer's revision cloud and three pieces of third-party markup, all on S-101."""
    b.add(
        M.Annotation(
            id="annotation-revision-cloud",
            annotation_origin=E.AnnotationOrigin.ENGINEER_ORIGIN,
            markup_kind=E.MarkupKind.REVISION_CLOUD,
            annotates=["beam-B3"],
            evidenced_by=b.cite("annotation-revision-cloud", "S-101", "revision-cloud"),
        )
    )
    b.add(
        M.Annotation(
            id="annotation-takeoff-highlight",
            annotation_origin=E.AnnotationOrigin.THIRD_PARTY_ORIGIN,
            markup_kind=E.MarkupKind.TAKEOFF_HIGHLIGHT,
            markup_meaning_text=job.HIGHLIGHT_MEANING,
            annotates=["beam-B1"],
            evidenced_by=b.cite("annotation-takeoff-highlight", "S-101", "highlight-B1"),
        )
    )
    b.add(
        M.Annotation(
            id="annotation-query-note",
            annotation_origin=E.AnnotationOrigin.THIRD_PARTY_ORIGIN,
            markup_kind=E.MarkupKind.QUERY_NOTE,
            annotation_text=job.QUERY_NOTE_TEXT,
            annotates=["beam-B3"],
            evidenced_by=b.cite("annotation-query-note", "S-101", "query-note"),
        )
    )
    b.add(
        M.Annotation(
            id="annotation-received-stamp",
            annotation_origin=E.AnnotationOrigin.THIRD_PARTY_ORIGIN,
            markup_kind=E.MarkupKind.RECEIVED_STAMP,
            annotation_text="RECEIVED",
            stamp_date=job.RECEIVED_STAMP_DATE,
            evidenced_by=b.cite("annotation-received-stamp", "S-101", "received-stamp"),
        )
    )
    return [
        "annotation-revision-cloud",
        "annotation-takeoff-highlight",
        "annotation-query-note",
        "annotation-received-stamp",
    ]


def _sheets_and_set(
    b: _Builder,
    clause_ids: list[str],
    schedule_ids: list[str],
    view_ids: dict[str, list[str]],
    annotation_ids: list[str],
) -> None:
    for index, sheet in enumerate(job.SHEETS, start=1):
        revision_ids = []
        for revision in job.REVISIONS:
            revision_id = f"revision-{sheet.number}-{revision.code}"
            b.add(
                M.Revision(
                    id=revision_id,
                    revision_code=revision.code,
                    revision_date=revision.date,
                    issue_purpose=E.IssuePurpose(revision.purpose),
                    evidenced_by=b.cite(revision_id, sheet.number, f"revision-{revision.code}"),
                )
            )
            revision_ids.append(revision_id)
        notes_sheet = sheet.number == "S-001"
        b.add(
            M.Sheet(
                id=_sheet_id(sheet.number),
                sheet_number=sheet.number,
                sheet_title=sheet.title,
                page_index=index,
                sheet_total=len(job.SHEETS),
                sheet_kind=E.SheetKind(sheet.kind),
                sheet_discipline=[E.Discipline.STEEL_DISCIPLINE],
                project_number=job.PROJECT_NUMBER,
                has_revision=revision_ids,
                has_view=view_ids.get(sheet.number, []),
                has_schedule=schedule_ids if sheet.number == "S-201" else [],
                has_annotation=annotation_ids if sheet.number == "S-101" else [],
                has_requirement=clause_ids if notes_sheet else [],
                has_default_rule=["default-brace-connections"] if notes_sheet else [],
                has_design_parameter=["parameter-importance"] if notes_sheet else [],
                evidenced_by=b.cite(_sheet_id(sheet.number), sheet.number, "title-block"),
            )
        )
    b.add(
        M.DrawingSet(
            id="drawing-set",
            project_number=job.PROJECT_NUMBER,
            unit_system=E.UnitSystem.METRIC,
            in_domain=E.Domain.PLATFORM_STAIR_DOMAIN,
            author_role=[E.AuthorRole.ENGINEER_OF_RECORD_ROLE],
            revision_code_scheme="letters before the construction issue, then numbers",
            has_sheet=[_sheet_id(sheet.number) for sheet in job.SHEETS],
        )
    )


def break_it(gold: M.Extraction) -> M.Extraction:
    """A copy of the gold extraction with the mistakes a real extractor makes.

    - the schedule total is misread (two digits swapped), so the arithmetic check fires;
    - a force loses its factored/unfactored tag;
    - a stamp loses its origin, so nobody knows whether the engineer drew it;
    - a sheet loses its kind;
    - the default-rule percentage is read as 500;
    - one piece of evidence loses its confidence.
    """
    changes = {
        "schedule-columns": {"declared_total": BROKEN_TOTAL_KG},
        "force-C1-Cf": {"is_factored": None},
        "annotation-received-stamp": {"annotation_origin": None},
        _sheet_id("S-301"): {"sheet_kind": None},
        "default-brace-connections": {"default_percent": Decimal("500")},
        "ev-beam-B1": {"confidence": None},
    }
    nodes = [node.model_copy(update=changes.get(node.id, {})) for node in gold.nodes]
    return M.Extraction(base_iri=gold.base_iri, nodes=nodes)
