# How the vocabulary was built

This is the method, in general terms.

## From structural drawings

Structural drawings were used. Each time a drawing said something the vocabulary could not, the
gap became a change (a value, a field, or rarely a class), a shape where a rule applied, and a
test. The [changelog](../CHANGELOG.md) records the decisions and lessons.

Drawings were read page by page as images, with zooms on the dense parts: notes, schedules,
title blocks, revision tables and stamps.

## Rules that kept it small

- **A new class needs evidence from two different drawing sets.** A value or a field could
  follow one clear example. A class had to recur. Candidates seen once stayed as notes.
- **Values are kept as printed.** No date parsing, no unit conversion, no normalised marks.
  The extractor's job is to read, not to interpret.
- **Prefer a value or a field to a class.** Job types, author roles and statuses became values
  and defined classes, not new class trees.
- **Every change is exercised.** Each vocabulary change came with sample data that uses it and
  a shape where a rule applies, and an OWL DL reasoner must load the ontology with no
  unsatisfiable class.

## How it settled

The class structure stopped changing early; later additions were mostly fields and values. That
is the sense in which the vocabulary is "1.0": stable for the kinds of drawings it describes. It
is not a claim about extraction accuracy, which is not measured.

## What was learned about drawings

- A PDF is a package. One file can hold sheets from several authors, disciplines and projects.
- Status is not where you expect it. A title block can say one thing, the revision table another
  and a stamp a third. Record each; trust none alone.
- Third-party markup is common: take-off highlights, received stamps, query notes. It must be
  kept apart from design content, and its colour code differs between fabricators.
- Drawings print their own defaults ("unless noted otherwise ..."). Reading a drawing correctly
  means applying them, and the numbers differ between owners.
- Schedules can be checked against themselves: printed totals against rows, row totals against
  components. No outside data is needed.
- Units, sign conventions and date formats vary within one set, sometimes within one table.
- Identical files appear under different names, and related drawing sets share base sheets.
  Duplicate detection has to work at page level.

## The example in this repository

The repository ships a synthetic four-sheet set drawn by `examples/generate.py`. It is small,
but it exercises the parts that matter: notes with a default rule and scope splits, a plan with
third-party markup and a revision cloud, schedules whose printed total can be checked, and
connection details. The gold extraction of that set, its broken variant and the recorded
extraction answers are all generated from the same script.
