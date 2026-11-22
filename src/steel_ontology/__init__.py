"""Steel drawing ontology: typed objects, RDF mapping, validation, reasoning and queries.

The usual path through the package::

    from steel_ontology import Extraction, to_graph, validate, infer, run_query

    extraction = Extraction.from_json(text)      # typed objects (steel_ontology.models)
    graph = to_graph(extraction)                 # RDF in the ontology's vocabulary
    report = validate(graph)                     # SHACL findings: severity, node, message
    inferred = infer(graph)                      # OWL RL class memberships
    rows = run_query(inferred.graph, "marked-up-sheets").rows
"""

from steel_ontology.graph import from_graph, load_graph, to_graph
from steel_ontology.models import Extraction, extraction_json_schema
from steel_ontology.queries import list_queries, run_query
from steel_ontology.reason import infer
from steel_ontology.validate import validate
from steel_ontology.vocabulary import STEEL, VERSION, load_ontology, load_shapes

__version__ = VERSION

__all__ = [
    "STEEL",
    "Extraction",
    "__version__",
    "extraction_json_schema",
    "from_graph",
    "infer",
    "list_queries",
    "load_graph",
    "load_ontology",
    "load_shapes",
    "run_query",
    "to_graph",
    "validate",
]
