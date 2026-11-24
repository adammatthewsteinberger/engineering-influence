"""A whole book made in one process over a folder of state: end to end, resumable, and refused before it spends."""

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
    assert heard[0] == "brief: advanced" and heard[-1] == "build: completed"
    assert len(heard) == 12 and summary.files > 10
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
