# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A run's inputs survive being stored, and a run stored before inputs existed still loads."""

import json

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_input import RunInput
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.book_run_codec import BookRunCodec

CODEC = BookRunCodec()


def run(*inputs: RunInput) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "an idea", 1_000_000, inputs=inputs)
    return BookRun(
        "run-1", brief, StagePlan(BookKind.NONFICTION, ("brief", "outline")), Budget(1_000_000)
    )


def test_inputs_round_trip_exactly() -> None:
    made = run(RunInput("notes", "Line\n\tTwo — é"), RunInput("ch1", "x", "file"))
    assert CODEC.decode(CODEC.encode(made)) == made


def test_a_run_stored_before_inputs_existed_loads_with_none() -> None:
    document = json.loads(CODEC.encode(run()))
    del document["brief"]["inputs"]
    assert "inputs" not in document["brief"]
    assert CODEC.decode(json.dumps(document)).brief.inputs == ()


def test_a_stored_input_is_checked_again_when_it_is_loaded() -> None:
    document = json.loads(CODEC.encode(run(RunInput("notes", "fine"))))
    document["brief"]["inputs"][0]["text"] = "bad" + chr(0x202E) + "text"
    try:
        CODEC.decode(json.dumps(document))
    except ValueError as error:
        assert "cannot be seen" in str(error)
    else:
        raise AssertionError("a hidden character was loaded")
