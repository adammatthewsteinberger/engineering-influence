# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginMarketplace: an index lists files, a download is checked against its hash first, and nothing is installed."""

import hashlib
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.toml_plugin_index_parser import (
    TomlPluginIndexParser,
)
from engineering_influence.infrastructure.plugins.toml_plugin_parser import TomlPluginParser
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.services.interfaces.plugin_marketplace_interface import (
    PluginMarketplaceInterface,
)
from engineering_influence.services.plugin_marketplace import PluginMarketplace

URL = "https://plugins.example.com/research_pack.toml"
INDEX_URL = "https://plugins.example.com/index.toml"
FOLDER = Path("/downloads")
BUNDLE = (
    b'name = "research_pack"\nversion = 1\n\n[[skill]]\nname = "plain_style"\nversion = 2\n\n'
    b'[skill.parts]\noutline = "Prefer short chapters."\n'
)
DIGEST = hashlib.sha256(BUNDLE).hexdigest()


def index_text(
    version: int = 1, sha: str = DIGEST, name: str = "research_pack", url: str = URL
) -> bytes:
    return (
        f'version = 1\n\n[[plugin]]\nname = "{name}"\nversion = {version}\n'
        f'description = "Sources and style."\nurl = "{url}"\nsha256 = "{sha}"\n'
    ).encode()


class Fetcher(BundleFetcherInterface):
    def __init__(self, pages: dict[str, bytes | Exception] | None = None) -> None:
        self.pages = dict(pages or {})
        self.asked: list[tuple[str, int]] = []

    def fetch(self, url: str, max_bytes: int) -> bytes:
        self.asked.append((url, max_bytes))
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return page


class Files(SkillFilesInterface):
    def __init__(self, files: dict[Path, bytes] | None = None) -> None:
        self.files = dict(files or {})
        self.broken: dict[Path, ApplicationError] = {}
        self.writes: list[tuple[Path, bytes, bool]] = []

    def read(self, path: Path) -> bytes | None:
        if path in self.broken:
            raise self.broken[path]
        return self.files.get(path)

    def write(self, path: Path, data: bytes, replace: bool) -> None:
        self.writes.append((path, data, replace))
        self.files[path] = data

    def remove(self, path: Path) -> None:
        self.files.pop(path, None)


def market(
    fetcher: Fetcher, files: Files | None = None, max_bytes: int = 512 * 1024
) -> PluginMarketplace:
    return PluginMarketplace(
        fetcher,
        files or Files(),
        TomlPluginIndexParser(),
        TomlPluginParser(TomlSkillParser()),
        max_bytes,
    )


def refused(action: object, code: str, status: int = 422) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        action()  # type: ignore[operator]
    assert (error.value.code, error.value.http_status) == (code, status)
    return error.value


def test_it_is_a_plugin_marketplace() -> None:
    assert isinstance(market(Fetcher()), PluginMarketplaceInterface)


# -------------------------------------------------------------------------------------- index
def test_an_index_at_an_https_address_is_downloaded_with_the_size_cap_and_read() -> None:
    fetcher = Fetcher({INDEX_URL: index_text()})
    found = market(fetcher, max_bytes=1234).index(INDEX_URL)
    assert [entry.name for entry in found.entries] == ["research_pack"]
    assert fetcher.asked == [(INDEX_URL, 1234)]


def test_an_index_that_is_a_file_on_disk_is_read_without_any_download() -> None:
    fetcher = Fetcher()
    files = Files({Path("/market/index.toml"): index_text()})
    assert market(fetcher, files).index("/market/index.toml").find("research_pack") is not None
    assert fetcher.asked == []


def test_an_address_that_is_neither_a_file_nor_https_is_refused_and_nothing_is_contacted() -> None:
    fetcher = Fetcher()
    for address in ("http://plugins.example.com/i.toml", "ftp://x.example/i.toml", "file:///etc/x"):
        error = refused(
            lambda address=address: market(fetcher).index(address), "PLUGIN_INDEX_REFUSED"
        )  # type: ignore[misc]
        assert "a file on disk or an https:// address" in error.message
    assert fetcher.asked == []


def test_a_missing_or_unreadable_index_file_is_refused() -> None:
    error = refused(lambda: market(Fetcher()).index("/market/none.toml"), "PLUGIN_INDEX_MISSING")
    assert "there is no index at /market/none.toml" in error.message
    files = Files()
    files.broken[Path("/market/link.toml")] = ApplicationError(
        code="SKILL_FILE_UNUSABLE", message="a link"
    )
    refused(lambda: market(Fetcher(), files).index("/market/link.toml"), "SKILL_FILE_UNUSABLE", 400)


def test_an_index_that_is_not_an_index_is_refused() -> None:
    fetcher = Fetcher({INDEX_URL: b'version = 1\ncommand = "sh"\n'})
    error = refused(lambda: market(fetcher).index(INDEX_URL), "PLUGIN_INDEX_INVALID")
    assert "unknown top-level key" in error.message


def test_a_download_failure_is_passed_on_unchanged() -> None:
    fetcher = Fetcher(
        {INDEX_URL: ApplicationError(code="BUNDLE_NOT_FOUND", message="x answered 404")}
    )
    refused(lambda: market(fetcher).index(INDEX_URL), "BUNDLE_NOT_FOUND", 400)


# ----------------------------------------------------------------------------------- download
def downloaded() -> tuple[Fetcher, Files]:
    return Fetcher({URL: BUNDLE}), Files({Path("/market/index.toml"): index_text()})


def test_a_download_is_saved_beside_the_folder_given_and_nothing_is_installed() -> None:
    fetcher, files = downloaded()
    result = market(fetcher, files, 999).download("/market/index.toml", "research_pack", FOLDER)
    assert result.path == FOLDER / "research_pack.toml"
    assert files.writes == [(FOLDER / "research_pack.toml", BUNDLE, False)]
    assert result.bundle.sha256 == DIGEST and result.bundle.plugin.identifier() == "research_pack@1"
    assert result.entry.url == URL and fetcher.asked == [(URL, 999)]


def test_a_plugin_the_index_does_not_list_is_refused_before_anything_is_downloaded() -> None:
    fetcher, files = downloaded()
    error = refused(
        lambda: market(fetcher, files).download("/market/index.toml", "other_pack", FOLDER),
        "PLUGIN_NOT_IN_INDEX",
    )
    assert "lists no plugin named 'other_pack'" in error.message
    assert fetcher.asked == [] and files.writes == []


def test_bytes_that_are_not_what_the_index_promised_are_refused_before_they_are_read() -> None:
    junk = b"this is = = not toml and not the promised file"
    fetcher = Fetcher({URL: junk})
    files = Files({Path("/market/index.toml"): index_text()})
    error = refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "PLUGIN_HASH_MISMATCH",
    )
    assert f"starts {hashlib.sha256(junk).hexdigest()[:12]}" in error.message
    assert f"index's starts {DIGEST[:12]}" in error.message and "nothing was saved" in error.message
    assert files.writes == []


def test_the_bytes_are_checked_for_exactly_the_hash_in_the_index() -> None:
    changed = BUNDLE.replace(b"short", b"Short")
    fetcher = Fetcher({URL: changed})
    files = Files({Path("/market/index.toml"): index_text()})
    refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "PLUGIN_HASH_MISMATCH",
    )


def test_a_file_that_matches_its_hash_but_is_not_a_plugin_is_refused_and_not_saved() -> None:
    junk = b"this is = = not toml"
    fetcher = Fetcher({URL: junk})
    files = Files({Path("/market/index.toml"): index_text(sha=hashlib.sha256(junk).hexdigest())})
    error = refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "PLUGIN_INVALID",
    )
    assert "it is not valid TOML" in error.message and files.writes == []


def test_a_plugin_that_names_itself_otherwise_than_the_index_does_is_refused() -> None:
    other = BUNDLE.replace(b'name = "research_pack"', b'name = "other_pack"', 1)
    fetcher = Fetcher({URL: other})
    files = Files({Path("/market/index.toml"): index_text(sha=hashlib.sha256(other).hexdigest())})
    error = refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "PLUGIN_INVALID",
    )
    assert "names itself 'other_pack', not 'research_pack'" in error.message and files.writes == []


def test_a_version_other_than_the_one_the_index_lists_is_refused() -> None:
    fetcher = Fetcher({URL: BUNDLE})
    files = Files({Path("/market/index.toml"): index_text(version=2)})
    error = refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "PLUGIN_VERSION_MISMATCH",
    )
    assert "lists research_pack@2, but the file is research_pack@1" in error.message
    assert files.writes == []


def test_a_file_already_there_is_never_overwritten() -> None:
    fetcher = Fetcher({URL: BUNDLE})
    existing = FOLDER / "research_pack.toml"
    files = Files({Path("/market/index.toml"): index_text(), existing: b"mine"})
    error = refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "PLUGIN_FILE_EXISTS",
        409,
    )
    assert "choose another --output folder" in error.message
    assert files.files[existing] == b"mine" and files.writes == []


def test_a_download_that_fails_is_passed_on_and_saves_nothing() -> None:
    fetcher = Fetcher(
        {URL: ApplicationError(code="BUNDLE_TOO_LARGE", message="x sent more than 5 bytes")}
    )
    files = Files({Path("/market/index.toml"): index_text()})
    refused(
        lambda: market(fetcher, files).download("/market/index.toml", "research_pack", FOLDER),
        "BUNDLE_TOO_LARGE",
        400,
    )
    assert files.writes == []
