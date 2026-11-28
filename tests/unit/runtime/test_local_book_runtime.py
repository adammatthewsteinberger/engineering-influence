"""A whole book made in one process over a folder of state: end to end, resumable, and refused before it spends."""

import json
from datetime import date
from pathlib import Path

import pytest
from smoke_rehearsal import NoSecrets, RehearsalBuilder, brief_for, environment, serve

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.local_book_creator_interface import (
    LocalBookCreatorInterface,
)
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.run_status import RunStatus
from engineering_influence.runtime.local_book_runtime import LocalBookRuntime

TODAY = date(2026, 11, 22)
PRICING = (
    '\n[pricing]\nverified_on = "2026-11-19"\nsource_url = "https://kdp.example/costs"\n'
    "ebook = 4.99\npaperback = 12.99\n"
)


def made(tmp_path: Path, url: str, **settings: str) -> LocalBookRuntime:
    return LocalBookRuntime(
        tmp_path / "state",
        environment(tmp_path, url, settings),
        NoSecrets(),
        TODAY,
        builder=RehearsalBuilder(),
    )


def test_a_non_fiction_book_is_made_from_its_brief_and_written_out(tmp_path: Path) -> None:
    heard: list[str] = []
    with serve() as server:
        creator = made(tmp_path, server.url)
        assert isinstance(creator, LocalBookCreatorInterface)
        try:
            run = creator.start(brief_for(BookKind.NONFICTION), heard.append)
            summary = creator.export(tmp_path / "out")
        finally:
            creator.close()
    assert run.status is RunStatus.COMPLETED
    assert heard[0] == "brief: advanced" and heard[-1] == "narration: completed"
    assert len(heard) == 15 and summary.files > 10
    out = tmp_path / "out"
    assert (out / "books" / "herbs-indoors.toml").is_file()
    assert (out / "src" / "chapter_02.md").is_file()
    assert (out / "run" / "book" / "herbs-indoors.pdf").read_bytes() == b"%PDF-1.7"
    assert (out / "run" / "quality-report.json").is_file()


def test_a_novel_is_made_the_same_way(tmp_path: Path) -> None:
    with serve() as server:
        creator = made(tmp_path, server.url)
        try:
            run = creator.start(brief_for(BookKind.NOVEL), lambda line: None)
            creator.export(tmp_path / "out")
        finally:
            creator.close()
    assert run.status is RunStatus.COMPLETED
    assert 'kind = "novel"' in (tmp_path / "out" / "books" / "the-salt-road.toml").read_text()


def test_the_run_is_kept_in_the_state_folder_so_a_finished_run_costs_nothing_to_look_at_again(
    tmp_path: Path,
) -> None:
    with serve() as server:
        first = made(tmp_path, server.url)
        try:
            first.start(brief_for(BookKind.NONFICTION), lambda line: None)
        finally:
            first.close()
        calls = len(server.seen)
        second = made(tmp_path, server.url)
        try:
            run = second.resume(False, lambda line: None)
        finally:
            second.close()
        assert len(server.seen) == calls
    assert run.status is RunStatus.COMPLETED
    assert (tmp_path / "state" / LocalBookRuntime.DATABASE).is_file()


def test_a_run_that_is_killed_is_continued_without_paying_for_the_stages_that_finished(
    tmp_path: Path,
) -> None:
    def kill_after_research(line: str) -> None:
        if line.startswith("research"):
            raise KeyboardInterrupt

    with serve() as server:
        first = made(tmp_path, server.url)
        try:
            with pytest.raises(KeyboardInterrupt):
                first.start(brief_for(BookKind.NONFICTION), kill_after_research)
        finally:
            first.close()
        paid = [r for r in server.seen if b"Write the brief" in r.body]
        assert len(paid) == 1
        second = made(tmp_path, server.url)
        try:
            heard: list[str] = []
            run = second.resume(False, heard.append)
        finally:
            second.close()
        again = [r for r in server.seen if b"Write the brief" in r.body]
    assert run.status is RunStatus.COMPLETED and len(again) == 1
    assert heard[0] == "outline: advanced"


def test_a_book_with_no_author_details_is_refused_before_anything_is_made_or_paid_for(
    tmp_path: Path,
) -> None:
    with serve() as server:
        env = environment(tmp_path, server.url)
        del env["EI_AUTHOR_PROFILE"]
        with pytest.raises(ApplicationError) as error:
            LocalBookRuntime(tmp_path / "state", env, NoSecrets(), TODAY)
        assert error.value.code == "AUTHOR_PROFILE_REQUIRED"
        assert server.seen == [] and not (tmp_path / "state").exists()


def test_a_strict_release_needs_the_authors_pricing_before_anything_is_paid_for(
    tmp_path: Path,
) -> None:
    with serve() as server:
        with pytest.raises(ApplicationError) as error:
            made(tmp_path, server.url, EI_BUILD_STRICT_RELEASE="1")
        assert error.value.code == "PRICING_REQUIRED"
        assert not (tmp_path / "state").exists()
        env = environment(tmp_path, server.url, {"EI_BUILD_STRICT_RELEASE": "1"})
        author = Path(env["EI_AUTHOR_PROFILE"])
        author.write_text(author.read_text() + PRICING, encoding="utf-8")
        LocalBookRuntime(tmp_path / "state", env, NoSecrets(), TODAY).close()


def test_the_plan_sets_the_brief_against_what_the_priced_model_would_charge(tmp_path: Path) -> None:
    with serve() as server:
        creator = made(tmp_path, server.url)
        try:
            plan = creator.plan(brief_for(BookKind.NONFICTION))
        finally:
            creator.close()
    assert plan is not None and plan.estimate.expected() > plan.estimate.essential() > 0
    assert plan.cap == 5_000_000 and plan.grade() in {"short", "tight", "lean", "ample"}
    assert server.seen == []  # an estimate asks the model nothing


def test_with_the_offline_placeholder_there_is_no_price_and_no_plan(tmp_path: Path) -> None:
    env = environment(tmp_path, "http://127.0.0.1:1", {"EI_STAGE_EXECUTOR": "deterministic"})
    creator = LocalBookRuntime(tmp_path / "state", env, NoSecrets(), TODAY)
    try:
        assert creator.plan(brief_for(BookKind.NONFICTION)) is None
    finally:
        creator.close()


def test_a_finished_run_records_what_it_spent_beside_what_the_brief_was_expected_to_cost(
    tmp_path: Path,
) -> None:
    with serve() as server:
        creator = made(tmp_path, server.url)
        try:
            creator.start(brief_for(BookKind.NONFICTION), lambda line: None)
            creator.export(tmp_path / "out")
        finally:
            creator.close()
    spend = json.loads((tmp_path / "out" / "run" / "quality-report.json").read_text())["spend"]
    assert spend["cap_micro_usd"] == 5_000_000 and spend["spent_micro_usd"] > 0
    assert spend["estimated_micro_usd"] > 0 and spend["spent_over_estimated"] > 0


class Killed(BaseException):
    """What a killed process looks like to the run: nothing after it runs."""


def finished_in_one_go(
    tmp_path: Path, url: str, kind: BookKind
) -> tuple[list[str], int, dict[str, str]]:
    """The uninterrupted run: its progress lines, what it spent, and the chapters it wrote."""
    heard: list[str] = []
    creator = made(tmp_path, url)
    try:
        run = creator.start(brief_for(kind), heard.append)
        creator.export(tmp_path / "out")
    finally:
        creator.close()
    assert run.status is RunStatus.COMPLETED
    return heard, run.budget.spent, chapters_of(tmp_path / "out")


def chapters_of(out: Path) -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8") for p in sorted((out / "src").glob("chapter_*.md"))
    }


@pytest.mark.parametrize(
    ("kind", "stages"),
    [(BookKind.NONFICTION, 15), (BookKind.NOVEL, 12)],
    ids=["nonfiction", "novel"],
)
def test_a_run_killed_after_any_stage_ends_where_an_uninterrupted_run_ends_and_pays_for_nothing_twice(
    tmp_path: Path, kind: BookKind, stages: int
) -> None:
    whole = tmp_path / "whole"
    whole.mkdir()
    with serve() as reference:
        lines, spent, chapters = finished_in_one_go(whole, reference.url, kind)
        calls = len(reference.seen)
    assert len(lines) == stages and chapters

    for killed_after in range(1, stages):
        folder = tmp_path / f"killed-after-{killed_after}"
        folder.mkdir()
        seen = 0

        def kill(line: str, at: int = killed_after) -> None:
            nonlocal seen
            seen += 1
            if seen == at:
                raise Killed

        with serve() as server:
            first = made(folder, server.url)
            try:
                with pytest.raises(Killed):
                    first.start(brief_for(kind), kill)
            finally:
                first.close()
            second = made(folder, server.url)
            try:
                resumed: list[str] = []
                run = second.resume(False, resumed.append)
                second.export(folder / "out")
            finally:
                second.close()
            paid_in_all = len(server.seen)

        where = f"killed after stage {killed_after} of {stages}"
        assert run.status is RunStatus.COMPLETED, where
        assert resumed == lines[killed_after:], (
            where
        )  # it carried on from the next stage, not the first
        assert paid_in_all == calls, (
            where
        )  # every model call was made exactly once across both processes
        assert run.budget.spent == spent, where  # and so the bill is the uninterrupted run's bill
        assert chapters_of(folder / "out") == chapters, where  # and the book is the same book
