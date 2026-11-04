"""A release is only coherent if the version is the same everywhere it appears."""

import tomllib
from pathlib import Path

import engineering_influence_sdk
import pytest

import engineering_influence
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.api.api_guard import ApiGuard
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.interaction.cli.main import CliApplication

ROOT = Path(__file__).resolve().parents[2]


def test_the_two_distributions_release_in_step() -> None:
    assert engineering_influence.__version__ == engineering_influence_sdk.__version__


def test_the_version_is_a_pep_440_release_number() -> None:
    from packaging.version import Version

    assert str(Version(engineering_influence.__version__)) == engineering_influence.__version__


@pytest.mark.parametrize(
    "pyproject", ["pyproject.toml", "packages/engineering-influence-sdk/pyproject.toml"]
)
def test_pyproject_reads_the_version_from_the_package_instead_of_repeating_it(
    pyproject: str,
) -> None:
    path = ROOT / pyproject
    data = tomllib.loads(path.read_text())

    assert "version" not in data["project"]
    assert "version" in data["project"]["dynamic"]
    source = path.parent / data["tool"]["hatch"]["version"]["path"]
    assert "__version__ =" in source.read_text()


def test_the_cli_reports_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        CliApplication().run(["--version"])

    assert exit_info.value.code == 0
    assert (
        capsys.readouterr().out.strip()
        == f"engineering-influence {engineering_influence.__version__}"
    )


def test_the_api_reports_the_package_version(api_guard: ApiGuard) -> None:
    app = ApiApplication(InMemoryLedger(), InMemoryQueue(), api_guard).build()

    assert app.version == engineering_influence.__version__


def test_the_changelog_has_an_unreleased_section_to_cut_a_release_from() -> None:
    assert "## Unreleased" in (ROOT / "CHANGELOG.md").read_text()


def test_the_typing_marker_ships_with_both_packages() -> None:
    assert (ROOT / "src/engineering_influence/py.typed").is_file()
    assert (
        ROOT / "packages/engineering-influence-sdk/src/engineering_influence_sdk/py.typed"
    ).is_file()
