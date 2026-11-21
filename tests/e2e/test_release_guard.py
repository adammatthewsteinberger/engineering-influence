"""The release workflow's guard decides whether a tag may publish; test the real script."""

import fnmatch
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


def test_a_tag_with_an_unfolded_changelog_fragment_is_refused(repo: Path) -> None:
    write(repo, "changelog.d/README.md", "how to\n")
    write(repo, "changelog.d/a-change.md", "A change.\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fragment")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    result = run_guard(repo, f"v{VERSION}")

    assert result.returncode == 1
    assert "changelog.d/a-change.md is an unfolded changelog fragment" in result.stderr


def test_the_fragments_readme_alone_does_not_block_a_release(repo: Path) -> None:
    write(repo, "changelog.d/README.md", "how to\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "readme")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    assert run_guard(repo, f"v{VERSION}").returncode == 0


def release_jobs() -> dict[str, dict[str, object]]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    return jobs


PUBLISHING = {
    # job: (index host or None for PyPI, file stem, environment)
    "testpypi": ("test.pypi.org", "engineering_influence", "testpypi"),
    "testpypi-sdk": ("test.pypi.org", "engineering_influence_sdk", "testpypi-sdk"),
    "pypi": (None, "engineering_influence", "pypi"),
    "pypi-sdk": (None, "engineering_influence_sdk", "pypi-sdk"),
}
BUILT = [
    "engineering_influence-0.1.0a2-py3-none-any.whl",
    "engineering_influence-0.1.0a2.tar.gz",
    "engineering_influence_sdk-0.1.0a2-py3-none-any.whl",
    "engineering_influence_sdk-0.1.0a2.tar.gz",
    "SHA256SUMS",
    "sbom.cdx.json",
]


def publish_step(job: dict[str, object]) -> dict[str, object]:
    steps = [s for s in job["steps"] if "gh-action-pypi-publish" in s.get("uses", "")]
    assert len(steps) == 1
    return steps[0]


def test_the_testpypi_rehearsal_is_off_until_its_own_variable_is_set() -> None:
    jobs = release_jobs()

    for name in ("testpypi", "testpypi-sdk"):
        assert jobs[name]["if"] == "vars.PUBLISH_TO_TESTPYPI == 'true'"
    assert jobs["testpypi"]["needs"] == "github-release"
    assert jobs["testpypi-sdk"]["needs"] == "testpypi"


def test_each_package_is_uploaded_from_an_environment_of_its_own() -> None:
    jobs = release_jobs()

    names = [jobs[name]["environment"]["name"] for name in PUBLISHING]
    assert names == [env for _, _, env in PUBLISHING.values()]
    assert len(set(names)) == 4  # PyPI tells pending publishers apart by environment


def test_every_upload_is_authorised_by_the_runs_identity_and_uses_no_token() -> None:
    for name, (host, _, _) in PUBLISHING.items():
        job = release_jobs()[name]
        assert job["permissions"] == {"id-token": "write"}
        options = publish_step(job)["with"]
        assert not {"password", "user"} & options.keys()
        assert options["attestations"] is True
        assert ("repository-url" in options) is (host is not None)
        if host:
            assert options["repository-url"] == f"https://{host}/legacy/"


def test_each_job_uploads_only_its_own_package_and_not_the_sbom_or_checksums() -> None:
    for name, (_, stem, _) in PUBLISHING.items():
        job = release_jobs()[name]
        move = next(
            s
            for s in job["steps"]
            if s.get("name") == "Keep only the distributions of this package"
        )
        patterns = [word for word in move["run"].split() if word.startswith("dist/")]
        assert patterns == [f"dist/{stem}-*.whl", f"dist/{stem}-*.tar.gz"]
        taken = {f for f in BUILT for p in patterns if fnmatch.fnmatch(f"dist/{f}", p)}
        assert taken == {f for f in BUILT if f.startswith(f"{stem}-")}
        assert publish_step(job)["with"]["packages-dir"] == move["run"].split()[-1]


def test_the_two_packages_never_take_each_others_files() -> None:
    core = {f for f in BUILT if fnmatch.fnmatch(f, "engineering_influence-*")}
    sdk = {f for f in BUILT if fnmatch.fnmatch(f, "engineering_influence_sdk-*")}

    assert len(core) == len(sdk) == 2
    assert not core & sdk


def test_pypi_waits_for_the_rehearsal_and_stops_if_it_failed_but_not_if_it_was_skipped() -> None:
    job = release_jobs()["pypi"]
    condition = " ".join(str(job["if"]).split())

    assert job["needs"] == ["github-release", "testpypi", "testpypi-sdk"]
    assert "always()" in condition
    assert "vars.PUBLISH_TO_PYPI == 'true'" in condition
    assert "needs.github-release.result == 'success'" in condition
    for rehearsal in ("testpypi", "testpypi-sdk"):
        assert f"needs.{rehearsal}.result != 'failure'" in condition
        assert f"needs.{rehearsal}.result != 'cancelled'" in condition
    assert "'skipped'" not in condition  # a skipped rehearsal is allowed, so it is not named


def test_the_sdk_goes_up_to_pypi_only_after_the_core_did() -> None:
    job = release_jobs()["pypi-sdk"]
    condition = " ".join(str(job["if"]).split())

    assert job["needs"] == "pypi"
    assert "always()" in condition
    assert "vars.PUBLISH_TO_PYPI == 'true'" in condition
    assert "needs.pypi.result == 'success'" in condition


def test_every_publishing_chain_starts_after_the_github_release() -> None:
    jobs = release_jobs()

    assert jobs["testpypi"]["needs"] == "github-release"
    assert "github-release" in jobs["pypi"]["needs"]
