# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run names the locked servers it may use; None means every granted server, as for the command line."""

import json

import pytest

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.book_run_codec import BookRunCodec


def run(**changes: object) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 5_000_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    return BookRun("run-1", brief, plan, Budget(cap=5_000_000), **changes)  # type: ignore[arg-type]


def test_a_run_made_without_a_selection_may_use_every_granted_server() -> None:
    assert run().servers is None


def test_a_run_may_name_the_servers_it_may_use_and_none_at_all() -> None:
    assert run(servers=("docs",)).servers == ("docs",)
    assert run(servers=()).servers == ()


def test_a_server_is_named_once_in_a_run() -> None:
    with pytest.raises(ValueError, match="each of its servers once"):
        run(servers=("docs", "docs"))


@pytest.mark.parametrize("servers", [None, (), ("docs", "maps")])
def test_the_selection_survives_a_save_and_a_load(servers: tuple[str, ...] | None) -> None:
    codec = BookRunCodec()
    assert codec.decode(codec.encode(run(servers=servers))).servers == servers


def test_a_run_stored_before_selections_existed_loads_with_none() -> None:
    codec = BookRunCodec()
    document = json.loads(codec.encode(run()))
    del document["servers"]
    assert codec.decode(json.dumps(document)).servers is None
