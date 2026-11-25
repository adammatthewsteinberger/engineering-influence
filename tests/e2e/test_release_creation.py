# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The release step must never attach the built files to a tag that names a different commit."""

import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILT = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
OTHER = "ffffffffffffffffffffffffffffffffffffffff"
TAG_OBJECT = "0123456789abcdef0123456789abcdef01234567"

FAKE_GH = """#!/bin/sh
# A stand-in for gh: it records each call, and answers from FAKE_TAG, FAKE_PEELED and FAKE_RELEASE.
echo "$*" >> "$FAKE_LOG"
case "$1" in
  api)
    case "$2" in
      */git/ref/tags/*)
        case "$FAKE_TAG" in
          "") echo "gh: Not Found (HTTP 404)" >&2; exit 1 ;;
          error) echo "gh: Bad credentials (HTTP 401)" >&2; exit 1 ;;
          commit:*) echo "commit ${FAKE_TAG#commit:}" ;;
          tag:*) echo "tag ${FAKE_TAG#tag:}" ;;
        esac ;;
      */git/tags/*) echo "$FAKE_PEELED" ;;
    esac ;;
  release)
    case "$2" in
      view) [ "$FAKE_RELEASE" = yes ] ;;
      create) : ;;
    esac ;;
esac
"""


def step_script() -> str:
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["github-release"]["steps"]
    return str(next(s for s in steps if s.get("name") == "Create the GitHub release")["run"])


def run_step(
    tmp_path: Path, tag_state: str, release: str = "no", peeled: str = BUILT, tag: str = "v0.1.0a2"
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "gh"
    fake.write_text(FAKE_GH)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    work = tmp_path / "work"
    (work / "dist").mkdir(parents=True, exist_ok=True)
    (work / "dist" / "a.whl").write_text("x")
    log = tmp_path / "gh.log"
    log.write_text("")
    done = subprocess.run(
        ["sh", "-e", "-c", step_script()],
        cwd=work,
        capture_output=True,
        text=True,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "GH_TOKEN": "not-a-real-token",
            "GITHUB_REPOSITORY": "owner/repo",
            "TAG": tag,
            "TARGET": BUILT,
            "FAKE_TAG": tag_state,
            "FAKE_PEELED": peeled,
            "FAKE_RELEASE": release,
            "FAKE_LOG": str(log),
            "HOME": os.environ.get("HOME", "/"),
        },
        check=False,
    )
    return done, [line for line in log.read_text().splitlines() if line]


def created(calls: list[str]) -> list[str]:
    return [call for call in calls if call.startswith("release create")]


def test_a_tag_that_does_not_exist_yet_is_created_at_the_built_commit(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, "")

    assert done.returncode == 0, done.stderr
    assert "v0.1.0a2 does not exist yet" in done.stdout
    (create,) = created(calls)
    assert f"--target {BUILT}" in create and "dist/a.whl" in create


def test_a_tag_that_already_points_at_the_built_commit_is_accepted(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, f"commit:{BUILT}")

    assert done.returncode == 0, done.stderr
    assert len(created(calls)) == 1


def test_an_annotated_tag_is_followed_to_the_commit_it_names(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, f"tag:{TAG_OBJECT}", peeled=BUILT)

    assert done.returncode == 0, done.stderr
    assert any(call.startswith(f"api repos/owner/repo/git/tags/{TAG_OBJECT}") for call in calls)
    assert len(created(calls)) == 1


def test_a_tag_that_points_at_another_commit_stops_the_release_before_anything_is_created(
    tmp_path: Path,
) -> None:
    done, calls = run_step(tmp_path, f"commit:{OTHER}")

    assert done.returncode == 1
    assert f"tag v0.1.0a2 points at {OTHER}, not at the built commit {BUILT}" in done.stderr
    assert created(calls) == []
    assert not any(call.startswith("release view") for call in calls)


def test_an_annotated_tag_that_names_another_commit_stops_the_release(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, f"tag:{TAG_OBJECT}", peeled=OTHER)

    assert done.returncode == 1
    assert f"points at {OTHER}" in done.stderr
    assert created(calls) == []


def test_an_answer_that_is_not_a_clear_not_found_stops_the_release(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, "error")

    assert done.returncode == 1
    assert "could not tell whether v0.1.0a2 exists" in done.stderr
    assert "Bad credentials" in done.stderr
    assert created(calls) == []


def test_a_release_that_already_exists_for_the_right_commit_is_left_alone(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, f"commit:{BUILT}", release="yes")

    assert done.returncode == 0, done.stderr
    assert "v0.1.0a2 is already released" in done.stdout
    assert created(calls) == []


def test_an_existing_release_does_not_excuse_a_tag_on_the_wrong_commit(tmp_path: Path) -> None:
    done, calls = run_step(tmp_path, f"commit:{OTHER}", release="yes")

    assert done.returncode == 1
    assert created(calls) == []


@pytest.mark.parametrize("tag", ["v0.1.0a2", "v1.0.0b3", "v2.0.0rc1", "v0.1.0a12"])
def test_a_pre_release_version_is_marked_as_one(tmp_path: Path, tag: str) -> None:
    done, calls = run_step(tmp_path, "", tag=tag)

    assert done.returncode == 0, done.stderr
    assert created(calls)[0].endswith("--prerelease")


@pytest.mark.parametrize("tag", ["v1.0.0", "v10.20.30", "v0.1.0"])
def test_a_stable_version_is_not_marked_as_a_pre_release(tmp_path: Path, tag: str) -> None:
    done, calls = run_step(tmp_path, "", tag=tag)

    assert done.returncode == 0, done.stderr
    assert "--prerelease" not in created(calls)[0]


def test_the_release_is_titled_and_noted_by_its_tag(tmp_path: Path) -> None:
    _, calls = run_step(tmp_path, "")

    (create,) = created(calls)
    assert create.startswith("release create v0.1.0a2 dist/a.whl --repo owner/repo")
    assert "--generate-notes --title v0.1.0a2" in create


def test_the_tag_is_looked_up_before_the_release(tmp_path: Path) -> None:
    _, calls = run_step(tmp_path, f"commit:{BUILT}")

    kinds = [call.split()[0] + " " + call.split()[1] for call in calls]
    assert kinds.index("api repos/owner/repo/git/ref/tags/v0.1.0a2") < kinds.index("release view")


def test_the_api_calls_are_the_ones_checked_by_hand_against_the_real_github_api(
    tmp_path: Path,
) -> None:
    """The fake answers with extracted values, so the exact requests are pinned here instead."""
    _, calls = run_step(tmp_path, f"tag:{TAG_OBJECT}", peeled=BUILT)

    assert calls[0] == (
        'api repos/owner/repo/git/ref/tags/v0.1.0a2 --jq .object.type + " " + .object.sha'
    )
    assert calls[1] == f"api repos/owner/repo/git/tags/{TAG_OBJECT} --jq .object.sha"
