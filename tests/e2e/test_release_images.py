# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The release pushes both images only from the commit it released, and never over a tag built from another."""

import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILT = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
OTHER = "ffffffffffffffffffffffffffffffffffffffff"
DIGEST = "sha256:" + "ab" * 32

FAKE_DOCKER = """#!/bin/sh
# A stand-in for docker: it records each call, and answers from the FAKE_* variables.
echo "$*" >> "$FAKE_LOG"
case "$1" in
  login) cat >/dev/null ;;
  manifest)
    case "$FAKE_REGISTRY" in
      "") echo "no such manifest: $3" >&2; exit 1 ;;
      error) echo "unauthorized: authentication required" >&2; exit 1 ;;
      *) : ;;
    esac ;;
  inspect)
    case "$*" in
      *Labels*) printf '%s\\n' "$FAKE_REVISION" ;;
      *RepoDigests*) printf '%s\\n' "ghcr.io/owner/repo@$FAKE_DIGEST" ;;
    esac ;;
  run) printf '%s\\n' "$FAKE_REPORTED" ;;
  build|pull|push|tag) : ;;
esac
"""


def workflow() -> dict[str, object]:
    return yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())  # type: ignore[no-any-return]


def job() -> dict[str, object]:
    found = workflow()["jobs"]["images"]  # type: ignore[index]
    assert isinstance(found, dict)
    return found


def step_script() -> str:
    steps: list[dict[str, str]] = job()["steps"]  # type: ignore[assignment]
    publish = next(s for s in steps if s.get("name") == "Build, check and push both images")
    return publish["run"]


def run_step(
    tmp_path: Path,
    version: str = "0.1.0",
    registry: str = "",
    revision: str = BUILT,
    reported: str | None = None,
    repository: str = "Owner/Repo",
) -> tuple[subprocess.CompletedProcess[str], list[str], dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "docker"
    fake.write_text(FAKE_DOCKER)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "docker.log"
    log.write_text("")
    out = tmp_path / "output"
    out.write_text("")
    done = subprocess.run(
        ["sh", "-e", "-c", step_script()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "GITHUB_TOKEN": "not-a-real-token",
            "GITHUB_ACTOR": "someone",
            "GITHUB_REPOSITORY": repository,
            "GITHUB_SHA": BUILT,
            "GITHUB_OUTPUT": str(out),
            "VERSION": version,
            "FAKE_REGISTRY": registry,
            "FAKE_REVISION": revision,
            "FAKE_REPORTED": reported
            if reported is not None
            else f"engineering-influence {version}",
            "FAKE_DIGEST": DIGEST,
            "FAKE_LOG": str(log),
            "HOME": os.environ.get("HOME", "/"),
        },
        check=False,
    )
    calls = [line for line in log.read_text().splitlines() if line]
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)
    return done, calls, outputs


def pushed(calls: list[str]) -> list[str]:
    return [call.removeprefix("push --quiet ") for call in calls if call.startswith("push")]


def built(calls: list[str]) -> list[str]:
    return [call for call in calls if call.startswith("build")]


# ------------------------------------------------------------------------------ what a release pushes
def test_a_stable_release_builds_both_images_and_moves_the_floating_tags(tmp_path: Path) -> None:
    done, calls, outputs = run_step(tmp_path)

    assert done.returncode == 0, done.stderr
    assert pushed(calls) == [
        "ghcr.io/owner/repo:0.1.0",
        "ghcr.io/owner/repo:latest",
        "ghcr.io/owner/repo:0.1.0-tex",
        "ghcr.io/owner/repo:tex",
    ]
    assert outputs == {
        "image": "ghcr.io/owner/repo",
        "runtime_digest": DIGEST,
        "tex_digest": DIGEST,
    }


@pytest.mark.parametrize("version", ["0.1.0a2", "0.2.0b1", "1.0.0rc3"])
def test_a_pre_release_gets_its_version_tags_and_never_moves_latest(
    tmp_path: Path, version: str
) -> None:
    done, calls, _ = run_step(tmp_path, version=version)

    assert done.returncode == 0, done.stderr
    assert pushed(calls) == [
        f"ghcr.io/owner/repo:{version}",
        f"ghcr.io/owner/repo:{version}-tex",
    ]


def test_each_image_is_built_from_its_own_target_and_says_which_commit_it_came_from(
    tmp_path: Path,
) -> None:
    _, calls, _ = run_step(tmp_path)

    runtime, tex = built(calls)
    assert "--target runtime" in runtime and "--tag ghcr.io/owner/repo:0.1.0 " in runtime
    assert "--target worker-tex" in tex and "--tag ghcr.io/owner/repo:0.1.0-tex " in tex
    for call in (runtime, tex):
        assert f"org.opencontainers.image.revision={BUILT}" in call
        assert "org.opencontainers.image.version=0.1.0" in call
        assert "org.opencontainers.image.source=https://github.com/Owner/Repo" in call


def test_the_registry_name_is_lowercase_whatever_the_repository_is_called(tmp_path: Path) -> None:
    _, calls, outputs = run_step(tmp_path, repository="Adam/Engineering-Influence")

    assert outputs["image"] == "ghcr.io/adam/engineering-influence"
    assert all(call.startswith("ghcr.io/adam/") for call in pushed(calls))


def test_the_login_uses_the_runs_token_on_stdin_and_never_on_the_command_line(
    tmp_path: Path,
) -> None:
    done, calls, _ = run_step(tmp_path)

    (login,) = [call for call in calls if call.startswith("login")]
    assert login == "login ghcr.io --username someone --password-stdin"
    assert "not-a-real-token" not in done.stdout + done.stderr + "".join(calls)


# ------------------------------------------------------------------------------ what it refuses
def test_an_image_that_does_not_report_the_released_version_is_never_pushed(tmp_path: Path) -> None:
    done, calls, outputs = run_step(tmp_path, reported="engineering-influence 0.0.9")

    assert done.returncode == 1
    assert "reports 'engineering-influence 0.0.9', not 0.1.0" in done.stderr
    assert pushed(calls) == [] and outputs == {"image": "ghcr.io/owner/repo"}


def test_a_tag_built_from_this_commit_is_accepted_and_not_built_or_pushed_again(
    tmp_path: Path,
) -> None:
    done, calls, outputs = run_step(tmp_path, registry="present", revision=BUILT, version="0.1.0a2")

    assert done.returncode == 0, done.stderr
    assert "ghcr.io/owner/repo:0.1.0a2 is already published from this commit" in done.stdout
    assert built(calls) == [] and pushed(calls) == []
    assert outputs["runtime_digest"] == DIGEST and outputs["tex_digest"] == DIGEST


def test_a_repeat_run_of_a_stable_release_still_moves_the_floating_tags(tmp_path: Path) -> None:
    done, calls, _ = run_step(tmp_path, registry="present", revision=BUILT)

    assert done.returncode == 0, done.stderr
    assert built(calls) == []
    assert pushed(calls) == ["ghcr.io/owner/repo:latest", "ghcr.io/owner/repo:tex"]


def test_a_tag_built_from_another_commit_stops_the_job_before_anything_is_pushed(
    tmp_path: Path,
) -> None:
    done, calls, outputs = run_step(tmp_path, registry="present", revision=OTHER)

    assert done.returncode == 1
    assert f"ghcr.io/owner/repo:0.1.0 was built from '{OTHER}', not from {BUILT}" in done.stderr
    assert built(calls) == [] and pushed(calls) == []
    assert "runtime_digest" not in outputs


def test_a_tag_with_no_revision_label_is_not_trusted(tmp_path: Path) -> None:
    done, calls, _ = run_step(tmp_path, registry="present", revision="")

    assert done.returncode == 1
    assert "was built from ''" in done.stderr
    assert pushed(calls) == []


def test_an_answer_that_is_not_a_clear_no_such_manifest_stops_the_job(tmp_path: Path) -> None:
    done, calls, _ = run_step(tmp_path, registry="error")

    assert done.returncode == 1
    assert "could not tell whether ghcr.io/owner/repo:0.1.0 exists" in done.stderr
    assert "authentication required" in done.stderr
    assert built(calls) == [] and pushed(calls) == []


# ------------------------------------------------------------------------------ the job's shape
def test_only_a_release_with_the_variable_on_publishes_images_after_the_github_release() -> None:
    assert job()["needs"] == ["guard", "github-release"]
    condition = " ".join(str(job()["if"]).split())
    assert condition == "needs.guard.outputs.kind == 'release' && vars.PUBLISH_IMAGES == 'true'"


def test_the_images_are_pushed_from_an_environment_of_their_own() -> None:
    environment = job()["environment"]
    assert isinstance(environment, dict) and environment["name"] == "ghcr"
    other = {
        spec["environment"]["name"]  # type: ignore[index]
        for name, spec in workflow()["jobs"].items()  # type: ignore[attr-defined]
        if name != "images" and "environment" in spec
    }
    assert "ghcr" not in other


def test_the_job_may_write_packages_and_attest_and_nothing_else() -> None:
    assert job()["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
        "attestations": "write",
    }


def test_the_job_builds_the_commit_that_was_released_and_keeps_no_credentials() -> None:
    checkout = job()["steps"][0]  # type: ignore[index]

    assert checkout["with"] == {"ref": "${{ github.sha }}", "persist-credentials": False}


def test_each_image_gets_its_own_attestation_by_digest_and_pushes_it_to_the_registry() -> None:
    attests = [s for s in job()["steps"] if "attest-build-provenance" in s.get("uses", "")]  # type: ignore[attr-defined]

    assert [a["with"]["subject-digest"] for a in attests] == [
        "${{ steps.publish.outputs.runtime_digest }}",
        "${{ steps.publish.outputs.tex_digest }}",
    ]
    for attest in attests:
        assert attest["with"]["subject-name"] == "${{ steps.publish.outputs.image }}"
        assert attest["with"]["push-to-registry"] is True


def test_every_action_the_job_uses_is_pinned_to_a_full_commit_sha() -> None:
    used = [s["uses"] for s in job()["steps"] if "uses" in s]  # type: ignore[attr-defined]

    assert used
    for reference in used:
        _, _, ref = reference.partition("@")
        assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), reference


def test_nothing_the_run_does_not_control_is_interpolated_into_the_script() -> None:
    assert "${{" not in step_script()
