"""The release workflow publishes by branch; test the real guard script and the shape of every job."""

import fnmatch
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0a1"
MAIN, DEVELOP = "refs/heads/main", "refs/heads/develop"


def workflow() -> dict[object, object]:
    loaded = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    assert isinstance(loaded, dict)
    return loaded


def guard_script() -> str:
    steps = workflow()["jobs"]["guard"]["steps"]  # type: ignore[index]
    return str(next(s for s in steps if s.get("id") == "guard")["run"])


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


def run_guard(repo: Path, ref: str = MAIN) -> subprocess.CompletedProcess[str]:
    """Run the guard with the repository checked out at the commit under test (HEAD)."""
    output = repo.parent / f"{repo.name}.github-output"
    output.unlink(missing_ok=True)
    return subprocess.run(
        ["sh", "-e", "-c", guard_script()],
        cwd=repo,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "REF": ref, "GITHUB_OUTPUT": str(output)},
        check=False,
    )


def outputs(repo: Path) -> dict[str, str]:
    path = repo.parent / f"{repo.name}.github-output"
    if not path.exists():
        return {}
    return dict(line.split("=", 1) for line in path.read_text().splitlines())


def set_version(repo: Path, version: str) -> None:
    for relative in (
        "src/engineering_influence/__init__.py",
        "packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py",
    ):
        write(repo, relative, f'__version__ = "{version}"\n')


# ----------------------------------------------------------------------------- the guard: a release
def test_a_matching_version_on_main_with_a_changelog_section_may_be_released(repo: Path) -> None:
    result = run_guard(repo, MAIN)

    assert result.returncode == 0, result.stderr
    assert f"release build of {VERSION}" in result.stdout
    assert outputs(repo) == {"kind": "release", "version": VERSION}


@pytest.mark.parametrize("heading", [f"## [{VERSION}] - 2026-11-04", f"## {VERSION} (2026-11-04)"])
def test_the_usual_changelog_heading_styles_are_accepted(repo: Path, heading: str) -> None:
    write(repo, "CHANGELOG.md", f"# Changelog\n\n{heading}\n\n- first\n")

    assert run_guard(repo, MAIN).returncode == 0


def test_the_changelog_must_have_a_section_for_the_version(repo: Path) -> None:
    write(repo, "CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- not cut yet\n")

    result = run_guard(repo, MAIN)

    assert result.returncode == 1 and "has no '## 0.1.0a1' section" in result.stderr
    assert outputs(repo) == {}


@pytest.mark.parametrize("heading", ["## 0x1x0a1", "## 0.1.0a10", "## 10.1.0a1", "## 0.1.0a"])
def test_a_changelog_heading_for_a_different_version_does_not_count(
    repo: Path, heading: str
) -> None:
    write(repo, "CHANGELOG.md", f"# Changelog\n\n{heading}\n")

    assert run_guard(repo, MAIN).returncode == 1


def test_a_release_with_an_unfolded_changelog_fragment_is_refused(repo: Path) -> None:
    write(repo, "changelog.d/README.md", "how to\n")
    write(repo, "changelog.d/a-change.md", "A change.\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fragment")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    result = run_guard(repo, MAIN)

    assert result.returncode == 1
    assert "changelog.d/a-change.md is an unfolded changelog fragment" in result.stderr


def test_the_fragments_readme_alone_does_not_block_a_release(repo: Path) -> None:
    write(repo, "changelog.d/README.md", "how to\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "readme")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    assert run_guard(repo, MAIN).returncode == 0


def test_a_release_commit_that_is_not_on_main_is_refused(repo: Path) -> None:
    git(repo, "commit", "-q", "--allow-empty", "-m", "work after main")

    result = run_guard(repo, MAIN)

    assert result.returncode == 1 and "is not on the main branch" in result.stderr
    assert outputs(repo) == {}


def test_a_commit_that_main_has_since_moved_past_may_still_be_released(repo: Path) -> None:
    """Re-running an older run of main judges that run's commit, which is an ancestor of main now."""
    earlier = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-q", "--allow-empty", "-m", "later work on main")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "-q", earlier)

    assert run_guard(repo, MAIN).returncode == 0


# --------------------------------------------------------------------------- the guard: a development build
def test_a_development_build_needs_none_of_the_release_checks(repo: Path) -> None:
    write(repo, "CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- not cut yet\n")
    write(repo, "changelog.d/a-change.md", "A change.\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "work on develop, past main, with a fragment")

    result = run_guard(repo, DEVELOP)

    assert result.returncode == 0, result.stderr
    assert f"dev build of {VERSION}" in result.stdout
    assert outputs(repo) == {"kind": "dev", "version": VERSION}


# ------------------------------------------------------------------------------- the guard: both kinds
@pytest.mark.parametrize("ref", [MAIN, DEVELOP])
def test_core_and_sdk_must_carry_the_same_version(repo: Path, ref: str) -> None:
    write(
        repo,
        "packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py",
        '__version__ = "0.0.1"\n',
    )

    result = run_guard(repo, ref)

    assert result.returncode == 1 and "versions differ" in result.stderr
    assert outputs(repo) == {}


@pytest.mark.parametrize("ref", [MAIN, DEVELOP])
def test_an_unreadable_version_fails_closed(repo: Path, ref: str) -> None:
    write(repo, "src/engineering_influence/__init__.py", "# no version here\n")

    result = run_guard(repo, ref)

    assert result.returncode == 1 and "could not read the package version" in result.stderr


@pytest.mark.parametrize(
    "version",
    ["0.1.0a1.dev3", "0.1", "v0.1.0", "0.1.0+local", "1.0.0.post1", "0.1.0a", "1.0.0 ", "1..0"],
)
@pytest.mark.parametrize("ref", [MAIN, DEVELOP])
def test_only_a_plain_release_version_is_published(repo: Path, ref: str, version: str) -> None:
    set_version(repo, version)

    result = run_guard(repo, ref)

    assert result.returncode == 1 and "is not a plain release version" in result.stderr
    assert outputs(repo) == {}


@pytest.mark.parametrize("version", ["0.1.0", "10.20.30", "0.1.0a1", "0.1.0b12", "2.0.0rc3"])
def test_the_release_versions_the_project_uses_are_accepted(repo: Path, version: str) -> None:
    set_version(repo, version)

    assert run_guard(repo, DEVELOP).returncode == 0


@pytest.mark.parametrize(
    "ref",
    [
        "refs/heads/feature/x",
        "refs/heads/developer",
        "refs/heads/develop-2",
        "refs/heads/main2",
        "refs/heads/release/main",
        "refs/tags/v0.1.0a1",
        "refs/tags/main",
        "refs/pull/1/merge",
        "develop",
        "main",
        "",
    ],
)
def test_no_other_ref_is_ever_published(repo: Path, ref: str) -> None:
    result = run_guard(repo, ref)

    assert result.returncode == 1 and "only develop and main are published" in result.stderr
    assert outputs(repo) == {}


# ------------------------------------------------------------------------------ the workflow's shape
def jobs() -> dict[str, dict[str, object]]:
    found = workflow()["jobs"]
    assert isinstance(found, dict)
    return found


def condition(job: str) -> str:
    return " ".join(str(jobs()[job]["if"]).split())


def publish_step(job: dict[str, object]) -> dict[str, object]:
    steps = [s for s in job["steps"] if "gh-action-pypi-publish" in s.get("uses", "")]  # type: ignore[attr-defined]
    assert len(steps) == 1
    return steps[0]


def test_the_workflow_runs_on_a_push_to_develop_or_main_and_never_on_a_tag() -> None:
    triggers = workflow().get("on", workflow().get(True))  # PyYAML reads a bare `on:` key as True
    assert isinstance(triggers, dict)

    assert triggers["push"] == {"branches": ["develop", "main"]}
    assert triggers["workflow_dispatch"] in (None, {})


def test_nothing_in_the_workflow_still_refers_to_a_tag_input() -> None:
    text = (ROOT / ".github/workflows/release.yml").read_text()

    assert "inputs.tag" not in text and "ref_name" not in text and "--verify-tag" not in text


def test_runs_for_one_branch_queue_instead_of_cancelling_each_other() -> None:
    assert workflow()["concurrency"] == {
        "group": "release-${{ github.ref }}",
        "cancel-in-progress": False,
    }


def test_the_guard_and_the_build_judge_the_commit_that_started_the_run() -> None:
    guard_checkout = jobs()["guard"]["steps"][0]  # type: ignore[index]

    assert guard_checkout["with"]["ref"] == "${{ github.sha }}"
    assert jobs()["build"]["with"]["ref"] == "${{ github.sha }}"  # type: ignore[index]


def test_the_full_tests_run_for_a_release_and_the_dev_number_only_for_a_development_build() -> None:
    build = jobs()["build"]["with"]  # type: ignore[index]

    assert build["run_tests"] == "${{ needs.guard.outputs.kind == 'release' }}"
    assert "needs.guard.outputs.kind == 'dev'" in build["dev_build"]
    assert "github.run_number" in build["dev_build"]
    assert jobs()["build"]["needs"] == "guard"


def test_only_a_release_creates_the_github_release_and_it_can_be_repeated() -> None:
    job = jobs()["github-release"]
    create = next(s for s in job["steps"] if s.get("name") == "Create the GitHub release")  # type: ignore[attr-defined]

    assert job["if"] == "needs.guard.outputs.kind == 'release'"
    assert job["needs"] == ["guard", "build"]
    assert "gh release view" in create["run"]
    assert "--target" in create["run"] and create["env"]["TARGET"] == "${{ github.sha }}"
    assert create["env"]["TAG"] == "v${{ needs.guard.outputs.version }}"


PUBLISHING = {
    # job: (index host or None for PyPI, file stem, environment, kind)
    "testpypi": ("test.pypi.org", "engineering_influence", "testpypi", "dev"),
    "testpypi-sdk": ("test.pypi.org", "engineering_influence_sdk", "testpypi-sdk", "dev"),
    "pypi": (None, "engineering_influence", "pypi", "release"),
    "pypi-sdk": (None, "engineering_influence_sdk", "pypi-sdk", "release"),
}
BUILT = [
    "engineering_influence-0.1.0a2-py3-none-any.whl",
    "engineering_influence-0.1.0a2.tar.gz",
    "engineering_influence_sdk-0.1.0a2-py3-none-any.whl",
    "engineering_influence_sdk-0.1.0a2.tar.gz",
    "SHA256SUMS",
    "sbom.cdx.json",
]


def test_develop_goes_to_testpypi_and_main_goes_to_pypi_and_never_the_other_way() -> None:
    for name, (_, _, _, kind) in PUBLISHING.items():
        other = "release" if kind == "dev" else "dev"
        variable = "PUBLISH_TO_TESTPYPI" if kind == "dev" else "PUBLISH_TO_PYPI"
        assert f"needs.guard.outputs.kind == '{kind}'" in condition(name)
        assert f"needs.guard.outputs.kind == '{other}'" not in condition(name)
        assert f"vars.{variable} == 'true'" in condition(name)


def test_the_core_goes_up_before_the_sdk_and_a_release_only_after_its_github_release() -> None:
    assert jobs()["testpypi"]["needs"] == ["guard", "build"]
    assert jobs()["testpypi-sdk"]["needs"] == ["guard", "testpypi"]
    assert jobs()["pypi"]["needs"] == ["guard", "github-release"]
    assert jobs()["pypi-sdk"]["needs"] == ["guard", "pypi"]


def test_each_package_is_uploaded_from_an_environment_of_its_own() -> None:
    names = [jobs()[name]["environment"]["name"] for name in PUBLISHING]  # type: ignore[index]

    assert names == [env for _, _, env, _ in PUBLISHING.values()]
    assert len(set(names)) == 4  # PyPI tells pending publishers apart by environment


def test_every_upload_is_authorised_by_the_runs_identity_and_uses_no_token() -> None:
    for name, (host, _, _, _) in PUBLISHING.items():
        job = jobs()[name]
        assert job["permissions"] == {"id-token": "write"}
        options = publish_step(job)["with"]
        assert not {"password", "user"} & options.keys()  # type: ignore[attr-defined]
        assert options["attestations"] is True  # type: ignore[index]
        assert ("repository-url" in options) is (host is not None)  # type: ignore[operator]
        if host:
            assert options["repository-url"] == f"https://{host}/legacy/"  # type: ignore[index]


def test_each_job_uploads_only_its_own_package_and_not_the_sbom_or_checksums() -> None:
    for name, (_, stem, _, _) in PUBLISHING.items():
        job = jobs()[name]
        move = next(
            s
            for s in job["steps"]
            if s.get("name") == "Keep only the distributions of this package"
        )  # type: ignore[attr-defined]
        patterns = [word for word in move["run"].split() if word.startswith("dist/")]
        assert patterns == [f"dist/{stem}-*.whl", f"dist/{stem}-*.tar.gz"]
        taken = {f for f in BUILT for p in patterns if fnmatch.fnmatch(f"dist/{f}", p)}
        assert taken == {f for f in BUILT if f.startswith(f"{stem}-")}
        assert publish_step(job)["with"]["packages-dir"] == move["run"].split()[-1]  # type: ignore[index]


def test_the_two_packages_never_take_each_others_files() -> None:
    core = {f for f in BUILT if fnmatch.fnmatch(f, "engineering_influence-*")}
    sdk = {f for f in BUILT if fnmatch.fnmatch(f, "engineering_influence_sdk-*")}

    assert len(core) == len(sdk) == 2
    assert not core & sdk
