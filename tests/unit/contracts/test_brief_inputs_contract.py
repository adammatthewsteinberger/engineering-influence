# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Version 1 of the brief gained optional ``inputs``; a brief without them reads exactly as it did."""

from typing import Any

import pytest
from pydantic import ValidationError

from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.brief.v1.run_input_v1 import RunInputV1


def brief(**changes: Any) -> dict[str, Any]:
    return {"kind": "nonfiction", "idea": "an idea", "budget_micro_usd": 5_000_000, **changes}


def test_a_brief_without_inputs_is_unchanged_and_has_none() -> None:
    value = BookBriefV1.model_validate(brief())
    assert value.inputs == [] and value.schema_version == 1
    assert value.to_model().inputs == ()


def test_inputs_are_read_validated_and_carried_into_the_model() -> None:
    value = BookBriefV1.model_validate(
        brief(
            inputs=[
                {"name": "notes", "text": "My notes."},
                {"name": "ch1", "text": "x", "origin": "file"},
            ]
        )
    )
    assert isinstance(value.inputs[0], RunInputV1)
    model = value.to_model()
    assert [(i.name, i.text, i.origin) for i in model.inputs] == [
        ("notes", "My notes.", "pasted"),
        ("ch1", "x", "file"),
    ]


@pytest.mark.parametrize(
    "inputs",
    [
        [{"name": "notes"}],
        [{"text": "x"}],
        [{"name": "notes", "text": "x", "extra": 1}],
        [{"name": "Bad Name", "text": "x"}],
        [{"name": "notes", "text": "  "}],
        [{"name": "notes", "text": "bad" + chr(0x200B) + "text"}],
        [{"name": "notes", "text": "x", "origin": "email"}],
        [{"name": "a", "text": "x"}, {"name": "a", "text": "y"}],
        [{"name": f"n{n}", "text": "x"} for n in range(9)],
        [{"name": f"n{n}", "text": "a" * 50_000} for n in range(5)],
        "notes",
        [3],
    ],
)
def test_inputs_that_a_run_could_not_use_are_refused_when_the_brief_is_read(inputs: object) -> None:
    with pytest.raises(ValidationError):
        BookBriefV1.model_validate(brief(inputs=inputs))


def test_a_brief_with_inputs_cannot_be_changed_after_it_is_read() -> None:
    value = BookBriefV1.model_validate(brief(inputs=[{"name": "notes", "text": "x"}]))
    with pytest.raises(ValidationError):
        value.inputs[0].text = "other"  # type: ignore[misc]


def test_one_input_is_checked_on_its_own_not_only_inside_a_brief() -> None:
    with pytest.raises(ValidationError):
        RunInputV1(name="Bad Name", text="x")
    with pytest.raises(ValidationError):
        RunInputV1(name="ok", text="bad" + chr(0x200B))
    assert RunInputV1(name="ok", text="fine").origin == "pasted"


def test_the_published_schema_says_how_many_inputs_and_which_origins_are_allowed() -> None:
    schema = BookBriefV1.model_json_schema()
    assert schema["properties"]["inputs"]["maxItems"] == 8
    assert schema["$defs"]["RunInputV1"]["properties"]["origin"]["enum"] == ["pasted", "file"]
