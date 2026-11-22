# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""``ei plugins search`` and ``fetch`` over real files: a download is checked against its hash, and installs nothing."""

import hashlib
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface
from engineering_influence.runtime.cli_runtime import CliRuntime

URL = "https://plugins.example.com/v1/research_pack.toml"
BUNDLE = (
    b'name = "research_pack"\nversion = 1\ndescription = "Sources and style."\n\n'
    b'[[server]]\nname = "docs"\nurl = "https://mcp.example.com/v1/mcp"\n\n'
    b'[[skill]]\nname = "plain_style"\nversion = 2\n\n[skill.parts]\noutline = "Prefer short chapters."\n'
)


class Fetcher(BundleFetcherInterface):
    def __init__(self, pages: dict[str, bytes]) -> None:
        self.pages = pages
        self.asked: list[tuple[str, int]] = []

    def fetch(self, url: str, max_bytes: int) -> bytes:
        self.asked.append((url, max_bytes))
        if url not in self.pages:
            raise ApplicationError(
                code="BUNDLE_NOT_FOUND", message="plugins.example.com answered 404"
            )
        return self.pages[url]


class Project:
    def __init__(
        self, root: Path, capsys: pytest.CaptureFixture[str], pages: dict[str, bytes]
    ) -> None:
        self.root = root
        self.capsys = capsys
        self.fetcher = Fetcher(pages)
        self.cli = CliRuntime(bundles=self.fetcher).build()
        self.index = root / "index.toml"
        digest = hashlib.sha256(BUNDLE).hexdigest()
        self.index.write_text(
            f'version = 1\n\n[[plugin]]\nname = "research_pack"\nversion = 1\n'
            f'description = "Sources and style."\nurl = "{URL}"\nsha256 = "{digest}"\n',
            encoding="utf-8",
        )
        self.downloads = root / "downloads"
        self.plugin_lock = root / "ei-plugins.lock.toml"
        self.skill_lock = root / "ei-skills.lock.toml"

    def ei(self, *argv: str) -> tuple[int, str, str]:
        status = self.cli.run(["plugins", *argv])
        captured = self.capsys.readouterr()
        return status, captured.out, captured.err


@pytest.fixture
def project(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Project:
    return Project(tmp_path, capsys, {URL: BUNDLE})


def test_a_plugin_is_found_fetched_read_and_only_then_installed(project: Project) -> None:
    status, out, _ = project.ei("search", str(project.index))
    assert status == 0 and "research_pack@1" in out and "Sources and style." in out and URL in out

    status, out, _ = project.ei(
        "fetch", str(project.index), "research_pack", "--output", str(project.downloads)
    )
    saved = project.downloads / "research_pack.toml"
    assert status == 0 and saved.read_bytes() == BUNDLE
    assert "matches the index" in out and f"ei plugins add {saved}" in out
    assert project.fetcher.asked == [(URL, 512 * 1024)]
    assert not project.plugin_lock.exists() and not project.skill_lock.exists()

    assert project.ei("show", str(saved))[0] == 0
    assert not project.plugin_lock.exists()
    status, out, _ = project.ei(
        "add",
        "--lock",
        str(project.plugin_lock),
        "--skill-lock",
        str(project.skill_lock),
        str(saved),
    )
    assert status == 0 and "installed research_pack@1" in out
    assert "stages = []" in project.skill_lock.read_text(encoding="utf-8")


def test_a_download_that_is_not_what_the_index_promised_is_refused_and_nothing_is_saved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = Project(tmp_path, capsys, {URL: BUNDLE.replace(b"short", b"LONG!")})
    status, _, err = project.ei(
        "fetch", str(project.index), "research_pack", "--output", str(project.downloads)
    )
    assert status == 2 and "is not what the index promised" in err and "nothing was saved" in err
    assert not project.downloads.exists()


def test_a_file_that_is_already_there_is_never_overwritten(project: Project) -> None:
    args = ("fetch", str(project.index), "research_pack", "--output", str(project.downloads))
    assert project.ei(*args)[0] == 0
    saved = project.downloads / "research_pack.toml"
    saved.write_bytes(b"my edits")
    status, _, err = project.ei(*args)
    assert status == 2 and "already exists" in err and saved.read_bytes() == b"my edits"


def test_a_plugin_the_index_does_not_list_or_a_missing_index_is_refused(project: Project) -> None:
    status, _, err = project.ei("fetch", str(project.index), "other_pack")
    assert status == 2 and "lists no plugin named 'other_pack'" in err
    status, _, err = project.ei("search", str(project.root / "none.toml"))
    assert status == 2 and "there is no index at" in err


def test_a_download_the_fetcher_refuses_is_a_setup_error(project: Project) -> None:
    project.fetcher.pages.clear()
    status, _, err = project.ei(
        "fetch", str(project.index), "research_pack", "--output", str(project.downloads)
    )
    assert status == 2 and "plugins.example.com answered 404" in err


def test_search_with_text_finds_by_name_or_description(project: Project) -> None:
    assert "research_pack" in project.ei("search", str(project.index), "STYLE")[1]
    assert "matches 'zebra'" in project.ei("search", str(project.index), "zebra")[1]


def test_the_real_downloader_refuses_an_address_on_this_machine_without_touching_the_network(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = CliRuntime().build()
    assert cli.run(["plugins", "search", "https://127.0.0.1/index.toml"]) == 2
    err = capsys.readouterr().err
    assert "127.0.0.1 refused: non_public_address" in err


def test_an_index_address_that_is_not_https_is_refused_before_anything_is_contacted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = CliRuntime().build()
    assert cli.run(["plugins", "search", "http://plugins.example.com/index.toml"]) == 2
    assert "a file on disk or an https:// address" in capsys.readouterr().err
