"""The Streamlit explorer, driven headless with ``streamlit.testing``."""

from __future__ import annotations

import pytest

from conftest import ROOT

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = str(ROOT / "app" / "explorer.py")


@pytest.fixture
def app() -> AppTest:
    test = AppTest.from_file(APP, default_timeout=120).run()
    assert not test.exception
    return test


def _widget(elements, label: str):
    return next(e for e in elements if e.label == label)


def _table(app: AppTest, column: str):
    return next(d.value for d in app.dataframe if column in d.value.columns)


def test_starts_on_the_example_and_validates_it(app: AppTest) -> None:
    assert [tab.label for tab in app.tabs] == [
        "Vocabulary",
        "Data",
        "Validate",
        "Reason",
        "Queries",
        "Ask",
    ]
    assert app.success[0].value == "Conforms: 0 violation(s), 0 warning(s)"
    assert len(_table(app, "class")) == 59
    assert any("gold.json" in caption.value for caption in app.sidebar.caption)


def test_vocabulary_filter(app: AppTest) -> None:
    _widget(app.radio, "Show").set_value("Properties").run()
    _widget(app.text_input, "Filter").set_value("weld").run()
    properties = _table(app, "property")
    assert 0 < len(properties) < 30
    assert all("weld" in " ".join(row).lower() for row in properties.itertuples(index=False))


def test_broken_variant_fails_validation(app: AppTest) -> None:
    _widget(app.sidebar.radio, "Source").set_value("Example: broken variant").run()
    assert app.error[0].value == "Does not conform: 5 violation(s), 1 warning(s)"
    findings = _table(app, "severity")
    assert list(findings["severity"]).count("Violation") == 5
    assert "sheet-S-301" in set(findings["object"])


def test_upload_choice_without_a_file_asks_for_one(app: AppTest) -> None:
    _widget(app.sidebar.radio, "Source").set_value("Upload a file").run()
    assert not app.exception
    assert len(app.info) >= 5  # the sidebar hint plus one per data tab


def test_reasoner_button(app: AppTest) -> None:
    _widget(app.button, "Run the reasoner").click().run()
    assert app.success[-1].value == "The data is consistent with the ontology."
    inferred = _table(app, "inferred classes")
    by_object = dict(zip(inferred["object"], inferred["inferred classes"], strict=True))
    assert "MarkedUpSheet" in by_object["sheet-S-101"]


def test_query_with_a_parameter(app: AppTest) -> None:
    _widget(app.selectbox, "Competency query").set_value(
        "CQ09 Requirement clauses on one topic"
    ).run()
    _widget(app.selectbox, "topic").set_value("BoltingReq").run()
    rows = _table(app, "clause")
    assert list(rows["clause"]) == ["clause-2"]
    assert list(rows["value"]) == ["20 mm A325"]


def test_ask_a_question_and_see_the_evidence(app: AppTest) -> None:
    _widget(app.text_input, "Question").set_value("What size is beam B3?").run()
    answer = _table(app, "evidence")
    assert list(answer["section"]) == ["W200x27"]
    assert answer["evidence"][0].startswith("S-101 zone ")
    assert any("Routed by rule to CQ17" in caption.value for caption in app.caption)

    _widget(app.text_input, "Question").set_value("Is the sky blue?").run()
    assert app.warning[0].value.startswith("I could not route this question")
