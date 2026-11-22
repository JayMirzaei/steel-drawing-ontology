"""Extraction: drawing PDF -> typed objects, through a language model with structured output.

::

    from steel_ontology.extract import extract_pdf, get_provider

    provider = get_provider("recorded", recorded="examples/kestrel-platform/recorded")
    result = extract_pdf("examples/kestrel-platform/drawings.pdf", provider)
    result.extraction        # typed objects, every fact with Evidence (sheet, zone, confidence)
    result.report            # SHACL validation of the extraction
    result.problems          # what was dropped, conflicting or dangling

Providers: ``anthropic``, ``openai``, ``gemini`` (optional SDK extras), ``local`` (an
OpenAI-compatible server) and ``recorded`` (stored answers, fully offline).
"""

from steel_ontology.extract.pipeline import ExtractionResult, extract_pdf
from steel_ontology.extract.providers import (
    PROVIDERS,
    Provider,
    ProviderError,
    Request,
    get_provider,
)

__all__ = [
    "PROVIDERS",
    "ExtractionResult",
    "Provider",
    "ProviderError",
    "Request",
    "extract_pdf",
    "get_provider",
]
