# Changelog

Decisions and lessons, newest version first. It holds no project, company or drawing content.

## 1.0.6 (first public release)

A review before publication found modelling faults that change what a reasoner or a validator
concludes. They are fixed here, with a regression test for each.

Domains and ranges. In OWL a domain or range is an inference rule, not a check, so a narrow one
quietly reclassifies data or makes it inconsistent.

- `hasPart` had range `Member`. A skid holding a truss or a base plate connection was
  inconsistent (members and assemblies are disjoint), and a lifting lug in an assembly was
  inferred to be a member. The range is now `Element`.
- `camberMm` had domain `Beam`, so a cambered joist was inconsistent (beams and joists are
  disjoint). It is now beam, joist or truss. `studCount` is now beam or joist.
- `sectionText` had domain `Member`, so a plate with "PL10" was inferred to be a member. It is
  now member or plate.

Units. Property names such as `axialKN` said kilonewtons while `forceUnit` allowed kip, so a
schedule printed in kips could only be stored by converting it or by mislabelling it.

- Force values are now unit-free and stored as printed: `axialValue`, `compressionValue`,
  `tensionValue`, `shearMajorValue`, `shearMinorValue` in `forceUnit`; `momentMajorValue`,
  `momentMinorValue`, `torsionValue` in the new `momentUnit` (one functional unit could not
  describe kN and kN.m on one record). They replace `axialKN`, `compressionKN`, `tensionKN`,
  `shearMajorKN`, `shearMinorKN`, `momentMajorKNm`, `momentMinorKNm` and `torsionKNm`.
- Numeric properties that keep a unit in their name (`elevationM`, `cutLengthMm`,
  `areaLoadKPa` ...) are now documented as what they are: numbers in that unit, normalised for
  arithmetic. See "Values as printed" in docs/modelling-decisions.md.

Names that said more or less than the definition:

- `ScheduleWithForces` is a row, not a schedule: renamed `RowWithForces`.
- `ExistingElement` covered only elements to remain. It now covers all three existing statuses
  (to remain, to demolish, to be modified).
- `UnverifiedFact` covered only force records: renamed `UnverifiedForceRecord`.
- A review outcome whose name repeated one stamp's wording is now `ReviewedForLimitedScope`.

Shapes:

- Closed vocabularies are now checked with `sh:in`, one shape per vocabulary. `sh:class` let a
  new individual typed as a member pass, in RDF input; only the typed models refused it.
- The clause-value warning fires only for a clause whose text prints a number or a percentage.
  The gold example now conforms with no warning.
- Every property shape has a readable message. No finding shows raw SHACL text.
- A force or moment value without its printed unit is warned about.
- Two overlapping disjointness axioms were merged.

Queries and the question router (not vocabulary, listed for completeness):

- CQ08 added area loads (kPa) across zones, which is not a quantity anyone designs with. It now
  returns the load of each zone (`area-loads-by-zone`).
- CQ01, CQ02 and the new CQ21 ask for reasoner-defined classes and run the OWL RL reasoner
  first, instead of repeating the class definitions in SPARQL.
- CQ17 returns each element once on an inferred graph (its most specific class).
- New: CQ21 connections someone else designs, CQ22 elements by responsibility, CQ23 forces on
  each element, CQ24 printed schedule totals beside the sum of their rows.
- The router no longer lets a single vocabulary word choose a query ("by others" once picked
  the area-load sum through `OtherLoad`); a query needs one of its own keywords.

Namespace: `https://jaymirzaei.github.io/steel-drawing-ontology/core#` (shapes `.../shapes#`).

## 1.0.5

Two faults were found while preparing the first public release. Both change what a reasoner or a
validator concludes, so they get their own version.

- `isVoided` had two `rdfs:domain` axioms (first `View`, later `View or Annotation`). In OWL two
  domains intersect, so a voided stamp was inferred to be a view, which is disjoint from
  annotation. The older axiom was removed. A test now refuses a property with two domains.
- `sh:severity` was written on `sh:sparql` constraints. SHACL reads severity from the shape
  only, so the arithmetic and conflict checks were reported as violations instead of warnings.
  Each SPARQL check is now its own node shape carrying its severity; the sheet-total shape was
  split in two (`SheetTotalShape`, `TitleBlockStatusConflictShape`) for that reason.

Three small gaps showed up while writing the gold data of the synthetic example, and were closed:

- `annotationText`: the wording of a note, stamp or markup. Before this a query note could be
  classified but its question was lost.
- `standardDesignation` on `Standard`: the cited code as printed. A `Standard` had no name.
- `gridLocationText` on `Element`: the grid intersection where an element sits, one value per
  place. This is text as printed, not a grid model: grids, bays and coordinates are still not
  in the vocabulary.

Four everyday competency queries were added next to the sixteen original ones (elements of one
class, sheet list with revisions, annotation wording, cited standards).

## Before 1.0.5

The vocabulary was developed from structural drawings over earlier versions. The main steps, in
order:

- One core ontology for all kinds of steel drawing sets. Job types differ in who authored a set
  and what it contains, so they became values (`authorRole`, `Domain`) and defined classes, not
  separate ontologies.
- Drawing content kept apart from annotation: take-off highlights, received stamps and query
  notes carry an `annotationOrigin`, and scope language ("by others", "by connection engineer")
  became a closed `ResponsibilityTag` vocabulary.
- Schedules as first-class objects (`Schedule`, `ScheduleRow`, `ScheduleCell`), with forces that
  state whether they are factored.
- A PDF treated as a package: sheets can have different authors and statuses, and status stamps
  are separate from the revision table.
- Assemblies with weights and parts, the type and instance pattern (`ElementType`), voided
  content, submission stages and hold lists.
- `Evidence` on every extracted value (sheet, zone, confidence), after a first extraction test
  showed that nothing said where a value was read.
- Requirement clauses, selection tables, design parameters, reinforcement of existing members,
  pile installation criteria and typed default rules ("unless noted otherwise, design for 50% of
  the tensile yield resistance").
- Construction sequences, keeper plates, citations of standard-notes sheets, and SHACL-SPARQL
  checks that printed schedule totals match their rows.
- From 1.0.0: a new class (not a value or a field) needs evidence from at least two different
  drawing sets. An OWL DL reasoner (HermiT) must load the ontology with no unsatisfiable class.
