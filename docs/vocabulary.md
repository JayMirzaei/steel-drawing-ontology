# Vocabulary reference (version 1.0.6)

Generated from `ontology/core.ttl` and `ontology/shapes.ttl` by `steel-ontology docs`. Do not edit by hand.

Namespace: `https://jaymirzaei.github.io/steel-drawing-ontology/core#` (prefix `steel:`).

## Classes (59)

Classes that extracted data is written in.

| Class | Subclass of | Meaning |
| --- | --- | --- |
| `Accessory` | Element | Non-primary steel: grating, handrail, guardrail, stair, ladder, deck, kick plate. |
| `Annotation` |  | Anything drawn on the sheet that is not design geometry: a revision cloud, a reviewer's highlight, a hand note. |
| `AreaLoad` |  | A load stated per area (kPa) for a zone, not per element: snow drift, uplift zones, live load by room use. |
| `Assembly` | Element | A shippable/liftable unit made of members, plates, connections and smaller assemblies: module, skid, frame, support tower. |
| `BasePlateConnection` | Connection |  |
| `Beam` | Member |  |
| `Bearing` | Support | Truss/beam bearing (fixed, sliding, elastomeric). |
| `Brace` | Member |  |
| `BraceConnection` | Connection |  |
| `Column` | Member |  |
| `Connection` | Element | A joint between members or between a member and a support (shear, moment, brace, base plate, splice). |
| `ConstructionSequence` | Annotation | A boxed or numbered sequence on a drawing (shore, excavate, install foundations, install steel, remove old column last); order is content and may include a prohibition (do not remove the existing column before the new support is in). |
| `Deck` | Accessory |  |
| `DefaultRule` |  | A convention printed on the drawing that gives meaning to missing data, e.g. 'where no moment is shown, provide a full moment connection'. |
| `DesignParameter` |  | A named design input printed on a notes sheet: wind pressure q, snow Ss, Sa(0.2), site class, importance factor. |
| `DrawingListRow` | ScheduleRow | A row of a drawing list / master drawing list: names a sheet and its status per issue. |
| `DrawingSet` |  | A bundle of sheets issued together (one PDF or one issue of a project drawing package). |
| `Element` |  | A physical item shown or specified on the drawing. |
| `ElementRow` | ScheduleRow | A row that tabulates one tagged element (column, pile, joist ...). |
| `ElementType` |  | A reusable type printed on drawings (base plate BP3, support type 2A, pile type A): the type/instance pattern. Types are placed many times with different locations. |
| `Evidence` |  | Where a fact was read: sheet, region and how sure the reader is. Every extracted fact should point to one (evidence-first). |
| `Fastener` | Element |  |
| `Footing` | Support |  |
| `ForceRecord` |  | Design forces or loads for one element and one load case, as printed on the drawing (not computed). |
| `Girt` | Beam | Horizontal wall-framing member (cold-formed or HSS girt); is-a test: a girt is a beam that carries wall cladding load. |
| `Grating` | Accessory |  |
| `Handrail` | Accessory |  |
| `InclusionRow` |  | Which document revision a package revision includes (work package revision matrix). |
| `Joist` | Member |  |
| `JoistGirder` | Joist |  |
| `KeeperPlate` | Plate | Plate welded to a cantilever pipe support to keep the pipe in place; is-a test: a keeper plate is a plate. |
| `Ladder` | Accessory |  |
| `LiftingLug` | Plate |  |
| `Member` | Element | A linear structural member (beam, column, brace, joist, stringer, post). |
| `MomentConnection` | Connection |  |
| `Party` |  | A company or professional named on the drawing (consultant, owner, supplier, fabricator, architect). |
| `Pile` | Support |  |
| `Plate` | Element |  |
| `Post` | Member |  |
| `RequirementClause` |  | One numbered clause of a notes sheet, standard or work package (e.g. 'minimum fillet weld 1/4 in', '100% UT on member splices'). Applies by reference to every element of the stated kind in the set. |
| `Revision` |  | One entry in a sheet's revision/issue table. |
| `SafetyGate` | Accessory |  |
| `Schedule` |  | A table on a sheet (column, pile, baseplate, member forces, lap splice, plate quantity ...). |
| `ScheduleCell` |  |  |
| `ScheduleRow` |  | One row of a schedule. |
| `ScopeItem` |  | One lettered or numbered scope-of-work item (an item code with its text, such as supply and install piles) on a scope plan or scope table; tells the fabricator what is theirs. |
| `SelectionRow` |  |  |
| `SelectionTable` |  | A reusable lookup table printed on a standard drawing: key range -> values. |
| `ShearConnection` | Connection |  |
| `Sheet` |  | One drawing sheet (page) with its own sheet number and title block. |
| `Stair` | Accessory |  |
| `Standard` |  | A code or specification cited (CSA, ASTM, building code, owner standard). |
| `StandardDocument` |  | An owner or firm standard reproduced or cited by a set, with its revision (a standard-notes sheet reproduced across projects). |
| `Stringer` | Member |  |
| `Support` | Element | Foundation or existing structure that carries the steel (pile, footing, pedestal, existing wall or column). |
| `Truss` | Assembly |  |
| `View` |  | A drawn region on a sheet: plan, elevation, section, detail, 3D view, schedule area, notes block. |
| `WorkPoint` |  | Survey control or work point with coordinates and elevation (work point tables, pile coordinates). |
| `Zone` |  | A region of a building or plant that carries its own data: area loads, repair type, status, or a column set. |

## Properties (230)

A functional property takes one value per object. Values are stored as printed.

| Property | Kind | Domain | Range | Meaning |
| --- | --- | --- | --- | --- |
| `annotates` | object | Annotation | Element |  |
| `annotationOrigin` | object, functional | Annotation | AnnotationOrigin |  |
| `annotationText` | datatype | Annotation | xsd:string | Wording of the note, stamp or markup as written on the sheet. |
| `appliesAtElevationText` | datatype | RequirementClause | xsd:string | Clause applies only at a stated top-of-steel elevation. |
| `appliesForPurpose` | object | DefaultRule | IssuePurpose | Rule applies only for this issue purpose (bidding/pricing default that is replaced at design). |
| `appliesToKindText` | datatype | RequirementClause | xsd:string | Element kind or condition it applies to (fillet weld, member splice, HSS end, lifting lug ...). |
| `appliesToProperty` | datatype | DefaultRule | xsd:string |  |
| `areaLoadFactored` | datatype, functional | AreaLoad | xsd:boolean |  |
| `areaLoadKPa` | datatype, functional | AreaLoad | xsd:decimal | The area load in kPa. A load printed in psf is converted (1 psf = 0.04788 kPa); the printed figure stays in the drawing, cited by the evidence. |
| `areaLoadType` | object | AreaLoad | LoadType |  |
| `assemblyCount` | datatype, functional | Schedule | xsd:integer | Number of assemblies the quantities of a bill of materials cover (the quantities shown are for a stated number of assemblies). |
| `assemblyWeightTonnes` | datatype, functional | Assembly | xsd:decimal |  |
| `authoredBy` | object | DrawingSet | Party |  |
| `authorRole` | object | DrawingSet or Sheet | AuthorRole | Not functional: one PDF can be a package whose sheets have different authors (an owner drawing list, engineer sheets, a vendor drawing), so the domain is the union of set and sheet. |
| `axialValue` | datatype, functional | ForceRecord | xsd:decimal | Axial force as printed, in forceUnit. |
| `baseplateTypeText` | datatype | Element | xsd:string | Base plate type letter carried inside a composite column tag (C1-C = column C-1 on base plate type C). |
| `calloutTargetSheetText` | datatype | View | xsd:string | Target sheet number printed in a detail bubble (for example S-301). |
| `calloutTo` | object | View | View | A section/detail marker in one view pointing to another view (possibly on another sheet). |
| `camberMm` | datatype | Beam or Joist or Truss | xsd:decimal | Camber in millimetres; beams, joists and trusses are cambered. |
| `camberPercentDeadLoad` | datatype, functional | Joist | xsd:decimal |  |
| `capacityTonnes` | datatype, functional | LiftingLug | xsd:decimal |  |
| `catalogueText` | datatype | Accessory or Plate or Fastener | xsd:string | Supplier catalogue reference printed on the drawing (grating by catalogue name, a post-base catalogue number). |
| `cellText` | datatype | ScheduleCell | xsd:string | The cell exactly as printed; never silently parsed. |
| `cellUnitText` | datatype | ScheduleCell | xsd:string | Unit of THIS column (units can differ per column in one table: kN beside ft-lbs, mm beside in). |
| `cellValueKind` | object | ScheduleCell | CellValueKind |  |
| `changeReason` | object | Revision | ChangeReason |  |
| `citesStandard` | object |  | Standard |  |
| `citesStandardNotes` | object | Sheet or DrawingSet | StandardDocument | The set refers to an owner standard-notes sheet instead of reproducing it; its clauses apply by reference. |
| `clauseNumber` | datatype | RequirementClause | xsd:string |  |
| `clauseText` | datatype | RequirementClause | xsd:string |  |
| `clauseValue` | datatype | RequirementClause | xsd:string | The value as printed (with unit), e.g. '1/4 in', '100%', '2 in'. |
| `coatingCodeText` | datatype | RequirementClause | xsd:string | Colour or coating code printed in a coating clause (a federal-standard colour number, an owner colour code). |
| `cogX` | datatype, functional | Assembly | xsd:decimal |  |
| `cogY` | datatype, functional | Assembly | xsd:decimal |  |
| `cogZ` | datatype, functional | Assembly | xsd:decimal |  |
| `columnHeaderText` | datatype | ScheduleCell | xsd:string |  |
| `componentValue` | datatype | ScheduleRow | xsd:decimal | One printed component of a row total (friction capacity, end bearing). |
| `compressionPositive` | datatype, functional | ForceRecord | xsd:boolean | Sign convention of the axial value as stated on the sheet (Fx + = compression in one set, tension in others). |
| `compressionValue` | datatype, functional | ForceRecord | xsd:decimal | Compression force as printed, in forceUnit. |
| `confidence` | object, functional | Evidence | ExtractionConfidence |  |
| `connects` | object | Connection | Element |  |
| `consequenceText` | datatype | RequirementClause | xsd:string | What happens if the clause is not met (shop drawings are rejected without a sealed letter). |
| `consultant` | object | Sheet | Party |  |
| `consultantSheetNumber` | datatype | Sheet | xsd:string | The engineering firm's own sheet number when the owner's drawing number is the one in the title block. |
| `cutLengthMm` | datatype, functional | Element | xsd:decimal |  |
| `datumNote` | datatype | DrawingSet | xsd:string | Printed datum statement: which drawing elevation equals which surveyed (geodetic) elevation. |
| `declaredTotal` | datatype, functional | Schedule | xsd:decimal | Total printed under a schedule (total approximate weight). |
| `defaultPercent` | datatype | DefaultRule | xsd:decimal | Percentage printed in the rule (30, 50, 60, 100) where one exists. |
| `defaultRuleKind` | object | DefaultRule | DefaultRuleKind |  |
| `defaultRuleText` | datatype | DefaultRule | xsd:string |  |
| `defaultValueText` | datatype | DefaultRule | xsd:string |  |
| `deflectionLimitText` | datatype | Joist | xsd:string | L/240, L/360, L/720 as printed. |
| `depthMm` | datatype | Joist | xsd:decimal |  |
| `derivedFromRaster` | datatype, functional | Sheet | xsd:boolean | Sheet states it was created from raster images and may be inaccurate. |
| `describesElement` | object | ElementRow | Element | Schedule row -> the element it tabulates (tag-based). |
| `designEmbedmentM` | datatype, functional | Pile | xsd:decimal |  |
| `drawingNumberSegmentsText` | datatype | Sheet | xsd:string | Owner drawing number split into its named segments (plant unit, originator, group, type, serial, sheet, revision) as printed. |
| `driveEnergyJ` | datatype, functional | Pile | xsd:decimal |  |
| `easting` | datatype, functional | Support or WorkPoint or Assembly | xsd:decimal |  |
| `eastingText` | datatype | Support or WorkPoint or Assembly | xsd:string |  |
| `elementStatus` | object | Element | ElementStatus |  |
| `elevationKind` | datatype | Element | xsd:string | What the elevation means: TOS, U/S base plate, T/pile cap, cutoff. |
| `elevationM` | datatype | Support or WorkPoint or Element | xsd:decimal | Top of steel / top of cap / finished grade elevation in metres (converted when the sheet prints feet and inches). |
| `embedmentRuleText` | datatype | Pile | xsd:string |  |
| `enlargementOf` | object | Sheet | Sheet | An enlarged-plan sheet (S-201B) of an overall sheet (S-201A). |
| `evidencedBy` | object |  | Evidence | Applies to ForceRecord, ScheduleRow, Element, Annotation, Revision: any extracted fact. |
| `existingMarkerText` | datatype | Element | xsd:string | Printed marker of existing work: [E], EXIST., (REF). |
| `exposureClass` | object | Element | ExposureClass | Architecturally exposed structural steel has stricter fabrication and finish rules (cost driver). |
| `extraPointLoadKN` | datatype, functional | Joist | xsd:decimal |  |
| `fabricatorJobNumber` | datatype | DrawingSet | xsd:string | Number the fabricator stamps on every page (the job number of the file); a file property, not design content. |
| `forceGroup` | datatype | ForceRecord | xsd:string | Groups the components (F1,F2,F3) of one reaction row. |
| `forceUnit` | datatype, functional | ForceRecord | xsd:string | Unit of the force values of this record (axial, compression, tension, shear) exactly as printed: kN, kip, lbf. The values are not converted. |
| `gridLocationText` | datatype | Element | xsd:string | Grid intersection or grid line where the element sits, as printed (A/1, B/2-3); one value per place, because one mark is placed many times. |
| `handednessText` | datatype | Member | xsd:string | AS SHOWN / OPPOSITE HAND quantities on a cut list. |
| `hasAnnotation` | object | Sheet | Annotation |  |
| `hasAreaLoad` | object | Zone | AreaLoad |  |
| `hasCell` | object | ScheduleRow | ScheduleCell |  |
| `hasConstructionSequence` | object | Sheet or View | ConstructionSequence |  |
| `hasDefaultRule` | object | Sheet or DrawingSet | DefaultRule |  |
| `hasDesignParameter` | object | Sheet or DrawingSet | DesignParameter |  |
| `hasForceRecord` | object | Element | ForceRecord |  |
| `hasPart` | object | Assembly | Element | Anything an assembly is made of: members, plates, lugs, connections and smaller assemblies (a skid holds a sub-frame). |
| `hasRequirement` | object | Sheet or DrawingSet | RequirementClause |  |
| `hasRevision` | object | Sheet | Revision |  |
| `hasRow` | object | Schedule | ScheduleRow |  |
| `hasSchedule` | object | Sheet | Schedule |  |
| `hasScopeItem` | object | Sheet or DrawingSet | ScopeItem |  |
| `hasSelectionRow` | object | SelectionTable | SelectionRow |  |
| `hasSheet` | object | DrawingSet | Sheet |  |
| `hasStatusStamp` | object | Sheet | IssuePurpose | Stamp printed on the sheet (FOR REFERENCE ONLY, FOR INFORMATION ONLY ...), distinct from the revision table. |
| `hasType` | object | Element | ElementType |  |
| `hasView` | object | Sheet | View |  |
| `heatNumber` | datatype | Element | xsd:string | Mill heat number printed on shop cut lists (traceability). |
| `holdCondition` | datatype | Annotation | xsd:string | Condition under which a hold applies (e.g. soil differs from design assumption). |
| `holdListIsExplicitlyEmpty` | datatype, functional | Schedule | xsd:boolean | An empty HOLD table printed on the sheet means no holds (closed-world reading of a table that exists). |
| `holdsZone` | object | Annotation | Zone | A HOLD that applies to a region of a sheet, not the whole sheet. |
| `includedRevisionCode` | datatype | InclusionRow | xsd:string |  |
| `includesSheet` | object | InclusionRow | Sheet |  |
| `inDomain` | object | DrawingSet | Domain |  |
| `inPackageRevision` | object | InclusionRow | Revision |  |
| `installationConstraintText` | datatype | Element or Annotation | xsd:string | How the work must be done, as printed: shoring before welding, a weld sequence, a time limit. |
| `inZone` | object | Element | Zone |  |
| `isAbandoned` | datatype, functional | Element | xsd:boolean | Existing item left in place and not used (abandoned pile); not demolished, not carrying load. |
| `isDefaultRuleClause` | datatype, functional | RequirementClause | xsd:boolean | True when the clause also defines what absence means (see DefaultRule). |
| `isDesignOpen` | datatype, functional | Element | xsd:boolean | The drawing says this connection or item will be designed later. |
| `isFactored` | datatype, functional | ForceRecord | xsd:boolean | Schedules print either factored or unfactored loads; recording which is essential. |
| `isGuideOnly` | datatype, functional | View or Schedule or Element | xsd:boolean | Shown as a guide only; another document governs (embeds shown as guide only, dimensions not for fabrication). |
| `isInformationOnly` | datatype, functional | Schedule | xsd:boolean | The table says it is for information only (material take-off list on a design sheet): the fabricator builds their own bill of materials. |
| `isProhibition` | datatype, functional | RequirementClause | xsd:boolean | Clause forbids something (do not field burn holes, do not paint, do not oversize holes). |
| `isSealed` | datatype, functional | Sheet | xsd:boolean | Sheet bears a professional engineer's seal. A sheet number prefix S does not imply a seal or an engineer of record. |
| `isSheetOf` | object |  |  |  |
| `isShippedLoose` | datatype, functional | Element | xsd:boolean | Shipped loose / by others / stick built rather than inside a module. |
| `isStickBuilt` | datatype, functional | Element | xsd:boolean | Built piece by piece in the field, not part of a shop-built module. |
| `issuePurpose` | object | Revision | IssuePurpose |  |
| `issueScope` | object | Revision | Discipline | One sheet can have separate issue tracks per trade (foundation permit / steel tender / timber tender). |
| `issueScopeText` | datatype | DrawingSet or Revision | xsd:string | Which work package or area an issue covers (a named work package; foundations and steel pricing). |
| `isTBD` | datatype, functional | Annotation or Element or View | xsd:boolean | Reference or detail printed as TBD / to be determined: an open item, not data. |
| `isTemplateChoiceUnresolved` | datatype, functional | RequirementClause | xsd:boolean | Bracketed [A] [B] choice or a [jurisdiction] placeholder left unselected in a template clause. |
| `isTemporary` | datatype, functional | Element | xsd:boolean | Temporary support or bracing shown on the drawing (to be removed). |
| `isTenderOnly` | datatype, functional | ScheduleCell or ScheduleRow | xsd:boolean | Value is for tender only (pile length); the actual value is set later by someone else. |
| `isTransportBeam` | datatype, functional | Beam | xsd:boolean | Beam marked to sit on the trailer or skid during transport; may carry its own no-projection rules. |
| `isTypical` | datatype, functional | View | xsd:boolean | True for typical details referenced from many places. |
| `isViewOn` | object |  |  |  |
| `isVoided` | datatype, functional | View or Annotation | xsd:boolean | A view stamped NOT USED, or a stamp crossed out (superseded stamp on a re-issued sheet). |
| `isVoidedRow` | datatype, functional | ScheduleRow | xsd:boolean | Row marked NOT USED. |
| `leadTimeText` | datatype | Sheet | xsd:string | Delivery lead time printed on a transmittal ('3 weeks after approval'). |
| `legacySheetNote` | datatype | DrawingListRow | xsd:string | Per-row tag showing the sheet was inherited from another author or earlier project (BY <firm>, FOR REFERENCE ONLY, REMOVED). |
| `libraryDetailRefText` | datatype | DefaultRule | xsd:string | Named library detail or standard drawing the rule points to, with its revision as printed. |
| `libraryDrawingNumber` | datatype | ScheduleRow | xsd:string | Standard/library drawing cited by a row (not part of this set). |
| `libraryDrawingRev` | datatype | ScheduleRow | xsd:string |  |
| `limitsDesignResponsibility` | datatype, functional | Annotation | xsd:boolean | True when the sheet states the engineer is responsible only for what is inside this (revision cloud) boundary; content outside the cloud is not the engineer's to confirm. |
| `listsSheet` | object | DrawingListRow | Sheet |  |
| `loadCase` | datatype | ForceRecord | xsd:string |  |
| `loadDirection` | object | ForceRecord | LoadDirection |  |
| `loadType` | object | ForceRecord | LoadType | Controlled type; loadCase stays as the printed label. |
| `markClassText` | datatype | Element | xsd:string | Class of a piece mark taken from its prefix (a angle, c channel, p plate, w wide flange). |
| `markupKind` | object | Annotation | MarkupKind |  |
| `markupMeaningText` | datatype | Annotation | xsd:string | What the markup colour means for this fabricator (one colour for taken off, another for checked, a third for a query); meaning differs between fabricators. |
| `materialText` | datatype | Member | xsd:string | steel, LSL timber, concrete ... for discipline filtering. |
| `maxLateralDisplacementMm` | datatype, functional | Pile | xsd:decimal |  |
| `minTorqueFtLbs` | datatype, functional | Pile | xsd:decimal |  |
| `momentMajorValue` | datatype, functional | ForceRecord | xsd:decimal | Moment about the major axis as printed, in momentUnit. |
| `momentMinorValue` | datatype, functional | ForceRecord | xsd:decimal | Moment about the minor axis as printed, in momentUnit. |
| `momentUnit` | datatype, functional | ForceRecord | xsd:string | Unit of the moment and torsion values of this record exactly as printed: kN.m, kip.ft, ft-kip. The values are not converted. |
| `needsFieldConfirm` | datatype, functional | Element or View | xsd:boolean | Dimension/elevation marked (FIELD VERIFY), V, or 'to be confirmed': do not fabricate before confirming. |
| `northing` | datatype, functional | Support or WorkPoint or Assembly | xsd:decimal |  |
| `northingText` | datatype | Support or WorkPoint or Assembly | xsd:string | As printed, including station (chainage) notation. |
| `noticeHours` | datatype, functional | RequirementClause | xsd:integer | Advance notice before a review or inspection (24, 48, 96 hours). |
| `numberingScheme` | datatype | DrawingSet | xsd:string | How the owner encodes unit/type/serial/sheet/rev in drawing numbers (a decode aid). |
| `onSheet` | object, functional | Evidence | Sheet |  |
| `ownedBy` | object | DrawingSet | Party |  |
| `pageIndex` | datatype, functional | Sheet | xsd:integer |  |
| `parameterName` | datatype | DesignParameter | xsd:string |  |
| `parameterUnitText` | datatype | DesignParameter | xsd:string |  |
| `parameterValueText` | datatype | DesignParameter | xsd:string |  |
| `partOfAssembly` | object |  |  |  |
| `partyRoleText` | datatype | Party | xsd:string | structural, architectural, mechanical, ... as printed. |
| `pricingColumns` | datatype, functional | Sheet | xsd:boolean | Sheet carries credit/extra price columns (change notices): commercial, not design content. |
| `productLineText` | datatype | Joist | xsd:string | Supplier product line named in notes (a proprietary composite joist series). |
| `projectNumber` | datatype | Sheet or DrawingSet | xsd:string | Per-sheet because multi-discipline packages carry different project numbers per discipline. |
| `qtyPerAssembly` | datatype, functional | Element | xsd:integer |  |
| `refersToDocument` | object | Sheet | Sheet | Change notice or instruction pointing at the sheets/documents it changes. |
| `regionBox` | datatype | Evidence | xsd:string | Normalised x0,y0,x1,y1 on the page. |
| `reinforces` | object | Element | Element | New member that strengthens an existing one (added web angle, chord rod, chord plate). |
| `reproducesStandard` | object | Sheet or DrawingSet | StandardDocument |  |
| `requiredQuantity` | datatype, functional | Element | xsd:integer | Quantity stated on the drawing ('12 required', 'ONE REQ'D'). |
| `requirementTopic` | object | RequirementClause | RequirementTopic |  |
| `requiresSealedDesign` | datatype, functional | Element | xsd:boolean | Fabricator-designed item whose calculations must be sealed by a registered engineer. |
| `responsibility` | object | Element | ResponsibilityTag | Scope split printed on the drawing ('joists by supplier' notes, 'connection to be designed by the fabricator's connection engineer'). |
| `responsiblePackage` | object | Element | DrawingSet | Another work package that does this work, when the drawing says the work is 'by' a named package. |
| `reviewOutcome` | object | Annotation | ReviewOutcome |  |
| `reviewScopeText` | datatype | DrawingSet | xsd:string | Clause limiting what the engineer's shop-drawing review covers. |
| `revisedInThisIssue` | datatype, functional | Element or ScheduleRow | xsd:boolean | Inside the latest revision cloud (changed row or element). |
| `revisionCode` | datatype | Revision | xsd:string |  |
| `revisionCodeScheme` | datatype | DrawingSet | xsd:string | How revision codes are built in this set (letters before permit then numbers; number.letter; a numbered issue series per purpose). |
| `revisionDate` | datatype | Revision | xsd:string | Date exactly as printed: formats differ (2021.03.07, 07/03/21, March 7 2021). xsd:date is not in the OWL 2 datatype map, and silent parsing of ambiguous formats is a risk. |
| `rowKeyText` | datatype | SelectionRow | xsd:string |  |
| `rowRefersToSheet` | object | ScheduleRow | Sheet | Detail or location sheet that a schedule row points to. |
| `rowTotal` | datatype, functional | ScheduleRow | xsd:decimal | Total printed on the row; checked against the sum of its components. |
| `rowValue` | datatype, functional | ScheduleRow | xsd:decimal | The additive value of the row that the schedule total sums (line weight). |
| `rowValuesText` | datatype | SelectionRow | xsd:string |  |
| `scaleText` | datatype | View | xsd:string |  |
| `scheduleKind` | object | Schedule | ScheduleKind |  |
| `scopeItemId` | datatype | ScopeItem | xsd:string |  |
| `scopeItemText` | datatype | ScopeItem | xsd:string |  |
| `scopeItemWork` | object, functional | ScopeItem | WorkKind |  |
| `sealJurisdictionText` | datatype | Sheet or Annotation | xsd:string | Licensing body printed on the seal (a seal from another jurisdiction on a local project). |
| `sealScopeText` | datatype | Sheet or Annotation | xsd:string | Statement that the seal or design responsibility covers only part of the sheet (e.g. only the clouded revision). |
| `sectionText` | datatype | Member or Plate | xsd:string | Printed profile or plate designation, e.g. W200x46 or PL10x200; stored as text because notations differ by region. |
| `selectionTableOf` | object | SelectionTable | Sheet |  |
| `sequenceStepText` | datatype | ConstructionSequence | xsd:string | One step as printed; keep the printed number in the text. |
| `shearMajorValue` | datatype, functional | ForceRecord | xsd:decimal | Shear about the major axis as printed, in forceUnit. |
| `shearMinorValue` | datatype, functional | ForceRecord | xsd:decimal | Shear about the minor axis as printed, in forceUnit. |
| `sheetDiscipline` | object | Sheet | Discipline |  |
| `sheetKind` | object | Sheet | SheetKind |  |
| `sheetNumber` | datatype, functional | Sheet | xsd:string |  |
| `sheetTitle` | datatype, functional | Sheet | xsd:string |  |
| `sheetTotal` | datatype, functional | Sheet | xsd:integer | N in 'sheet n of N': lets extraction check completeness. |
| `showsElement` | object | View | Element |  |
| `stageRevisionText` | datatype | DrawingListRow | xsd:string | Revision of the listed sheet at one submission stage, as printed per stage column (60% rev A, 90% rev B, IFC rev 0). |
| `stampDate` | datatype | Annotation | xsd:string |  |
| `standardDesignation` | datatype, functional | Standard | xsd:string | Designation of the cited code or specification as printed (CSA W59, ASTM F3125). |
| `standardRevisionText` | datatype | StandardDocument | xsd:string | Revision of the standard as printed (revisions per standard can differ between projects). |
| `standardTitleText` | datatype | StandardDocument | xsd:string |  |
| `statusWatermarkText` | datatype | Sheet | xsd:string | Diagonal or margin watermark as printed (FOR INFORMATION ONLY, PRELIMINARY NOT FOR CONSTRUCTION). |
| `studCount` | datatype | Beam or Joist | xsd:integer | Number of shear studs on a composite beam or joist. |
| `submissionStage` | object | Revision | SubmissionStage |  |
| `supportedBy` | object |  |  |  |
| `supports` | object | Element | Element |  |
| `symmetricTensionCompression` | datatype, functional | ForceRecord | xsd:boolean | Printed as 'Tf/Cf = 300 kN': one value for both. |
| `tableTitle` | datatype | SelectionTable | xsd:string |  |
| `tag` | datatype | Element | xsd:string | Mark printed on the drawing (C12, B4, BP3). |
| `tagPrefix` | datatype | ElementType | xsd:string | P-, BM, C: the prefix tells which family a tag belongs to. |
| `tensionValue` | datatype, functional | ForceRecord | xsd:decimal | Tension force as printed, in forceUnit. |
| `titleBlockStatus` | object | Sheet | IssuePurpose | Status FIELD printed in the title block; can disagree with the revision table (AS BUILT on an IFC sheet): flag, do not resolve silently. |
| `topOfSteelOffsetMm` | datatype, functional | Member | xsd:decimal | Offset in brackets after the size, e.g. W250x49 (+500). |
| `torsionValue` | datatype, functional | ForceRecord | xsd:decimal | Torsion as printed, in momentUnit. |
| `transmittalNumber` | datatype | DrawingSet | xsd:string |  |
| `typeTag` | datatype | ElementType | xsd:string |  |
| `unitConflictText` | datatype | Sheet | xsd:string | A note states one unit system while the printed values use another (a note says metres, the elevations are printed in feet-inches); record both, do not resolve. |
| `unitSystem` | object | DrawingSet | UnitSystem |  |
| `verbalInstructionNote` | datatype | Annotation | xsd:string | Dated note recording a phone/verbal instruction written on the sheet (source and date as printed). |
| `viewCode` | datatype | View | xsd:string | Code of a typical detail (such as D12 or SD-04) used by callouts; typical details are a reusable library. |
| `viewKind` | object | View | ViewKind |  |
| `weightText` | datatype | Assembly | xsd:string | Weight exactly as printed with its unit (kg, tonnes, lbs). |
| `weldPattern` | datatype | Connection | xsd:string | As printed: a fillet size alone, or size with length and pitch for an intermittent weld. |
| `workKind` | object | Element | WorkKind |  |
| `zoneKind` | object | Zone | ZoneKind |  |
| `zoneOnSheet` | object | Zone | Sheet |  |
| `zoneStatus` | object | Zone | ElementStatus |  |

## Closed vocabularies (24)

Each is a fixed list (owl:oneOf, all members different). A value outside the list is a validation error.

| Vocabulary | Members | Meaning |
| --- | --- | --- |
| `AnnotationOrigin` | EngineerOrigin, ThirdPartyOrigin |  |
| `AuthorRole` | EngineerOfRecordRole, SupplierDesignRole, FabricatorShopRole, OwnerStandardRole, FieldPackageRole, ArchitectRole, DetailerRole |  |
| `CellValueKind` | NumberCell, TextCell, BySupplierCell, NotApplicableCell, SeeNoteCell, BlankCell, LibraryRefCell |  |
| `ChangeReason` | ScopeChange, HoldsRemoved, VendorDocumentUpdate, ExecutionStrategyChange, ConstructionRequest, DesignChange, RegulatoryUpdate, DocumentCorrection, ClientRequest, CoordinationChange | Why a revision was made (owner change-reason codes and common free-text reasons). |
| `DefaultRuleKind` | PercentOfYieldRule, PercentOfShearTableRule, PercentOfUdlRule, ShearFromMomentCapacityUdlRule, FullMomentRule, FullShearRule, NamedLibraryDetailRule, ConnectionTypeByConditionRule |  |
| `Discipline` | SteelDiscipline, ConcreteDiscipline, MasonryDiscipline, TimberDiscipline, ArchitecturalDiscipline, PipingDiscipline, CivilDiscipline, MechanicalElectricalDiscipline | Trade/discipline a sheet or view belongs to; a folder of structural drawings can still contain non-structural sheets. |
| `Domain` | BuildingDomain, IndustrialSkidDomain, PlatformStairDomain, ParkingStructureDomain, ResidentialModularDomain, FieldRepairDomain, PrecastBuildingDomain |  |
| `ElementStatus` | NewWork, ExistingToRemain, ExistingToDemolish, ExistingToBeModified, FutureProvision | Whether the element is new, existing, to be removed, or future (separate from who designs it). |
| `ExposureClass` | AESS, StandardExposure |  |
| `ExtractionConfidence` | Verified, Probable, Unverified |  |
| `IssuePurpose` | IssuedForConstruction, IssuedForReview, IssuedForTender, IssuedForBid, IssuedForPricing, IssuedForPermit, Preliminary, ControlledRelease, AsBuilt, ForReferenceOnly, ForInformationOnly, ForImplementation, IssuedForErection, IssuedForApproval, IssuedForCoordination, NonPublished, UncontrolledIfPrinted, IssuedForDesign |  |
| `LoadDirection` | Vertical, HorizontalNS, HorizontalEW, HorizontalGeneral, UpliftDirection, AlongMemberAxis |  |
| `LoadType` | DeadLoad, LiveLoad, SnowLoad, WindLoad, SeismicLoad, OtherLoad, TotalLoad, LoadCombination, BlastLoad, PondingLoad |  |
| `MarkupKind` | TakeoffHighlight, CheckedHighlight, QueryNote, RevisionCloud, DemolitionCloud, HandwrittenNote, ReviewerComment, VendorReviewStamp, ReaderHighlight, ReceivedStamp, HoldMarker, DocumentControlStamp, SealedStamp, EngineerRedline, AsBuiltCertificationStamp, StatusWatermark |  |
| `RequirementTopic` | WeldingReq, BoltingReq, CoatingReq, FireproofingReq, InspectionReq, MaterialReq, ToleranceReq, GratingReq, UnitsReq, ConnectionDesignReq, ErectionReq, ShopDrawingReq, LiftingReq, PileInstallReq, ExistingStructureReq, ScopeExclusionReq, SubmittalReq |  |
| `ResponsibilityTag` | ByEngineerOfRecord, ByConnectionEngineer, ByFabricator, BySupplier, ByOthers, ByOwner | Who must design, supply or detail an element as stated on the drawing. |
| `ReviewOutcome` | ReturnedForCorrection, ExceptionsNoted, ReviewComplete, ReviewNotRequired, ApprovedForFabrication, NoExceptionsNoted, ReviseAndResubmit, ReviewedForLimitedScope, NotReviewed | Outcome ticked on a vendor/document review stamp. |
| `ScheduleKind` | ColumnSchedule, BeamSchedule, PileSchedule, FootingSchedule, BasePlateSchedule, MemberForceSchedule, ConnectionForceSchedule, JoistSchedule, DeckSchedule, OpeningSchedule, PlateQuantitySchedule, WallSchedule, DrawingListSchedule, BillOfMaterialSchedule, HoldListSchedule, CutListSchedule, OtherSchedule |  |
| `SheetKind` | GeneralNotesSheet, SpecificationSheet, CoverSheet, IndexSheet, PlanSheet, ElevationSheet, SectionSheet, DetailSheet, ScheduleSheet, ThreeDSheet, TypicalDetailsSheet, IssueRecordSheet, ScopeSheet, PhotoSheet, HandSketchSheet, PipingIsometricSheet, StandardSheet, BlankSheet, WorkPackageSheet, ChangeNoticeSheet, ManualSheet, TransmittalSheet, ReactionSheet, AnchorBoltPlanSheet, FrameCrossSectionSheet, ConsultantListSheet |  |
| `SubmissionStage` | PreliminaryReviewStage, Review60Stage, Review90Stage, BidStage, BidAddendumStage, ConstructionIssueStage, Review50Stage, Review95Stage, Review100Stage | Stage of the owner's review cycle recorded on an issue record (finer than issue purpose). |
| `UnitSystem` | Metric, Imperial, MixedUnits, DualUnits |  |
| `ViewKind` | PlanView, ElevationView, SectionView, DetailView, ThreeDView, PhotoView, KeyPlanView, IsometricView, ScheduleView, NotesView |  |
| `WorkKind` | SupplyOnly, FabricateOnly, InstallOnly, SupplyAndInstall, FieldWeldOnly, ShipLoose |  |
| `ZoneKind` | LoadZoneKind, RepairZoneKind, PlantAreaKind, BuildingSegmentKind, FutureAreaKind, HoldAreaKind |  |

## Reasoner-defined classes (25)

Membership is inferred from the definition, never written by an extractor.

| Class | Definition | Why it exists |
| --- | --- | --- |
| `CommercialSheet` | Sheet and (pricingColumns value true) | Change/price sheets: keep out of take-off; link revised design sheets through revisions. |
| `ConnectionToBeDesignedByOthers` | Connection and (responsibility value ByConnectionEngineer) | A connection the fabricator is told another party will design: needs a hold-point before detailing. |
| `ExistingElement` | Element and (elementStatus value ExistingToRemain) or (elementStatus value ExistingToDemolish) or (elementStatus value ExistingToBeModified) | Elements that exist already, whether they remain, are demolished or are modified: not new steel to fabricate. |
| `ExplicitNoHolds` | Schedule and (holdListIsExplicitlyEmpty value true) |  |
| `ExposedSteelElement` | Element and (exposureClass value AESS) |  |
| `FabricatorDesignedSealed` | Element and (responsibility value ByFabricator) and (requiresSealedDesign value true) |  |
| `MarkedUpSet` | DrawingSet and (hasSheet some MarkedUpSheet) |  |
| `MarkedUpSheet` | Sheet and (hasAnnotation some ThirdPartyMarkup) | A sheet that carries third-party markup and therefore needs content/markup separation when read. |
| `ModuleWithWeight` | Assembly and (assemblyWeightTonnes some xsd:decimal) | Assemblies whose drawing states a weight: needed for lifting and shipping decisions. |
| `ProhibitionClause` | RequirementClause and (isProhibition value true) | Clauses that forbid an action; an agent must check them before suggesting a fabrication change. |
| `ReferenceOnlySheet` | Sheet and (hasStatusStamp value ForReferenceOnly) | Sheet stamped FOR REFERENCE ONLY: do not take off or fabricate from it. |
| `ReinforcementMember` | Element and (reinforces some Element) | Members that strengthen an existing member; take-off must not count them as new primary steel. |
| `ResponsibilityBoundary` | Annotation and (limitsDesignResponsibility value true) | A cloud/boundary that limits the engineer's design responsibility: take-off outside it must be confirmed against earlier issues. |
| `ReviewedVendorSheet` | Sheet and (hasAnnotation some (markupKind value VendorReviewStamp)) | Vendor drawing carrying a review stamp: read the stamp outcome before relying on the content. |
| `RowWithForces` | ElementRow and (describesElement some (hasForceRecord some ForceRecord)) | Rows whose element has force records: the data that drives connection design. |
| `ShopReadySet` | DrawingSet and (authorRole value FabricatorShopRole) |  |
| `SteelRelevantSheet` | Sheet and (sheetDiscipline value SteelDiscipline) | Sheet with steel content. Under the open world a sheet is only classified here when steel is asserted; absence is unknown. |
| `SupplierDesignedSet` | DrawingSet and (authorRole value SupplierDesignRole) |  |
| `SupplierValueCell` | ScheduleCell and (cellValueKind value BySupplierCell) | Schedule cells that say BY SUPPLIER: the value is someone else's responsibility, not missing data. |
| `TemporaryElement` | Element and (isTemporary value true) | Temporary items; excluded from permanent steel take-off. |
| `ThirdPartyMarkup` | Annotation and (annotationOrigin value ThirdPartyOrigin) | Reviewer/fabricator markup, not design content (take-off highlights, check marks, query notes). |
| `UnconfirmedElement` | Element and (needsFieldConfirm value true) | Elements with dimensions or elevations to be field-confirmed before fabrication. |
| `UntrustedRasterSheet` | Sheet and (derivedFromRaster value true) | Sheets that warn of raster origin: treat extracted values from them as Probable at best. |
| `UnverifiedForceRecord` | ForceRecord and (evidencedBy some (confidence value Unverified)) | Force records whose evidence is only unverified: needs human check before use. |
| `VoidedView` | View and (isVoided value true) | Detail stamped NOT USED: exclude from take-off. |

## Shapes (60)

SHACL checks. A violation makes data non-conforming; a warning asks a person to look.

| Shape | Applies to | Severity | Check | Message |
| --- | --- | --- | --- | --- |
| `AnnotationOriginValuesShape` | anything with annotationOrigin | Violation | annotationOrigin: one of EngineerOrigin, ThirdPartyOrigin | annotationOrigin must be a member of the closed vocabulary AnnotationOrigin (see core.ttl). |
| `AnnotationShape` | every Annotation | Violation | annotationOrigin: at least 1, at most 1 | Every annotation must say whether the engineer or a third party drew it. |
| `AreaLoadShape` | every AreaLoad | Violation | areaLoadKPa: at least 1, at most 1, xsd:decimal | An area load needs exactly one value in kPa. |
| `AreaLoadShape` | every AreaLoad | Warning | areaLoadFactored: at least 1 | Area loads must say factored or unfactored. |
| `AreaLoadShape` | every AreaLoad | Warning | areaLoadType: at least 1 | Give the area load a load type (dead, live, snow ...) so loads can be compared. |
| `AssemblyShape` | every Assembly | Violation | assemblyWeightTonnes: at most 1, xsd:decimal, > 0 | An assembly weight must be one positive number (tonnes). |
| `AuthorRoleValuesShape` | anything with authorRole | Violation | authorRole: one of EngineerOfRecordRole, SupplierDesignRole, FabricatorShopRole, OwnerStandardRole, FieldPackageRole, ArchitectRole, DetailerRole | authorRole must be a member of the closed vocabulary AuthorRole (see core.ttl). |
| `CellValueKindValuesShape` | anything with cellValueKind | Violation | cellValueKind: one of NumberCell, TextCell, BySupplierCell, NotApplicableCell, SeeNoteCell, BlankCell, LibraryRefCell | cellValueKind must be a member of the closed vocabulary CellValueKind (see core.ttl). |
| `ChangeReasonValuesShape` | anything with changeReason | Violation | changeReason: one of ScopeChange, HoldsRemoved, VendorDocumentUpdate, ExecutionStrategyChange, ConstructionRequest, DesignChange, RegulatoryUpdate, DocumentCorrection, ClientRequest, CoordinationChange | changeReason must be a member of the closed vocabulary ChangeReason (see core.ttl). |
| `ClauseValueShape` | every RequirementClause | Warning | SPARQL check | A clause with a number or percentage should keep the value with its unit as printed. |
| `ConstructionSequenceShape` | every ConstructionSequence | Warning | sequenceStepText: at least 2 | A construction sequence needs at least two steps; one step is a note, not a sequence. |
| `DefaultRuleKindShape` | every DefaultRule | Violation | defaultPercent: <= 100, > 0 | A default percentage must be above 0 and at most 100. |
| `DefaultRuleKindShape` | every DefaultRule | Warning | defaultRuleKind: at least 1 | Say which kind of default this is so an agent can apply it. |
| `DefaultRuleKindValuesShape` | anything with defaultRuleKind | Violation | defaultRuleKind: one of PercentOfYieldRule, PercentOfShearTableRule, PercentOfUdlRule, ShearFromMomentCapacityUdlRule, FullMomentRule, FullShearRule, NamedLibraryDetailRule, ConnectionTypeByConditionRule | defaultRuleKind must be a member of the closed vocabulary DefaultRuleKind (see core.ttl). |
| `DefaultRuleShape` | every DefaultRule | Violation | defaultRuleText: at least 1, xsd:string | A default rule must keep its text as printed. |
| `DesignParameterShape` | every DesignParameter | Violation | parameterName: at least 1 | A design parameter must keep its printed name (q, Ss, Sa(0.2) ...). |
| `DesignParameterShape` | every DesignParameter | Violation | parameterValueText: at least 1 | A design parameter must keep its value as printed. |
| `DisciplineValuesShape` | anything with issueScope, sheetDiscipline | Violation | issueScope: one of SteelDiscipline, ConcreteDiscipline, MasonryDiscipline, TimberDiscipline, ArchitecturalDiscipline, PipingDiscipline, CivilDiscipline, MechanicalElectricalDiscipline | issueScope must be a member of the closed vocabulary Discipline (see core.ttl). |
| `DisciplineValuesShape` | anything with issueScope, sheetDiscipline | Violation | sheetDiscipline: one of SteelDiscipline, ConcreteDiscipline, MasonryDiscipline, TimberDiscipline, ArchitecturalDiscipline, PipingDiscipline, CivilDiscipline, MechanicalElectricalDiscipline | sheetDiscipline must be a member of the closed vocabulary Discipline (see core.ttl). |
| `DomainValuesShape` | anything with inDomain | Violation | inDomain: one of BuildingDomain, IndustrialSkidDomain, PlatformStairDomain, ParkingStructureDomain, ResidentialModularDomain, FieldRepairDomain, PrecastBuildingDomain | inDomain must be a member of the closed vocabulary Domain (see core.ttl). |
| `DrawingListRowShape` | every DrawingListRow | Violation | listsSheet: at least 1 | A drawing list row must name the sheet it lists. |
| `ElementRowShape` | every ElementRow | Violation | describesElement: at least 1 | An element row must name the element it tabulates. |
| `ElementStatusValuesShape` | anything with elementStatus, zoneStatus | Violation | elementStatus: one of NewWork, ExistingToRemain, ExistingToDemolish, ExistingToBeModified, FutureProvision | elementStatus must be a member of the closed vocabulary ElementStatus (see core.ttl). |
| `ElementStatusValuesShape` | anything with elementStatus, zoneStatus | Violation | zoneStatus: one of NewWork, ExistingToRemain, ExistingToDemolish, ExistingToBeModified, FutureProvision | zoneStatus must be a member of the closed vocabulary ElementStatus (see core.ttl). |
| `EvidenceShape` | every Evidence | Violation | confidence: at least 1, at most 1 | Evidence must give exactly one confidence: Verified, Probable or Unverified. |
| `EvidenceShape` | every Evidence | Violation | onSheet: at least 1, at most 1 | Evidence must name exactly one sheet it was read on. |
| `ExposureClassValuesShape` | anything with exposureClass | Violation | exposureClass: one of AESS, StandardExposure | exposureClass must be a member of the closed vocabulary ExposureClass (see core.ttl). |
| `ExtractionConfidenceValuesShape` | anything with confidence | Violation | confidence: one of Verified, Probable, Unverified | confidence must be a member of the closed vocabulary ExtractionConfidence (see core.ttl). |
| `ForceRecordShape` | every ForceRecord | Violation | isFactored: at least 1, at most 1, xsd:boolean | Loads must be tagged factored or unfactored; mixing them is a design error. |
| `ForceRecordShape` | every ForceRecord | Warning | evidencedBy: at least 1 | Every extracted force needs evidence (sheet, region, confidence). |
| `ForceRecordShape` | every ForceRecord | Warning | loadCase: at least 1, xsd:string | Keep the load case label as printed (D, L, Cf, Tf ...). |
| `ForceRecordShape` | every ForceRecord | Warning | loadType: at least 1 | Give a controlled load type (dead, live, snow, wind ...) so loads can be compared across sets. |
| `ForceUnitShape` | every ForceRecord | Warning | forceUnit: at most 1, one of kN, N, kip, lbf, kN/m, kip/ft, kPa, psf | forceUnit should be one printed force unit: kN, N, kip, lbf, kN/m, kip/ft, kPa or psf. |
| `ForceUnitShape` | every ForceRecord | Warning | momentUnit: at most 1, one of kN.m, N.m, kip.ft, ft-kip, kip.in, lbf.ft | momentUnit should be one printed moment unit: kN.m, N.m, kip.ft, ft-kip, kip.in or lbf.ft. |
| `ForceValueUnitShape` | every ForceRecord | Warning | SPARQL check | A force value (axial, compression, tension, shear) needs its printed unit in forceUnit. |
| `InclusionRowShape` | every InclusionRow | Violation | inPackageRevision: at least 1 | An inclusion row must name the package revision it belongs to. |
| `InclusionRowShape` | every InclusionRow | Violation | includesSheet: at least 1 | An inclusion row must name the sheet it includes. |
| `IssuePurposeValuesShape` | anything with appliesForPurpose, hasStatusStamp, issuePurpose, titleBlockStatus | Violation | appliesForPurpose: one of IssuedForConstruction, IssuedForReview, IssuedForTender, IssuedForBid, IssuedForPricing, IssuedForPermit, Preliminary, ControlledRelease, AsBuilt, ForReferenceOnly, ForInformationOnly, ForImplementation, IssuedForErection, IssuedForApproval, IssuedForCoordination, NonPublished, UncontrolledIfPrinted, IssuedForDesign | appliesForPurpose must be a member of the closed vocabulary IssuePurpose (see core.ttl). |
| `IssuePurposeValuesShape` | anything with appliesForPurpose, hasStatusStamp, issuePurpose, titleBlockStatus | Violation | hasStatusStamp: one of IssuedForConstruction, IssuedForReview, IssuedForTender, IssuedForBid, IssuedForPricing, IssuedForPermit, Preliminary, ControlledRelease, AsBuilt, ForReferenceOnly, ForInformationOnly, ForImplementation, IssuedForErection, IssuedForApproval, IssuedForCoordination, NonPublished, UncontrolledIfPrinted, IssuedForDesign | hasStatusStamp must be a member of the closed vocabulary IssuePurpose (see core.ttl). |
| `IssuePurposeValuesShape` | anything with appliesForPurpose, hasStatusStamp, issuePurpose, titleBlockStatus | Violation | issuePurpose: one of IssuedForConstruction, IssuedForReview, IssuedForTender, IssuedForBid, IssuedForPricing, IssuedForPermit, Preliminary, ControlledRelease, AsBuilt, ForReferenceOnly, ForInformationOnly, ForImplementation, IssuedForErection, IssuedForApproval, IssuedForCoordination, NonPublished, UncontrolledIfPrinted, IssuedForDesign | issuePurpose must be a member of the closed vocabulary IssuePurpose (see core.ttl). |
| `IssuePurposeValuesShape` | anything with appliesForPurpose, hasStatusStamp, issuePurpose, titleBlockStatus | Violation | titleBlockStatus: one of IssuedForConstruction, IssuedForReview, IssuedForTender, IssuedForBid, IssuedForPricing, IssuedForPermit, Preliminary, ControlledRelease, AsBuilt, ForReferenceOnly, ForInformationOnly, ForImplementation, IssuedForErection, IssuedForApproval, IssuedForCoordination, NonPublished, UncontrolledIfPrinted, IssuedForDesign | titleBlockStatus must be a member of the closed vocabulary IssuePurpose (see core.ttl). |
| `LiftingLugShape` | every LiftingLug | Violation | capacityTonnes: > 0 | A lifting lug capacity must be positive. |
| `LoadDirectionValuesShape` | anything with loadDirection | Violation | loadDirection: one of Vertical, HorizontalNS, HorizontalEW, HorizontalGeneral, UpliftDirection, AlongMemberAxis | loadDirection must be a member of the closed vocabulary LoadDirection (see core.ttl). |
| `LoadTypeValuesShape` | anything with areaLoadType, loadType | Violation | areaLoadType: one of DeadLoad, LiveLoad, SnowLoad, WindLoad, SeismicLoad, OtherLoad, TotalLoad, LoadCombination, BlastLoad, PondingLoad | areaLoadType must be a member of the closed vocabulary LoadType (see core.ttl). |
| `LoadTypeValuesShape` | anything with areaLoadType, loadType | Violation | loadType: one of DeadLoad, LiveLoad, SnowLoad, WindLoad, SeismicLoad, OtherLoad, TotalLoad, LoadCombination, BlastLoad, PondingLoad | loadType must be a member of the closed vocabulary LoadType (see core.ttl). |
| `MarkupKindValuesShape` | anything with markupKind | Violation | markupKind: one of TakeoffHighlight, CheckedHighlight, QueryNote, RevisionCloud, DemolitionCloud, HandwrittenNote, ReviewerComment, VendorReviewStamp, ReaderHighlight, ReceivedStamp, HoldMarker, DocumentControlStamp, SealedStamp, EngineerRedline, AsBuiltCertificationStamp, StatusWatermark | markupKind must be a member of the closed vocabulary MarkupKind (see core.ttl). |
| `MomentValueUnitShape` | every ForceRecord | Warning | SPARQL check | A moment or torsion value needs its printed unit in momentUnit. |
| `NoticeHoursShape` | every RequirementClause | Violation | noticeHours: > 0 | Notice hours must be positive. |
| `PileCriteriaShape` | every Pile | Violation | designEmbedmentM: > 0 | A design embedment must be positive. |
| `PileCriteriaShape` | every Pile | Violation | maxLateralDisplacementMm: > 0 | A maximum lateral displacement must be positive. |
| `PileCriteriaShape` | every Pile | Violation | minTorqueFtLbs: > 0 | A minimum installation torque must be positive. |
| `QuantityShape` | anything with requiredQuantity | Violation | requiredQuantity: xsd:integer, >= 1 | A required quantity must be a whole number of at least 1. |
| `ReinforcesShape` | anything with reinforces | Warning | SPARQL check | A reinforcing member should say how it must be installed (shoring, weld sequence) or be marked as having no constraint. |
| `RequirementClauseShape` | every RequirementClause | Violation | clauseText: at least 1, xsd:string | A requirement clause must keep its text as printed. |
| `RequirementClauseShape` | every RequirementClause | Violation | requirementTopic: at least 1 | A requirement clause must have a topic (welding, bolting, coating ...). |
| `RequirementTopicValuesShape` | anything with requirementTopic | Violation | requirementTopic: one of WeldingReq, BoltingReq, CoatingReq, FireproofingReq, InspectionReq, MaterialReq, ToleranceReq, GratingReq, UnitsReq, ConnectionDesignReq, ErectionReq, ShopDrawingReq, LiftingReq, PileInstallReq, ExistingStructureReq, ScopeExclusionReq, SubmittalReq | requirementTopic must be a member of the closed vocabulary RequirementTopic (see core.ttl). |
| `ResponsibilityTagValuesShape` | anything with responsibility | Violation | responsibility: one of ByEngineerOfRecord, ByConnectionEngineer, ByFabricator, BySupplier, ByOthers, ByOwner | responsibility must be a member of the closed vocabulary ResponsibilityTag (see core.ttl). |
| `ReviewOutcomeValuesShape` | anything with reviewOutcome | Violation | reviewOutcome: one of ReturnedForCorrection, ExceptionsNoted, ReviewComplete, ReviewNotRequired, ApprovedForFabrication, NoExceptionsNoted, ReviseAndResubmit, ReviewedForLimitedScope, NotReviewed | reviewOutcome must be a member of the closed vocabulary ReviewOutcome (see core.ttl). |
| `RevisionShape` | every Revision | Warning | issuePurpose: at least 1 | Revision has no issue purpose (issued for construction, for review ...): the revision row should say why it was issued. |
| `RowTotalShape` | every ScheduleRow | Warning | SPARQL check | Row total differs from the sum of its components: one of the printed numbers is misread or the table is wrong. |
| `ScheduleCellShape` | every ScheduleCell | Violation | cellText: at least 1, at most 1, xsd:string | A schedule cell needs exactly one text, the cell as printed. |
| `ScheduleCellShape` | every ScheduleCell | Violation | cellValueKind: at least 1 | A schedule cell must say what kind of value it holds (number, text, BY SUPPLIER, N/A ...). |
| `ScheduleCellShape` | every ScheduleCell | Warning | columnHeaderText: at least 1 | A schedule cell should keep its column header, or its value has no meaning. |
| `ScheduleKindValuesShape` | anything with scheduleKind | Violation | scheduleKind: one of ColumnSchedule, BeamSchedule, PileSchedule, FootingSchedule, BasePlateSchedule, MemberForceSchedule, ConnectionForceSchedule, JoistSchedule, DeckSchedule, OpeningSchedule, PlateQuantitySchedule, WallSchedule, DrawingListSchedule, BillOfMaterialSchedule, HoldListSchedule, CutListSchedule, OtherSchedule | scheduleKind must be a member of the closed vocabulary ScheduleKind (see core.ttl). |
| `ScheduleTotalShape` | every Schedule | Warning | SPARQL check | Printed schedule total differs from the sum of its rows by more than 0.5 percent: re-read the table before using the total. |
| `ScopeItemShape` | every ScopeItem | Violation | scopeItemText: at least 1, xsd:string | A scope item must carry its text; an id alone does not say what is in scope. |
| `SelectionRowShape` | every SelectionRow | Violation | rowKeyText: at least 1 | A selection row must keep its key (the range it applies to). |
| `SelectionRowShape` | every SelectionRow | Violation | rowValuesText: at least 1 | A selection row must keep its values as printed. |
| `SheetKindValuesShape` | anything with sheetKind | Violation | sheetKind: one of GeneralNotesSheet, SpecificationSheet, CoverSheet, IndexSheet, PlanSheet, ElevationSheet, SectionSheet, DetailSheet, ScheduleSheet, ThreeDSheet, TypicalDetailsSheet, IssueRecordSheet, ScopeSheet, PhotoSheet, HandSketchSheet, PipingIsometricSheet, StandardSheet, BlankSheet, WorkPackageSheet, ChangeNoticeSheet, ManualSheet, TransmittalSheet, ReactionSheet, AnchorBoltPlanSheet, FrameCrossSectionSheet, ConsultantListSheet | sheetKind must be a member of the closed vocabulary SheetKind (see core.ttl). |
| `SheetShape` | every Sheet | Violation | pageIndex: at least 1, at most 1, xsd:integer, >= 1 | Sheet needs exactly one page index, a whole number from 1: the page of the PDF it was read from. |
| `SheetShape` | every Sheet | Violation | sheetKind: at least 1 | Sheet has no sheet kind (plan, elevation, detail, notes ...): give one from the SheetKind list. |
| `SheetShape` | every Sheet | Warning | sheetNumber: at least 1, at most 1, xsd:string | Sheet has no sheet number (some drawings genuinely lack one: flag, do not fail). |
| `SheetTotalShape` | every Sheet | Violation | SPARQL check | pageIndex is larger than sheetTotal ('sheet n of N'). |
| `StandardDocumentShape` | every StandardDocument | Warning | standardRevisionText: at least 1 | A reproduced or cited standard should record its revision as printed (revisions differ between projects). |
| `SubmissionStageValuesShape` | anything with submissionStage | Violation | submissionStage: one of PreliminaryReviewStage, Review60Stage, Review90Stage, BidStage, BidAddendumStage, ConstructionIssueStage, Review50Stage, Review95Stage, Review100Stage | submissionStage must be a member of the closed vocabulary SubmissionStage (see core.ttl). |
| `TitleBlockStatusConflictShape` | every Sheet | Warning | SPARQL check | Title block status says AS BUILT but a revision row says issued for construction: check which is current. |
| `UnitSystemValuesShape` | anything with unitSystem | Violation | unitSystem: one of Metric, Imperial, MixedUnits, DualUnits | unitSystem must be a member of the closed vocabulary UnitSystem (see core.ttl). |
| `VendorStampShape` | every Annotation | Warning | SPARQL check | A vendor review stamp should record its ticked outcome (reviewOutcome). |
| `ViewKindValuesShape` | anything with viewKind | Violation | viewKind: one of PlanView, ElevationView, SectionView, DetailView, ThreeDView, PhotoView, KeyPlanView, IsometricView, ScheduleView, NotesView | viewKind must be a member of the closed vocabulary ViewKind (see core.ttl). |
| `WatermarkConflictShape` | every Sheet | Warning | SPARQL check | Sheet has an information-only or preliminary watermark but a revision row says issued for construction: confirm it may be built from. |
| `WorkKindValuesShape` | anything with scopeItemWork, workKind | Violation | scopeItemWork: one of SupplyOnly, FabricateOnly, InstallOnly, SupplyAndInstall, FieldWeldOnly, ShipLoose | scopeItemWork must be a member of the closed vocabulary WorkKind (see core.ttl). |
| `WorkKindValuesShape` | anything with scopeItemWork, workKind | Violation | workKind: one of SupplyOnly, FabricateOnly, InstallOnly, SupplyAndInstall, FieldWeldOnly, ShipLoose | workKind must be a member of the closed vocabulary WorkKind (see core.ttl). |
| `WorkPointShape` | every WorkPoint | Warning | easting: at least 1 | A work point should give its easting. |
| `WorkPointShape` | every WorkPoint | Warning | northing: at least 1 | A work point should give its northing. |
| `ZoneKindValuesShape` | anything with zoneKind | Violation | zoneKind: one of LoadZoneKind, RepairZoneKind, PlantAreaKind, BuildingSegmentKind, FutureAreaKind, HoldAreaKind | zoneKind must be a member of the closed vocabulary ZoneKind (see core.ttl). |
| `ZoneShape` | every Zone | Violation | zoneKind: at least 1 | A zone must say what kind of zone it is (load zone, repair zone, plant area ...). |
