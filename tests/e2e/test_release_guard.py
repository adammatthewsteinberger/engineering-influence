"""The release workflow's guard decides whether a tag may publish; test the real script."""

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0a1"


def guard_script() -> str:
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["guard"]["steps"]
    return str(next(s for s in steps if s.get("name", "").startswith("The tag must match"))["run"])


def git(repo: Path, *arguments: str) -> str:
    done = subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "-c",
            "core.hooksPath=/dev/null",
            *arguments,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository whose HEAD is on main, with matching versions and a changelog section."""
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "src/engineering_influence/__init__.py", f'__version__ = "{VERSION}"\n')
    write(
        tmp_path,
        "packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py",
        f'__version__ = "{VERSION}"\n',
    )
    write(tmp_path, "CHANGELOG.md", f"# Changelog\n\n## Unreleased\n\n## {VERSION}\n\n- first\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "snapshot")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def run_guard(
    repo: Path, tag: str, github_sha: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the guard with the repository checked out at the commit under test (HEAD)."""
    return subprocess.run(
        ["sh", "-e", "-c", guard_script()],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "TAG": tag,
            "GITHUB_SHA": github_sha or git(repo, "rev-parse", "HEAD"),
        },
        check=False,
    )


def test_a_matching_tag_on_main_with_a_changelog_section_may_release(repo: Path) -> None:
    result = run_guard(repo, f"v{VERSION}")

    assert result.returncode == 0, result.stderr
    assert f"releasing {VERSION}" in result.stdout


@pytest.mark.parametrize("heading", [f"## [{VERSION}] - 2026-11-04", f"## {VERSION} (2026-11-04)"])
def test_the_usual_changelog_heading_styles_are_accepted(repo: Path, heading: str) -> None:
    write(repo, "CHANGELOG.md", f"# Changelog\n\n{heading}\n\n- first\n")

    assert run_guard(repo, f"v{VERSION}").returncode == 0


def test_a_tag_that_does_not_match_the_version_is_refused(repo: Path) -> None:
    result = run_guard(repo, "v9.9.9")

    assert result.returncode == 1
    assert "does not match version" in result.stderr


def test_core_and_sdk_must_release_the_same_version(repo: Path) -> None:
    write(
        repo,
        "packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py",
        '__version__ = "0.0.1"\n',
    )

    result = run_guard(repo, f"v{VERSION}")

    assert result.returncode == 1 and "versions differ" in result.stderr


def test_an_unreadable_version_fails_closed(repo: Path) -> None:
    write(repo, "src/engineering_influence/__init__.py", "# no version here\n")

    result = run_guard(repo, f"v{VERSION}")

    assert result.returncode == 1 and "could not read the package version" in result.stderr


def test_the_changelog_must_have_a_section_for_the_version(repo: Path) -> None:
    write(repo, "CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- not cut yet\n")

    result = run_guard(repo, f"v{VERSION}")

    assert result.returncode == 1 and "has no '## 0.1.0a1' section" in result.stderr


@pytest.mark.parametrize("heading", ["## 0x1x0a1", "## 0.1.0a10", "## 10.1.0a1", "## 0.1.0a"])
def test_a_changelog_heading_for_a_different_version_does_not_count(
    repo: Path, heading: str
) -> None:
    write(repo, "CHANGELOG.md", f"# Changelog\n\n{heading}\n")

    assert run_guard(repo, f"v{VERSION}").returncode == 1


def test_a_tag_that_is_not_on_main_is_refused(repo: Path) -> None:
    git(repo, "commit", "-q", "--allow-empty", "-m", "work after main")

    result = run_guard(repo, f"v{VERSION}")

    assert result.returncode == 1 and "is not on the main branch" in result.stderr


def test_the_guard_judges_the_checked_out_tag_not_the_ref_that_started_the_run(repo: Path) -> None:
    """A hand-started run has GITHUB_SHA of the dispatching branch, which can be anything."""
    tagged = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-q", "--allow-empty", "-m", "work after the tag")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "-q", tagged)  # HEAD is the tagged commit, an ancestor of main

    result = run_guard(
        repo, f"v{VERSION}", github_sha=git(repo, "rev-parse", "refs/remotes/origin/main")
    )

    assert result.returncode == 0, result.stderr


def test_a_tag_commit_off_main_is_refused_even_when_the_dispatching_ref_is_on_it(
    repo: Path,
) -> None:
    main_tip = git(repo, "rev-parse", "HEAD")
    git(
        repo, "commit", "-q", "--allow-empty", "-m", "side work"
    )  # HEAD, the tag's commit, leaves main

    result = run_guard(repo, f"v{VERSION}", github_sha=main_tip)

    assert result.returncode == 1 and "is not on the main branch" in result.stderr


def release_triggers() -> dict[str, object]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))  # PyYAML reads a bare `on:` key as True
    assert isinstance(triggers, dict)
    return triggers


def test_the_release_can_be_started_by_hand_for_an_existing_tag() -> None:
    triggers = release_triggers()

    assert triggers["push"] == {"tags": ["v*"]}
    assert triggers["workflow_dispatch"]["inputs"]["tag"]["required"] is True


def test_every_stage_of_the_release_uses_the_same_tag() -> None:
    text = (ROOT / ".github/workflows/release.yml").read_text()
    expression = "inputs.tag || github.ref_name"

    assert text.count(expression) == 5  # concurrency, checkout, guard, build, release
    assert "github.ref_name" not in text.replace(expression, "")
