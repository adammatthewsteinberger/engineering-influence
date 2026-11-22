# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The build workflow's stage step: a development build is stamped in a copy, never in the checkout."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CORE = "src/engineering_influence/__init__.py"
SDK = "packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py"


def build_workflow() -> dict[object, object]:
    loaded = yaml.safe_load((ROOT / ".github/workflows/build-distribution.yml").read_text())
    assert isinstance(loaded, dict)
    return loaded


def steps() -> list[dict[str, object]]:
    return build_workflow()["jobs"]["build"]["steps"]  # type: ignore[index,no-any-return]


def step(identifier: str) -> dict[str, object]:
    return next(s for s in steps() if s.get("id") == identifier)


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A committed repository with both version files and the stamping script, as the runner has."""
    repo = tmp_path / "checkout"
    for relative in (CORE, SDK):
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).write_text('__version__ = "0.1.0a1"\n')
    (repo / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "stamp_dev_version.py", repo / "scripts")
    for command in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "snapshot"],
    ):
        subprocess.run(["git", *command], cwd=repo, check=True, capture_output=True)
    return repo


def run_stage(
    checkout: Path, dev_build: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    output = checkout.parent / "github-output"
    output.write_text("")
    runner = checkout.parent / "runner"
    runner.mkdir(exist_ok=True)
    done = subprocess.run(
        ["sh", "-e", "-c", str(step("stage")["run"])],
        cwd=checkout,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "DEV_BUILD": dev_build,
            "RUNNER_TEMP": str(runner),
            "GITHUB_OUTPUT": str(output),
            "PWD": str(checkout),
        },
        check=False,
    )
    pairs = [line.split("=", 1) for line in output.read_text().splitlines()]
    return done, dict(pairs)  # type: ignore[arg-type]


def test_a_development_build_is_stamped_in_a_copy_and_the_checkout_is_left_alone(
    checkout: Path,
) -> None:
    done, found = run_stage(checkout, "42")

    assert done.returncode == 0, done.stderr
    stage = Path(found["source"])
    assert stage != checkout and stage.name == "dev-source"
    assert found["stamped"] == "0.1.0a1.dev42"
    for relative in (CORE, SDK):
        assert (stage / relative).read_text() == '__version__ = "0.1.0a1.dev42"\n'
        assert (checkout / relative).read_text() == '__version__ = "0.1.0a1"\n'


def test_the_copy_holds_the_committed_files_and_not_the_git_history(checkout: Path) -> None:
    done, found = run_stage(checkout, "1")

    assert done.returncode == 0, done.stderr
    stage = Path(found["source"])
    assert (stage / "scripts" / "stamp_dev_version.py").exists()
    assert not (stage / ".git").exists()


def test_a_release_build_is_made_in_place_with_nothing_stamped(checkout: Path) -> None:
    done, found = run_stage(checkout, "")

    assert done.returncode == 0, done.stderr
    assert found == {"source": str(checkout)}
    assert (checkout / CORE).read_text() == '__version__ = "0.1.0a1"\n'
    assert not (checkout.parent / "runner" / "dev-source").exists()


@pytest.mark.parametrize("number", ["abc", "1.5", "-3", "1 2", "$(touch pwned)", "1;touch pwned"])
def test_a_build_number_that_is_not_digits_stops_the_build_and_runs_nothing(
    checkout: Path, number: str
) -> None:
    done, found = run_stage(checkout, number)

    assert done.returncode != 0
    assert "digits only" in done.stderr
    assert found == {}
    assert not (checkout / "pwned").exists()


def test_a_second_run_starts_from_a_clean_copy(checkout: Path) -> None:
    run_stage(checkout, "5")
    done, found = run_stage(checkout, "6")

    assert done.returncode == 0, done.stderr
    assert found["stamped"] == "0.1.0a1.dev6"


def test_the_version_comes_from_the_stamp_when_there_is_one() -> None:
    version = step("version")

    assert version["env"] == {"STAMPED": "${{ steps.stage.outputs.stamped }}"}
    assert "${STAMPED:-" in str(version["run"])


def test_the_packages_are_built_from_the_staged_source_into_the_checkouts_dist() -> None:
    build = next(s for s in steps() if s.get("name") == "Build both distributions")

    assert build["env"] == {"SOURCE": "${{ steps.stage.outputs.source }}"}
    script = str(build["run"])
    assert script.index("git log -1") < script.index(
        'cd "$SOURCE"'
    )  # the timestamp is the checkout's
    assert 'out="$PWD/dist"' in script
    assert script.count('--out-dir "$out"') == 2


def test_only_a_development_build_checks_the_stamped_files_install_and_report_their_version() -> (
    None
):
    check = next(
        s for s in steps() if s.get("name") == "Install the development build and check its version"
    )

    assert check["if"] == "inputs.dev_build != ''"
    assert check["env"] == {"EXPECTED": "${{ steps.version.outputs.version }}"}
    assert "engineering-influence $EXPECTED" in str(check["run"])
    assert "import engineering_influence_sdk" in str(check["run"])


def test_the_input_defaults_to_a_release_build_so_ci_is_unchanged() -> None:
    inputs = build_workflow()[True if True in build_workflow() else "on"]["workflow_call"]["inputs"]  # type: ignore[index]

    assert inputs["dev_build"]["default"] == ""
    assert inputs["dev_build"]["type"] == "string"
