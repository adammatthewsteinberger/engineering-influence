# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""``ReadinessDoctor``: what a book needs on this machine, found before a run starts."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.author.toml_author_profile_loader import (
    TomlAuthorProfileLoader,
)
from engineering_influence.interfaces.author_profile_loader_interface import (
    AuthorProfileLoaderInterface,
)
from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface
from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.services.interfaces.readiness_doctor_interface import (
    ReadinessDoctorInterface,
)
from engineering_influence.services.readiness_doctor import ReadinessDoctor

ROOT = Path(__file__).resolve().parents[3]
EVERY_TOOL = {"lualatex", "latexmk", "tex4ebook", "zip", "epubcheck", "pdftoppm", "mutool"}
PROFILE = Path("author.toml")


class Finder(ExecutableFinderInterface):
    def __init__(self, present: set[str]) -> None:
        self.present = present
        self.asked: list[str] = []

    def find(self, name: str) -> str | None:
        self.asked.append(name)
        return f"/usr/bin/{name}" if name in self.present else None


class Loader(AuthorProfileLoaderInterface):
    def __init__(self, answer: AuthorProfile | None | ApplicationError) -> None:
        self.answer = answer
        self.asked: list[Path] = []

    def load(self, path: Path) -> AuthorProfile | None:
        self.asked.append(path)
        if isinstance(self.answer, ApplicationError):
            raise self.answer
        return self.answer


def a_profile() -> AuthorProfile:
    loaded = TomlAuthorProfileLoader().load(ROOT / "examples" / "author-profile.example.toml")
    assert loaded is not None
    return loaded


def doctor(
    missing_modules: frozenset[str] = frozenset(),
    tools: set[str] | None = None,
    loader: Loader | None = None,
) -> tuple[ReadinessDoctor, Finder, Loader]:
    finder = Finder(EVERY_TOOL if tools is None else tools)
    used = loader or Loader(a_profile())
    return ReadinessDoctor(lambda module: module not in missing_modules, finder, used), finder, used


def by_check(findings: tuple[DoctorFinding, ...]) -> dict[str, DoctorFinding]:
    return {finding.check: finding for finding in findings}


def test_it_is_a_readiness_doctor_and_a_ready_machine_passes_every_check() -> None:
    ready, _, loader = doctor()
    assert isinstance(ready, ReadinessDoctorInterface)

    findings = ready.check(PROFILE)

    assert [finding.check for finding in findings] == [
        "extra runtime",
        "extra publishing",
        "tool lualatex",
        "tool latexmk",
        "tool tex4ebook",
        "tool zip",
        "tool epubcheck (optional)",
        "tool page images",
        "author profile",
    ]
    assert all(finding.passed and finding.profile == "install" for finding in findings)
    assert by_check(findings)["tool lualatex"].detail == "/usr/bin/lualatex"
    assert by_check(findings)["author profile"].detail == "author.toml reads as a profile"
    assert loader.asked == [PROFILE]


@pytest.mark.parametrize(
    ("module", "extra"),
    [
        ("sqlmodel", "runtime"),
        ("alembic", "runtime"),
        ("httpx", "runtime"),
        ("vibey_bootstrap", "runtime"),
        ("markdown_it", "publishing"),
        ("pypdf", "publishing"),
        ("pdfplumber", "publishing"),
        ("defusedxml", "publishing"),
    ],
)
def test_a_missing_module_fails_its_extra_only_and_says_which_extra_to_install(
    module: str, extra: str
) -> None:
    ready, _, _ = doctor(missing_modules=frozenset({module}))

    findings = by_check(ready.check(PROFILE))

    failed = [check for check, finding in findings.items() if not finding.passed]
    assert failed == [f"extra {extra}"]
    assert findings[f"extra {extra}"].detail == (
        f"missing {module}: install engineering-influence with the [{extra}] extra"
    )


def test_every_missing_module_of_an_extra_is_named_together() -> None:
    ready, _, _ = doctor(missing_modules=frozenset({"sqlmodel", "httpx"}))

    assert "missing sqlmodel, httpx:" in by_check(ready.check(PROFILE))["extra runtime"].detail


@pytest.mark.parametrize(
    ("tool", "purpose"),
    [
        ("lualatex", "the interior PDF"),
        ("latexmk", "the interior PDF"),
        ("tex4ebook", "the EPUB"),
        ("zip", "the EPUB"),
    ],
)
def test_a_missing_tool_fails_its_own_check_and_says_what_the_build_needs_it_for(
    tool: str, purpose: str
) -> None:
    ready, _, _ = doctor(tools=EVERY_TOOL - {tool})

    findings = by_check(ready.check(PROFILE))

    assert [check for check, finding in findings.items() if not finding.passed] == [f"tool {tool}"]
    assert findings[f"tool {tool}"].detail == (
        f"not on PATH; the build stage needs it for {purpose} "
        "(docs/WORKER_IMAGE.md lists the packages)"
    )


@pytest.mark.parametrize(
    ("present", "found"), [("pdftoppm", "/usr/bin/pdftoppm"), ("mutool", "/usr/bin/mutool")]
)
def test_either_rasteriser_will_do_for_the_page_images(present: str, found: str) -> None:
    ready, _, _ = doctor(tools=(EVERY_TOOL - {"pdftoppm", "mutool"}) | {present})

    finding = by_check(ready.check(PROFILE))["tool page images"]

    assert finding.passed and finding.detail == found


def test_poppler_is_preferred_when_both_rasterisers_are_there() -> None:
    ready, _, _ = doctor()

    assert by_check(ready.check(PROFILE))["tool page images"].detail == "/usr/bin/pdftoppm"


def test_with_no_rasteriser_the_page_check_is_named_as_what_cannot_run() -> None:
    ready, _, _ = doctor(tools=EVERY_TOOL - {"pdftoppm", "mutool"})

    finding = by_check(ready.check(PROFILE))["tool page images"]

    assert not finding.passed
    assert finding.detail == (
        "neither pdftoppm (poppler) nor mutool is on PATH; the page check needs one of them"
    )


def test_no_profile_named_fails_and_points_at_the_starter_without_reading_any_file() -> None:
    ready, _, loader = doctor()

    finding = by_check(ready.check(None))["author profile"]

    assert not finding.passed and loader.asked == []
    assert finding.detail == (
        "none named: set EI_AUTHOR_PROFILE or pass --author-profile FILE "
        "(examples/author-profile.example.toml is a starting point)"
    )


def test_a_named_file_that_is_not_there_fails() -> None:
    ready, _, _ = doctor(loader=Loader(None))

    finding = by_check(ready.check(PROFILE))["author profile"]

    assert not finding.passed and finding.detail == "there is no file at author.toml"


def test_a_file_that_is_not_a_profile_fails_with_the_readers_own_reason() -> None:
    refusal = ApplicationError(code="AUTHOR_PROFILE_INVALID", message="it has no author")
    ready, _, _ = doctor(loader=Loader(refusal))

    finding = by_check(ready.check(PROFILE))["author profile"]

    assert not finding.passed and finding.detail == "it has no author"


def test_one_failure_never_hides_another_every_check_is_always_made() -> None:
    ready, finder, _ = doctor(
        missing_modules=frozenset({"sqlmodel", "pypdf"}), tools=set(), loader=Loader(None)
    )

    findings = ready.check(PROFILE)

    failed = [finding.check for finding in findings if not finding.passed]
    assert len(findings) == 9
    assert failed == [
        "extra runtime",
        "extra publishing",
        "tool lualatex",
        "tool latexmk",
        "tool tex4ebook",
        "tool zip",
        "tool page images",
        "author profile",
    ]
    assert finder.asked == [
        "lualatex",
        "latexmk",
        "tex4ebook",
        "zip",
        "epubcheck",
        "pdftoppm",
        "mutool",
    ]


def test_the_starter_profile_in_the_examples_is_a_valid_profile_with_placeholder_details() -> None:
    profile = a_profile()

    assert profile.author == "Your Name" and profile.publisher == "Your Imprint"
    assert profile.pricing is None


def test_epubcheck_is_optional_its_absence_passes_and_says_what_is_lost() -> None:
    ready, _, _ = doctor(tools=EVERY_TOOL - {"epubcheck"})

    findings = ready.check(PROFILE)

    finding = by_check(findings)["tool epubcheck (optional)"]
    assert all(f.passed for f in findings)
    assert finding.detail == (
        "not on PATH: the EPUB gets the built-in checks only, and a strict release will refuse to build"
    )


def test_an_installed_epubcheck_is_reported_where_it_is() -> None:
    ready, _, _ = doctor()

    assert (
        by_check(ready.check(PROFILE))["tool epubcheck (optional)"].detail == "/usr/bin/epubcheck"
    )
