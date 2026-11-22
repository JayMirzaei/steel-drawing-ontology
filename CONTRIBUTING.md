# Contributing

Issues and pull requests are welcome. Please keep changes small and tested.

## Set up

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

The HermiT tests run only when Java is found (`STEEL_ONTOLOGY_JAVA`, `JAVA_HOME` or `java` on
the `PATH`); CI runs them.

## Changing the vocabulary

- Edit `ontology/core.ttl` and, where a rule applies, `ontology/shapes.ttl`.
- Mirror the change in `src/steel_ontology/models.py` or `enums.py`. The tests compare the
  models with the ontology and fail until they agree.
- Add sample data that uses the new term in `tests/data/` and a test for any new shape.
- Regenerate the reference: `uv run steel-ontology docs --markdown docs/vocabulary.md`.
- Bump the version in `pyproject.toml`, `steel_ontology/vocabulary.py` and the ontology header,
  and say what changed and why in `CHANGELOG.md`.
- A new class (not a value or a field) needs evidence from at least two different drawing
  sets. Values stay as printed.

## Adding a question

Add a `cqNN_<name>.rq` file to `src/steel_ontology/queries/` with the `# id`, `# title`,
`# question` and optional `# param` header lines, a test in `tests/test_queries.py`, and keyword
patterns in `ask.KEYWORDS` with a routing case in `tests/test_ask.py`.

## Adding a model provider

Implement `complete(request) -> str` (see `extract/providers/base.py`), register it in
`extract/providers/__init__.py`, put its SDK in an optional extra, and test it with a mocked
client. Never commit keys. Example drawings in this repository are synthetic; keep it that way.

## Changing the example

Edit `examples/generator/` and run `uv run python examples/generate.py`. The tests check that
the committed files match a fresh run.
