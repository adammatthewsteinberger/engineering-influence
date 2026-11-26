# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RunEventBuilder: one event per receiver, the catalogue's payload keys, and nothing when no receiver is configured."""

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_event_builder import RunEventBuilder

RUN = BookRun(
    run_id="run-1",
    brief=BookBrief(BookKind.NONFICTION, "bees", 5_000_000),
    plan=NonfictionRecipes().plan(),
    budget=Budget(cap=5_000_000),
)


def test_with_no_receiver_no_event_is_built() -> None:
    builder = RunEventBuilder(())
    assert builder.started(RUN) == ()
    assert builder.completed(RUN) == ()


def test_each_receiver_gets_its_own_copy_with_its_own_id() -> None:
    builder = RunEventBuilder(("https://a.example", "https://b.example"))
    events = builder.started(RUN)
    assert [e.url for e in events] == ["https://a.example", "https://b.example"]
    assert len({e.event_id for e in events}) == 2
    assert all(e.event_name == "pipeline.started" for e in events)


def test_the_started_payload_has_the_catalogue_keys() -> None:
    (event,) = RunEventBuilder(("https://a.example",)).started(RUN)
    assert set(event.payload) == {"project_slug", "remaining_stages", "stage"}
    assert event.payload["project_slug"] == "run-1"


def test_the_phase_payload_names_the_stage_and_its_artifact() -> None:
    (event,) = RunEventBuilder(("https://a.example",)).phase_completed(RUN, "research")
    assert event.event_name == "phase.completed"
    assert event.payload == {
        "artifact_id": "run-1/research.md",
        "job_id": "run-1/research",
        "phase": "research",
        "project_slug": "run-1",
    }


def test_the_gate_payload_names_the_gate() -> None:
    (event,) = RunEventBuilder(("https://a.example",)).awaiting_gate(RUN, "research")
    assert event.event_name == "gate.awaiting"
    assert event.payload["gate"] == "spend-consent"
    assert set(event.payload) == {"gate", "job_id", "phase", "project_slug"}


def test_the_completion_payload_is_the_project() -> None:
    (event,) = RunEventBuilder(("https://a.example",)).completed(RUN)
    assert event.event_name == "pipeline.completed"
    assert event.payload == {"project_slug": "run-1"}
