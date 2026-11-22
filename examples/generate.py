"""Regenerate the synthetic example: ``uv run python examples/generate.py``.

Writes into ``examples/kestrel-platform/``:

- ``drawings.pdf``  four vector sheets of an invented steel platform job
- ``gold.json``     the correct extraction as typed objects
- ``gold.ttl``      the same as RDF
- ``broken.json``   the gold extraction with deliberate extractor mistakes
- ``broken.ttl``    the same as RDF
- ``recorded/``     the gold extraction split by sheet in the wire format of a model provider:
                    fixture data for the offline pipeline, not a model's output

Everything here is invented. The output is deterministic, so the committed files can
be compared with a fresh run (``tests/test_example.py`` does that).
"""

from __future__ import annotations

import sys
from pathlib import Path

from generator import draw, gold, recorded
from steel_ontology.graph import to_graph
from steel_ontology.models import Extraction

OUTPUT = Path(__file__).resolve().parent / "kestrel-platform"


def write_example(folder: Path) -> None:
    """Draw the set and write the gold and broken extractions into ``folder``."""
    folder.mkdir(parents=True, exist_ok=True)
    regions = draw.render(folder / "drawings.pdf")
    good = gold.build(regions)
    _write(good, folder, "gold")
    recorded.write_recording(good.normalised(), folder / "recorded")
    _write(gold.break_it(good), folder, "broken")


def _write(extraction: Extraction, folder: Path, stem: str) -> None:
    normalised = extraction.normalised()
    (folder / f"{stem}.json").write_text(normalised.to_json(), encoding="utf-8")
    turtle = to_graph(normalised).serialize(format="turtle")
    (folder / f"{stem}.ttl").write_text(turtle, encoding="utf-8")


if __name__ == "__main__":
    write_example(Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT)
    print(f"wrote {OUTPUT if len(sys.argv) < 2 else sys.argv[1]}")
