"""SHACL validation with a report people can read.

The ontology infers under the open world; the shapes in ``ontology/shapes.ttl`` are the
closed-world checks: mandatory fields, value ranges and table arithmetic. This module runs them
and turns the SHACL results graph into plain findings (severity, focus node, path, message).

A warning does not make data non-conforming: it asks a person to look. Only violations do.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pyshacl
from rdflib import RDF, SH, Graph, URIRef
from rdflib.term import Node as RdfTerm

from steel_ontology.graph import to_graph
from steel_ontology.models import Extraction
from steel_ontology.vocabulary import load_ontology, load_shapes


class Severity(StrEnum):
    """SHACL severities, most serious first."""

    VIOLATION = "Violation"
    WARNING = "Warning"
    INFO = "Info"


_SEVERITY_ORDER = {Severity.VIOLATION: 0, Severity.WARNING: 1, Severity.INFO: 2}


@dataclass(frozen=True)
class Finding:
    """One SHACL result.

    ``focus_node``, ``path`` and ``shape`` are full IRIs (or ``None`` when SHACL gives none);
    ``value`` is the offending value as text.
    """

    severity: Severity
    focus_node: str
    message: str
    path: str | None = None
    value: str | None = None
    shape: str | None = None

    def to_text(self) -> str:
        """One line: severity, focus node, path, message."""
        where = _short(self.focus_node)
        if self.path:
            where += f" . {_short(self.path)}"
        return f"{self.severity.value.upper():9} {where}: {self.message}"


@dataclass(frozen=True)
class ValidationReport:
    """All findings for one data graph, violations first."""

    findings: tuple[Finding, ...]

    @property
    def violations(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.VIOLATION)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)

    @property
    def conforms(self) -> bool:
        """True when there is no violation (warnings are allowed)."""
        return not self.violations

    def to_text(self) -> str:
        """The whole report as text, one finding per line, with a summary line first."""
        verdict = "conforms" if self.conforms else "does not conform"
        head = f"{verdict}: {len(self.violations)} violation(s), {len(self.warnings)} warning(s)"
        return "\n".join([head, *(f.to_text() for f in self.findings)])

    def to_dicts(self) -> list[dict[str, str | None]]:
        """Findings as plain dictionaries (for JSON output)."""
        return [
            {
                "severity": f.severity.value,
                "focus_node": f.focus_node,
                "path": f.path,
                "value": f.value,
                "message": f.message,
                "shape": f.shape,
            }
            for f in self.findings
        ]


def validate(data: Graph | Extraction, *, shapes: Graph | None = None) -> ValidationReport:
    """Check a data graph (or an extraction) against the SHACL shapes.

    The ontology is merged into the data before validation: SHACL follows ``rdfs:subClassOf``
    in the data graph, so a shape that targets ``ScheduleRow`` also checks every
    ``ElementRow``. No OWL inference is run here, so the result depends only on stated facts.
    """
    data_graph = to_graph(data) if isinstance(data, Extraction) else data
    ontology = load_ontology()
    shapes_graph = shapes if shapes is not None else load_shapes()
    merged = Graph()
    for triple in data_graph:
        merged.add(triple)
    for triple in ontology:
        merged.add(triple)
    _, results, _ = pyshacl.validate(
        merged,
        shacl_graph=shapes_graph,
        inference="none",
        allow_warnings=True,
    )
    findings = [
        _finding(results, shapes_graph, node)
        for node in results.subjects(RDF.type, SH.ValidationResult)
    ]
    findings.sort(
        key=lambda f: (_SEVERITY_ORDER[f.severity], f.focus_node, f.path or "", f.message)
    )
    return ValidationReport(tuple(findings))


def _finding(results: Graph, shapes: Graph, node: RdfTerm) -> Finding:
    severity = results.value(node, SH.resultSeverity)
    path = results.value(node, SH.resultPath)
    value = results.value(node, SH.value)
    messages = sorted(str(m) for m in results.objects(node, SH.resultMessage))
    return Finding(
        severity=Severity(str(severity).rsplit("#", 1)[-1]),
        focus_node=str(results.value(node, SH.focusNode)),
        message=" ".join(messages),
        path=str(path) if isinstance(path, URIRef) else None,
        value=str(value) if value is not None else None,
        shape=_named_shape(shapes, results.value(node, SH.sourceShape)),
    )


def _named_shape(shapes: Graph, source: RdfTerm | None) -> str | None:
    """IRI of the node shape a result came from (property shapes are blank nodes inside it)."""
    if isinstance(source, URIRef):
        return str(source)
    if source is None:
        return None
    parent = shapes.value(predicate=SH.property, object=source)
    return str(parent) if isinstance(parent, URIRef) else None


def _short(iri: str) -> str:
    """Last segment of an IRI, enough to recognise a node in a report line."""
    cut = max(iri.rfind("#"), iri.rfind("/"))
    return iri[cut + 1 :] or iri
