"""Shared fixtures: the ontology, the sample data files and the synthetic example."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph

from steel_ontology.vocabulary import load_ontology, load_shapes

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "data"
EXAMPLE = ROOT / "examples" / "kestrel-platform"
SAMPLE_NS = "https://example.org/sample#"


@pytest.fixture(scope="session")
def ontology() -> Graph:
    return load_ontology()


@pytest.fixture(scope="session")
def shapes() -> Graph:
    return load_shapes()


@pytest.fixture(scope="session")
def sample_good() -> Graph:
    return Graph().parse(DATA / "sample_good.ttl")


@pytest.fixture(scope="session")
def sample_bad() -> Graph:
    return Graph().parse(DATA / "sample_bad.ttl")


def data_graph(turtle: str) -> Graph:
    """Parse a Turtle snippet with the ``steel:``, ``ex:`` and ``owl:`` prefixes declared."""
    prefixes = (
        "@prefix steel: <https://jaymirzaei.github.io/steel-drawing-ontology/core#> .\n"
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "@prefix ex: <https://example.org/t#> .\n"
    )
    return Graph().parse(data=prefixes + turtle, format="turtle")
