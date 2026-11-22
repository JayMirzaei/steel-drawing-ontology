# Modelling decisions

Short notes on the choices that shape the vocabulary, and the reason for each. The changelog
says when each one was made.

## One core ontology

There is one vocabulary for every kind of steel drawing set, not one per job type. Job types
differ in who drew the set (engineer, supplier, fabricator, owner standard) and in what content
appears. Those differences are values (`authorRole`, `Domain`) and reasoner-defined classes, not
separate class trees. One vocabulary means one extractor contract, one set of shapes and one
set of queries.

## OWL infers, SHACL validates

OWL works under the open world: a sheet with no sheet number is not wrong, the number is just
not known. That is the right logic for classification ("this sheet carries third-party
markup") and the wrong logic for checking an extraction ("this force has no factored tag, so it
cannot be used"). So:

- mandatory fields, ranges and arithmetic are SHACL shapes, not OWL cardinalities;
- the ontology carries classes, domains and ranges, disjointness and defined classes;
- validation runs without inference, so its result depends only on what was extracted.

Severity is part of the design. A **violation** means a fact cannot be used as it stands. A
**warning** asks a person to look: a sheet without a number (some genuinely lack one), or a
printed schedule total that differs from the sum of its rows.

## Closed vocabularies

Kinds of things that a drawing chooses from a fixed list (sheet kind, load type, markup kind,
review outcome, responsibility) are closed enumerations: an `owl:oneOf` class plus
`owl:AllDifferent` over its members. Free text would make every total and every filter depend
on spelling.

A value outside the list fails validation, in both kinds of input. The typed models refuse it in
JSON. In RDF, one SHACL shape per vocabulary checks every vocabulary property with `sh:in`.
`sh:class` is not enough there: a file that declares `ex:MadeUpKind a steel:SheetKind` passes it,
and OWL cannot reject it either, because under the open world the new individual might be the
same as a listed member. Tests keep three lists in step for each vocabulary: `oneOf`,
`AllDifferent` (an early version had a member in one and not the other) and the shape's `sh:in`.

## Values as printed

Dates, units, marks, cell text and clause text are kept exactly as printed. Dates are strings,
not `xsd:date`: formats differ between drawings, silent parsing of "07/03/21" is a risk, and
`xsd:date` is outside the OWL 2 datatype map, so a DL reasoner refuses it. Numbers are decimals
that keep their printed digits ("1209.60" stays "1209.60").

Numbers and units follow one naming rule:

- **A numeric property without a unit in its name holds the number as printed**, and its unit
  as printed sits in a companion property, checked against a list. Force records work this way:
  `axialValue`, `tensionValue`, `shearMajorValue` ... in `forceUnit` (kN, kip, lbf ...), and
  `momentMajorValue`, `torsionValue` in `momentUnit` (kN.m, kip.ft ...). Two unit properties,
  because one record often prints a force and a moment. Nothing is converted: a column schedule
  printed in kips stays in kips, and a query shows the unit beside every value. This is where a
  wrong unit costs most (kip read as kN is off by 4.45 times), so it is where the printed form
  is kept.
- **A numeric property whose name ends in a unit holds the number in that unit**: `elevationM`
  in metres, `cutLengthMm` in millimetres, `areaLoadKPa` in kPa, `minTorqueFtLbs` in ft-lb.
  These are normalised values, there so that numbers can be compared and checked without a unit
  column each. When a sheet prints another unit, the extractor converts, and that is the one
  place where a number is not as printed. The printed form survives where a text property
  exists beside it (`weightText`, `eastingText`, `cellText`) and always on the drawing, which
  the evidence points to.

Version 1.0.5 and earlier mixed the two: `axialKN` was named in kN while `forceUnit` allowed kip.
1.0.6 renamed the force values; the alternative, converting every force to kN, would have lost
the printed number exactly where it matters most.

## Evidence on every fact

Every extracted object can point at `Evidence`: the sheet, a box on the sheet (fractions of the
page, origin top-left) and a confidence (`Verified`, `Probable`, `Unverified`). An answer can
then show where it came from, and a person can check it on the drawing in seconds. Facts
without evidence are allowed but visible: the pipeline lists objects that cite nothing, and the
defined class `UnverifiedForceRecord` collects force records whose only evidence is
unverified.

## Annotation is not design content

Revision clouds, take-off highlights, review stamps, query notes and received stamps are
`Annotation` objects with an origin: the engineer, or a third party. A fabricator's orange
highlight is not part of the design, and a reviewer's "confirm size?" is a question, not a
value. Mixing them would put someone else's markup into the design data. The colour code of
markup differs between fabricators, so its meaning is stored as text, not inferred from colour.

## Typed default rules

Drawings print conventions that give meaning to missing data: "unless noted otherwise, design
brace connections for 50% of the tensile yield resistance". Under the open world, a missing
force is unknown; on this drawing it is not. `DefaultRule` stores the kind of rule
(`DefaultRuleKind`), the percentage and the text, so an extractor can apply the printed default
and record that it did. The same sentence carries very different numbers between owners, so
the number is data, not a constant.

## Schedules as tables

Schedules, rows and cells are first-class. A cell can hold a number, text, "BY SUPPLIER",
"N/A", "see note", a blank or a library reference (`CellValueKind`): "BY SUPPLIER" is someone
else's value, not missing data. Printed totals and row values are kept, and the shapes check the
arithmetic within a tolerance. A mismatch is a warning: it may be a misread or a drafting error,
and either way a person should look.

## Type and instance

A base plate mark or a pile type is printed once in a schedule and placed many times on plans.
`ElementType` with `hasType` keeps that reuse; modelling each type as its own class would lose
it.

## A set is a package

One PDF can bundle sheets from several authors, disciplines and even projects. Author, status
and discipline are therefore per sheet, not per set, and a title-block status can disagree with
the revision table. The shapes flag such conflicts rather than choosing.

## Defined classes answer questions

Each of the 25 reasoner-defined classes answers a question a fabricator asks: which sheets carry
third-party markup, which connections someone else designs, which cells are supplier values,
which clauses are prohibitions. Nobody writes these memberships; the reasoner works them out
from stated facts, so they cannot disagree with the data.

Queries use them. A query about a defined class says so in its header (`# reasoner: required`),
the runner applies the OWL RL reasoner first, and the SPARQL asks for the class
(`?sheet a steel:MarkedUpSheet`) instead of restating its definition. CQ01 (sheets with
third-party markup, two defined classes deep), CQ02 (reference-only sheets) and CQ21
(connections someone else designs) work this way; the rule lives once, in `core.ttl`.

## Domains and ranges are wide on purpose

In OWL, `rdfs:domain` and `rdfs:range` are inference rules, not checks: if `hasPart` has range
`Member`, a plate listed as a part of an assembly is inferred to be a member, and a truss listed
as a part makes the data inconsistent (assemblies and members are disjoint). So a domain or
range names the widest class the property honestly applies to (`hasPart` ranges over `Element`;
`camberMm` applies to beams, joists and trusses), and anything narrower is a SHACL shape or the
typed models. Version 1.0.6 fixed four properties that had been too narrow.

## A class needs two different drawing sets

The vocabulary was developed from structural drawings. A new value or field could be added after
one clear example; a new class needed evidence from at least two different drawing sets (a fixed
rule from 1.0.0). Things seen once are noted and left out. The
class structure stopped changing early, and later additions were mostly fields and values.

## Things deliberately left out

- Names of people who sign or approve: personal data, and not needed for fabrication.
- Design formulas printed in notes.
- Viewer navigation text and stamps repeated on every page by a document system.
- A grid and location model: grid positions are kept as printed text (`gridLocationText`).
  Real grids are irregular, skewed and multi-level; a geometric model is future work.

## The extraction wire format

The model does not answer in the full JSON Schema of the typed models. It answers in a small
generic format (objects with name/values pairs) that every provider's structured-output mode
accepts, and the typed models do the real checking afterwards. This trades a little prompt
length for portability across providers, and for decoding that can drop one bad field instead
of losing a whole sheet.
