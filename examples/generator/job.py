"""The invented job: a small steel equipment platform.

Everything here is made up for testing. The project, numbers and dates are invented.
Section names (W310x39, HSS102x102x6.4) and material standards are public.
Lengths are in millimetres, forces in kilonewtons, masses in kilograms.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

PROJECT_NAME = "KESTREL YARD EQUIPMENT PLATFORM"
PROJECT_NUMBER = "EX-0417"
DISCLAIMER = "SYNTHETIC EXAMPLE - NOT A REAL PROJECT - NOT FOR CONSTRUCTION"
TOP_OF_STEEL_M = Decimal("104.200")


@dataclass(frozen=True)
class SheetInfo:
    number: str
    title: str
    kind: str  # member of the SheetKind vocabulary
    scale: str


SHEETS = (
    SheetInfo("S-001", "GENERAL NOTES", "GeneralNotesSheet", "N.T.S."),
    SheetInfo("S-101", "PLATFORM FRAMING PLAN", "PlanSheet", "1:75"),
    SheetInfo("S-201", "COLUMN AND BASE PLATE SCHEDULES", "ScheduleSheet", "N.T.S."),
    SheetInfo("S-301", "CONNECTION DETAILS", "DetailSheet", "1:10"),
)


@dataclass(frozen=True)
class RevisionInfo:
    code: str
    date: str
    description: str
    purpose: str  # member of the IssuePurpose vocabulary


REVISIONS = (
    RevisionInfo("A", "2030-02-11", "ISSUED FOR REVIEW", "IssuedForReview"),
    RevisionInfo("0", "2030-03-18", "ISSUED FOR CONSTRUCTION", "IssuedForConstruction"),
)

GRID_LETTERS = {"A": 0, "B": 6000, "C": 12000}  # x position of each lettered grid
GRID_NUMBERS = {"1": 0, "2": 4500}  # y position of each numbered grid


@dataclass(frozen=True)
class ColumnRow:
    """One row of the column schedule."""

    mark: str
    kind: str  # ontology class: Column or Post
    section: str
    quantity: int
    length_mm: int
    base_plate: str | None
    factored_axial_kn: int | None
    weight_kg: Decimal  # mass per metre x length x quantity, as printed


COLUMN_ROWS = (
    ColumnRow("C1", "Column", "W200x46", 4, 4200, "BP1", 310, Decimal("772.8")),
    ColumnRow("C2", "Column", "W200x52", 2, 4200, "BP2", 520, Decimal("436.8")),
    ColumnRow("P1", "Post", "HSS102x102x6.4", 2, 1100, None, None, Decimal("40.0")),
)
COLUMN_TOTAL_KG = Decimal("1249.6")
COLUMN_LOCATIONS = {"C1": ("A/1", "A/2", "C/1", "C/2"), "C2": ("B/1", "B/2")}


@dataclass(frozen=True)
class BasePlateRow:
    """One row of the base plate schedule."""

    mark: str
    plate: str
    holes: str
    anchor_rods: str
    weld_mm: str


BASE_PLATE_ROWS = (
    BasePlateRow("BP1", "PL20x300x300", "4 - 22 DIA.", "BY FOUNDATION SUPPLIER", "6"),
    BasePlateRow("BP2", "PL25x350x350", "4 - 27 DIA.", "BY FOUNDATION SUPPLIER", "8"),
)


@dataclass(frozen=True)
class BeamInfo:
    mark: str
    section: str
    quantity: int


BEAMS = (
    BeamInfo("B1", "W310x39", 4),  # along grids 1 and 2
    BeamInfo("B2", "W250x33", 3),  # along grids A, B and C
    BeamInfo("B3", "W200x27", 2),  # infill at mid-bay, revised in the latest issue
)
BRACE_MARK = "VB1"
BRACE_SECTION = "HSS102x102x6.4"
BRACE_FORCE_KN = 180
BRACE_FORCE_TEXT = f"Tf/Cf = {BRACE_FORCE_KN} kN"


@dataclass(frozen=True)
class Note:
    """One numbered general note and how the ontology classifies it."""

    number: str
    heading: str
    text: str
    topic: str  # member of the RequirementTopic vocabulary
    value: str | None = None
    prohibition: bool = False
    notice_hours: int | None = None


NOTES = (
    Note("1", "MATERIALS", "W SHAPES AND HSS: CSA G40.21 GRADE 350W.", "MaterialReq", "350W"),
    Note(
        "2",
        "MATERIALS",
        "BOLTS: ASTM F3125 GRADE A325, 20 mm DIAMETER, SNUG TIGHT UNLESS NOTED.",
        "BoltingReq",
        "20 mm A325",
    ),
    Note(
        "3",
        "MATERIALS",
        "WELDING TO CSA W59. MINIMUM FILLET WELD 6 mm.",
        "WeldingReq",
        "6 mm",
    ),
    Note(
        "4",
        "ERECTION",
        "DO NOT FIELD CUT OR BURN HOLES IN BASE PLATES.",
        "ErectionReq",
        prohibition=True,
    ),
    Note(
        "5",
        "CONNECTIONS",
        "UNLESS NOTED OTHERWISE, DESIGN BRACE CONNECTIONS FOR 50% OF THE TENSILE YIELD "
        "RESISTANCE OF THE BRACE.",
        "ConnectionDesignReq",
        "50%",
    ),
    Note(
        "6",
        "CONNECTIONS",
        "CONNECTIONS NOT DETAILED ON THESE DRAWINGS ARE TO BE DESIGNED BY THE FABRICATOR'S "
        "CONNECTION ENGINEER. SUBMIT SEALED CALCULATIONS.",
        "SubmittalReq",
        "sealed calculations",
    ),
    Note(
        "7",
        "SCOPE",
        "ANCHOR RODS AND GROUT ARE SUPPLIED AND INSTALLED BY OTHERS.",
        "ScopeExclusionReq",
        "by others",
    ),
    Note(
        "8",
        "SCOPE",
        "GRATING IS SUPPLIED BY THE GRATING SUPPLIER AND INSTALLED BY THE STEEL ERECTOR.",
        "GratingReq",
        "supply by supplier",
    ),
    Note(
        "9",
        "INSPECTION",
        "GIVE 48 HOURS NOTICE BEFORE EACH FIELD REVIEW.",
        "InspectionReq",
        "48 hours",
        notice_hours=48,
    ),
)
CITED_STANDARDS = {"1": ("CSA G40.21",), "2": ("ASTM F3125",), "3": ("CSA W59",)}  # by note
DEFAULT_RULE_NOTE = "5"
DEFAULT_RULE_PERCENT = Decimal("50")
CONNECTION_DESIGN_NOTE = "6"
ANCHOR_ROD_NOTE = "7"
GRATING_NOTE = "8"

AREA_LOADS = (  # label, load type, kPa; printed as unfactored
    ("PLATFORM LIVE LOAD", "LiveLoad", Decimal("4.8")),
    ("DEAD LOAD (GRATING AND FRAMING)", "DeadLoad", Decimal("1.0")),
)
IMPORTANCE_CATEGORY = "NORMAL"

RECEIVED_STAMP_DATE = "2030-03-20"
QUERY_NOTE_TEXT = "CONFIRM B3 SIZE?"
HIGHLIGHT_MEANING = "orange highlight = taken off"
