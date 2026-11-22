"""Replay of stored answers: the provider that makes the pipeline run offline.

A recording is a folder with one JSON file per call, named by the request key
(``page-001.json``). ``steel-ontology extract --save-responses DIR`` writes such a folder from a
live provider; the folder shipped with the example was written by hand from the gold data and
says so in its README. No model is called and nothing leaves the machine.
"""

from __future__ import annotations

from pathlib import Path

from steel_ontology.extract.providers.base import ProviderError, Request


class RecordedProvider:
    """Answers each request with the file ``<folder>/<request.key>.json``."""

    name = "recorded"

    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise ProviderError(f"recorded: {self.folder} is not a folder of recorded answers")
        self.model = f"recording:{self.folder.name}"

    def complete(self, request: Request) -> str:
        path = self.folder / f"{request.key}.json"
        if not path.is_file():
            raise ProviderError(f"recorded: no stored answer for {request.key!r} in {self.folder}")
        return path.read_text(encoding="utf-8")
