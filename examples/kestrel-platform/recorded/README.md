# Recorded answers (fixture data, not model output)

The `page-NNN.json` files in this folder were written by `examples/generator/recorded.py` from
the gold extraction (`../gold.json`). They are in the wire format a model provider returns, one
file per page of `../drawings.pdf`. The `ask-*.json` file is a hand-written answer for the
question router's model fallback.

They are **not** the output of a language model, and they are not an accuracy result. They let
the pipeline run offline:

    steel-ontology extract examples/kestrel-platform/drawings.pdf \
        --provider recorded --recorded examples/kestrel-platform/recorded

A recording of a real model run has the same layout: `steel-ontology extract ... --provider
anthropic --save-responses DIR` writes one.
