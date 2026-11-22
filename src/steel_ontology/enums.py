"""Controlled vocabularies of the ontology as Python enumerations.

Each enumeration mirrors one closed ``owl:oneOf`` class in ``ontology/core.ttl``. A member's value
is the local name of the individual, so ``SheetKind.PLAN_SHEET.value == "PlanSheet"`` maps to
``steel:PlanSheet``. ``tests/test_models.py`` checks that the two stay in step.
"""

from enum import StrEnum


class SheetKind(StrEnum):
    GENERAL_NOTES_SHEET = "GeneralNotesSheet"
    SPECIFICATION_SHEET = "SpecificationSheet"
    COVER_SHEET = "CoverSheet"
    INDEX_SHEET = "IndexSheet"
    PLAN_SHEET = "PlanSheet"
    ELEVATION_SHEET = "ElevationSheet"
    SECTION_SHEET = "SectionSheet"
    DETAIL_SHEET = "DetailSheet"
    SCHEDULE_SHEET = "ScheduleSheet"
    THREE_DSHEET = "ThreeDSheet"
    TYPICAL_DETAILS_SHEET = "TypicalDetailsSheet"
    ISSUE_RECORD_SHEET = "IssueRecordSheet"
    SCOPE_SHEET = "ScopeSheet"
    PHOTO_SHEET = "PhotoSheet"
    HAND_SKETCH_SHEET = "HandSketchSheet"
    PIPING_ISOMETRIC_SHEET = "PipingIsometricSheet"
    STANDARD_SHEET = "StandardSheet"
    BLANK_SHEET = "BlankSheet"
    WORK_PACKAGE_SHEET = "WorkPackageSheet"
    CHANGE_NOTICE_SHEET = "ChangeNoticeSheet"
    MANUAL_SHEET = "ManualSheet"
    TRANSMITTAL_SHEET = "TransmittalSheet"
    REACTION_SHEET = "ReactionSheet"
    ANCHOR_BOLT_PLAN_SHEET = "AnchorBoltPlanSheet"
    FRAME_CROSS_SECTION_SHEET = "FrameCrossSectionSheet"
    CONSULTANT_LIST_SHEET = "ConsultantListSheet"


class ViewKind(StrEnum):
    PLAN_VIEW = "PlanView"
    ELEVATION_VIEW = "ElevationView"
    SECTION_VIEW = "SectionView"
    DETAIL_VIEW = "DetailView"
    THREE_DVIEW = "ThreeDView"
    PHOTO_VIEW = "PhotoView"
    KEY_PLAN_VIEW = "KeyPlanView"
    ISOMETRIC_VIEW = "IsometricView"
    SCHEDULE_VIEW = "ScheduleView"
    NOTES_VIEW = "NotesView"


class IssuePurpose(StrEnum):
    ISSUED_FOR_CONSTRUCTION = "IssuedForConstruction"
    ISSUED_FOR_REVIEW = "IssuedForReview"
    ISSUED_FOR_TENDER = "IssuedForTender"
    ISSUED_FOR_BID = "IssuedForBid"
    ISSUED_FOR_PRICING = "IssuedForPricing"
    ISSUED_FOR_PERMIT = "IssuedForPermit"
    PRELIMINARY = "Preliminary"
    CONTROLLED_RELEASE = "ControlledRelease"
    AS_BUILT = "AsBuilt"
    FOR_REFERENCE_ONLY = "ForReferenceOnly"
    FOR_INFORMATION_ONLY = "ForInformationOnly"
    FOR_IMPLEMENTATION = "ForImplementation"
    ISSUED_FOR_ERECTION = "IssuedForErection"
    ISSUED_FOR_APPROVAL = "IssuedForApproval"
    ISSUED_FOR_COORDINATION = "IssuedForCoordination"
    NON_PUBLISHED = "NonPublished"
    UNCONTROLLED_IF_PRINTED = "UncontrolledIfPrinted"
    ISSUED_FOR_DESIGN = "IssuedForDesign"


class UnitSystem(StrEnum):
    METRIC = "Metric"
    IMPERIAL = "Imperial"
    MIXED_UNITS = "MixedUnits"
    DUAL_UNITS = "DualUnits"


class Discipline(StrEnum):
    """Trade/discipline a sheet or view belongs to; a folder of structural drawings can still
    contain non-structural sheets."""

    STEEL_DISCIPLINE = "SteelDiscipline"
    CONCRETE_DISCIPLINE = "ConcreteDiscipline"
    MASONRY_DISCIPLINE = "MasonryDiscipline"
    TIMBER_DISCIPLINE = "TimberDiscipline"
    ARCHITECTURAL_DISCIPLINE = "ArchitecturalDiscipline"
    PIPING_DISCIPLINE = "PipingDiscipline"
    CIVIL_DISCIPLINE = "CivilDiscipline"
    MECHANICAL_ELECTRICAL_DISCIPLINE = "MechanicalElectricalDiscipline"


class AuthorRole(StrEnum):
    ENGINEER_OF_RECORD_ROLE = "EngineerOfRecordRole"
    SUPPLIER_DESIGN_ROLE = "SupplierDesignRole"
    FABRICATOR_SHOP_ROLE = "FabricatorShopRole"
    OWNER_STANDARD_ROLE = "OwnerStandardRole"
    FIELD_PACKAGE_ROLE = "FieldPackageRole"
    ARCHITECT_ROLE = "ArchitectRole"
    DETAILER_ROLE = "DetailerRole"


class Domain(StrEnum):
    BUILDING_DOMAIN = "BuildingDomain"
    INDUSTRIAL_SKID_DOMAIN = "IndustrialSkidDomain"
    PLATFORM_STAIR_DOMAIN = "PlatformStairDomain"
    PARKING_STRUCTURE_DOMAIN = "ParkingStructureDomain"
    RESIDENTIAL_MODULAR_DOMAIN = "ResidentialModularDomain"
    FIELD_REPAIR_DOMAIN = "FieldRepairDomain"
    PRECAST_BUILDING_DOMAIN = "PrecastBuildingDomain"


class ChangeReason(StrEnum):
    """Why a revision was made (owner change-reason codes and common free-text reasons)."""

    SCOPE_CHANGE = "ScopeChange"
    HOLDS_REMOVED = "HoldsRemoved"
    VENDOR_DOCUMENT_UPDATE = "VendorDocumentUpdate"
    EXECUTION_STRATEGY_CHANGE = "ExecutionStrategyChange"
    CONSTRUCTION_REQUEST = "ConstructionRequest"
    DESIGN_CHANGE = "DesignChange"
    REGULATORY_UPDATE = "RegulatoryUpdate"
    DOCUMENT_CORRECTION = "DocumentCorrection"
    CLIENT_REQUEST = "ClientRequest"
    COORDINATION_CHANGE = "CoordinationChange"


class SubmissionStage(StrEnum):
    """Stage of the owner's review cycle recorded on an issue record (finer than issue
    purpose)."""

    PRELIMINARY_REVIEW_STAGE = "PreliminaryReviewStage"
    REVIEW60_STAGE = "Review60Stage"
    REVIEW90_STAGE = "Review90Stage"
    BID_STAGE = "BidStage"
    BID_ADDENDUM_STAGE = "BidAddendumStage"
    CONSTRUCTION_ISSUE_STAGE = "ConstructionIssueStage"
    REVIEW50_STAGE = "Review50Stage"
    REVIEW95_STAGE = "Review95Stage"
    REVIEW100_STAGE = "Review100Stage"


class ScheduleKind(StrEnum):
    COLUMN_SCHEDULE = "ColumnSchedule"
    BEAM_SCHEDULE = "BeamSchedule"
    PILE_SCHEDULE = "PileSchedule"
    FOOTING_SCHEDULE = "FootingSchedule"
    BASE_PLATE_SCHEDULE = "BasePlateSchedule"
    MEMBER_FORCE_SCHEDULE = "MemberForceSchedule"
    CONNECTION_FORCE_SCHEDULE = "ConnectionForceSchedule"
    JOIST_SCHEDULE = "JoistSchedule"
    DECK_SCHEDULE = "DeckSchedule"
    OPENING_SCHEDULE = "OpeningSchedule"
    PLATE_QUANTITY_SCHEDULE = "PlateQuantitySchedule"
    WALL_SCHEDULE = "WallSchedule"
    DRAWING_LIST_SCHEDULE = "DrawingListSchedule"
    BILL_OF_MATERIAL_SCHEDULE = "BillOfMaterialSchedule"
    HOLD_LIST_SCHEDULE = "HoldListSchedule"
    CUT_LIST_SCHEDULE = "CutListSchedule"
    OTHER_SCHEDULE = "OtherSchedule"


class CellValueKind(StrEnum):
    NUMBER_CELL = "NumberCell"
    TEXT_CELL = "TextCell"
    BY_SUPPLIER_CELL = "BySupplierCell"
    NOT_APPLICABLE_CELL = "NotApplicableCell"
    SEE_NOTE_CELL = "SeeNoteCell"
    BLANK_CELL = "BlankCell"
    LIBRARY_REF_CELL = "LibraryRefCell"


class ElementStatus(StrEnum):
    """Whether the element is new, existing, to be removed, or future (separate from who designs
    it)."""

    NEW_WORK = "NewWork"
    EXISTING_TO_REMAIN = "ExistingToRemain"
    EXISTING_TO_DEMOLISH = "ExistingToDemolish"
    EXISTING_TO_BE_MODIFIED = "ExistingToBeModified"
    FUTURE_PROVISION = "FutureProvision"


class ExposureClass(StrEnum):
    AESS = "AESS"
    STANDARD_EXPOSURE = "StandardExposure"


class ResponsibilityTag(StrEnum):
    """Who must design, supply or detail an element as stated on the drawing."""

    BY_ENGINEER_OF_RECORD = "ByEngineerOfRecord"
    BY_CONNECTION_ENGINEER = "ByConnectionEngineer"
    BY_FABRICATOR = "ByFabricator"
    BY_SUPPLIER = "BySupplier"
    BY_OTHERS = "ByOthers"
    BY_OWNER = "ByOwner"


class WorkKind(StrEnum):
    SUPPLY_ONLY = "SupplyOnly"
    FABRICATE_ONLY = "FabricateOnly"
    INSTALL_ONLY = "InstallOnly"
    SUPPLY_AND_INSTALL = "SupplyAndInstall"
    FIELD_WELD_ONLY = "FieldWeldOnly"
    SHIP_LOOSE = "ShipLoose"


class LoadType(StrEnum):
    DEAD_LOAD = "DeadLoad"
    LIVE_LOAD = "LiveLoad"
    SNOW_LOAD = "SnowLoad"
    WIND_LOAD = "WindLoad"
    SEISMIC_LOAD = "SeismicLoad"
    OTHER_LOAD = "OtherLoad"
    TOTAL_LOAD = "TotalLoad"
    LOAD_COMBINATION = "LoadCombination"
    BLAST_LOAD = "BlastLoad"
    PONDING_LOAD = "PondingLoad"


class LoadDirection(StrEnum):
    VERTICAL = "Vertical"
    HORIZONTAL_NS = "HorizontalNS"
    HORIZONTAL_EW = "HorizontalEW"
    HORIZONTAL_GENERAL = "HorizontalGeneral"
    UPLIFT_DIRECTION = "UpliftDirection"
    ALONG_MEMBER_AXIS = "AlongMemberAxis"


class ZoneKind(StrEnum):
    LOAD_ZONE_KIND = "LoadZoneKind"
    REPAIR_ZONE_KIND = "RepairZoneKind"
    PLANT_AREA_KIND = "PlantAreaKind"
    BUILDING_SEGMENT_KIND = "BuildingSegmentKind"
    FUTURE_AREA_KIND = "FutureAreaKind"
    HOLD_AREA_KIND = "HoldAreaKind"


class RequirementTopic(StrEnum):
    WELDING_REQ = "WeldingReq"
    BOLTING_REQ = "BoltingReq"
    COATING_REQ = "CoatingReq"
    FIREPROOFING_REQ = "FireproofingReq"
    INSPECTION_REQ = "InspectionReq"
    MATERIAL_REQ = "MaterialReq"
    TOLERANCE_REQ = "ToleranceReq"
    GRATING_REQ = "GratingReq"
    UNITS_REQ = "UnitsReq"
    CONNECTION_DESIGN_REQ = "ConnectionDesignReq"
    ERECTION_REQ = "ErectionReq"
    SHOP_DRAWING_REQ = "ShopDrawingReq"
    LIFTING_REQ = "LiftingReq"
    PILE_INSTALL_REQ = "PileInstallReq"
    EXISTING_STRUCTURE_REQ = "ExistingStructureReq"
    SCOPE_EXCLUSION_REQ = "ScopeExclusionReq"
    SUBMITTAL_REQ = "SubmittalReq"


class DefaultRuleKind(StrEnum):
    PERCENT_OF_YIELD_RULE = "PercentOfYieldRule"
    PERCENT_OF_SHEAR_TABLE_RULE = "PercentOfShearTableRule"
    PERCENT_OF_UDL_RULE = "PercentOfUdlRule"
    SHEAR_FROM_MOMENT_CAPACITY_UDL_RULE = "ShearFromMomentCapacityUdlRule"
    FULL_MOMENT_RULE = "FullMomentRule"
    FULL_SHEAR_RULE = "FullShearRule"
    NAMED_LIBRARY_DETAIL_RULE = "NamedLibraryDetailRule"
    CONNECTION_TYPE_BY_CONDITION_RULE = "ConnectionTypeByConditionRule"


class AnnotationOrigin(StrEnum):
    ENGINEER_ORIGIN = "EngineerOrigin"
    THIRD_PARTY_ORIGIN = "ThirdPartyOrigin"


class MarkupKind(StrEnum):
    TAKEOFF_HIGHLIGHT = "TakeoffHighlight"
    CHECKED_HIGHLIGHT = "CheckedHighlight"
    QUERY_NOTE = "QueryNote"
    REVISION_CLOUD = "RevisionCloud"
    DEMOLITION_CLOUD = "DemolitionCloud"
    HANDWRITTEN_NOTE = "HandwrittenNote"
    REVIEWER_COMMENT = "ReviewerComment"
    VENDOR_REVIEW_STAMP = "VendorReviewStamp"
    READER_HIGHLIGHT = "ReaderHighlight"
    RECEIVED_STAMP = "ReceivedStamp"
    HOLD_MARKER = "HoldMarker"
    DOCUMENT_CONTROL_STAMP = "DocumentControlStamp"
    SEALED_STAMP = "SealedStamp"
    ENGINEER_REDLINE = "EngineerRedline"
    AS_BUILT_CERTIFICATION_STAMP = "AsBuiltCertificationStamp"
    STATUS_WATERMARK = "StatusWatermark"


class ReviewOutcome(StrEnum):
    """Outcome ticked on a vendor/document review stamp."""

    RETURNED_FOR_CORRECTION = "ReturnedForCorrection"
    EXCEPTIONS_NOTED = "ExceptionsNoted"
    REVIEW_COMPLETE = "ReviewComplete"
    REVIEW_NOT_REQUIRED = "ReviewNotRequired"
    APPROVED_FOR_FABRICATION = "ApprovedForFabrication"
    NO_EXCEPTIONS_NOTED = "NoExceptionsNoted"
    REVISE_AND_RESUBMIT = "ReviseAndResubmit"
    REVIEWED_FOR_LIMITED_SCOPE = "ReviewedForLimitedScope"
    NOT_REVIEWED = "NotReviewed"


class ExtractionConfidence(StrEnum):
    VERIFIED = "Verified"
    PROBABLE = "Probable"
    UNVERIFIED = "Unverified"
