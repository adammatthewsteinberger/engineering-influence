# Releasing

A release is a tag named `v<version>` pushed from the `main` branch. Everything after the
push is automatic, and the only step that cannot be undone, publishing to PyPI, is off until
you turn it on and approve it.

## Cutting a release

1. On `develop`, set `__version__` to the same new value in
   `src/engineering_influence/__init__.py` and
   `packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py`. Nothing
   else repeats the version: `pyproject.toml`, `ei --version` and the API all read it.
2. Fold the changelog fragments into the new version's section and delete them:
   `uv run python scripts/fold_changelog.py <version>`. It turns every `changelog.d/*.md` into a
   bullet under a new `## <version>` heading (keeping a fresh empty `## Unreleased` above it). Update
   the status text that names the current alpha (`README.md`, `llms.txt`, `docs/GETTING_STARTED.md`)
   in the same commit. `develop` does not claim a version until its release commit.
3. Merge `develop` into `main` through a pull request.
4. Tag the merge commit and push the tag:

   ```bash
   git tag -a v0.1.0 -m "v0.1.0"
   git push origin v0.1.0
   ```

If pushing the tag does not start the workflow (it did not for the first release, because push-triggered
workflows were not firing in the repository), start the same pipeline by hand for the existing tag:

```bash
gh workflow run release.yml --ref main -f tag=v0.1.0
```

The run checks out and verifies that tag, not the branch it was started from, so the guard, the tests,
the build and the attestation are all unchanged.

## What the pipeline does

| Job | Does | Stops the release if |
|---|---|---|
| `guard` | Compares the tag with the code | the tag is not `v<version>`; core and SDK versions differ; the changelog has no section for exactly this version; unfolded fragments remain in `changelog.d/`; the commit is not on `main` |
| `build` | Runs the whole test suite, builds both packages, installs the real artifacts in clean environments, writes `SHA256SUMS` and a CycloneDX SBOM | any test, `twine check --strict`, or an install check fails |
| `github-release` | Attests the build provenance, then creates the GitHub release with the artifacts, a checksum file and the SBOM | it cannot create the release |
| `testpypi` | Rehearses the upload of the core package to TestPyPI | `PUBLISH_TO_TESTPYPI` is not `true` (the job is skipped, and the release goes on), or the `testpypi` environment is not approved |
| `testpypi-sdk` | Rehearses the upload of the SDK, after the core | the core rehearsal did not succeed, or the `testpypi-sdk` environment is not approved |
| `pypi` | Publishes the core package with PyPI attestations | `PUBLISH_TO_PYPI` is not `true`, the `pypi` environment is not approved, or a TestPyPI rehearsal ran and failed or was cancelled |
| `pypi-sdk` | Publishes the SDK with PyPI attestations, after the core | the core was not published, or the `pypi-sdk` environment is not approved |

The `build` job is the same reusable workflow that CI runs on every push (`distribution`),
without the full test run. A release therefore cannot fail on packaging for the first time
at tag time. Versions with `a`, `b`, `rc` or `.dev` are marked as pre-releases.

Builds are reproducible: with the commit's timestamp fixed as `SOURCE_DATE_EPOCH`, two
builds of the same commit give byte-identical files.

## One package, one environment

The core and the SDK are separate projects, each uploaded by its own job from its own GitHub
environment. That is deliberate. A *pending* trusted publisher is told apart by its owner,
repository, workflow and environment, so two pending publishers cannot share all four. The workflow
file is the same for both, and the environment is what differs:

| Project | Workflow | On pypi.org | On test.pypi.org |
|---|---|---|---|
| `engineering-influence` | `release.yml` | environment `pypi` | environment `testpypi` |
| `engineering-influence-sdk` | `release.yml` | environment `pypi-sdk` | environment `testpypi-sdk` |

The core goes first and the SDK waits for it. The two are uploaded one after the other, not as one
step, so a failure between them can leave the core published and the SDK not. A PyPI version can never
be reused, so that is repaired by releasing the next version, not by uploading again.

## One-time setup for TestPyPI (optional rehearsal)

The rehearsal uploads the same files to TestPyPI, which accepts a version once, like PyPI. Do this
once, before setting `PUBLISH_TO_TESTPYPI`:

1. On test.pypi.org, add a **pending trusted publisher** for each project, using the table above:
   owner `adammatthewsteinberger`, repository `engineering-influence`, workflow `release.yml`.
2. In the repository settings, create the environments `testpypi` and `testpypi-sdk` and add
   **required reviewers** to both. A workflow that names an environment that does not exist
   creates it with no protection, so create them first.
3. Set the repository variable `PUBLISH_TO_TESTPYPI` to `true`.

A rerun of a rehearsal passes over files TestPyPI already has (`skip-existing`), so a failed run can be
repeated. If a rehearsal runs and fails, the `pypi` jobs do not run; if it is skipped, they go
ahead as before.

## One-time setup for PyPI

Do this once per repository, before setting the variable:

1. On PyPI, add a **pending trusted publisher** for each project, using the table above:
   owner `adammatthewsteinberger`, repository `engineering-influence`, workflow `release.yml`.
2. In the repository settings, create the environments `pypi` and `pypi-sdk` and add **required
   reviewers** to both, so a person approves every PyPI upload.
3. Set the repository variable `PUBLISH_TO_PYPI` to `true`.

A PyPI version can never be replaced or reused. Publish a pre-release first.

## Checking a download

```bash
sha256sum -c SHA256SUMS
gh attestation verify engineering_influence-0.1.0-py3-none-any.whl --repo adammatthewsteinberger/engineering-influence
```

## Keeping the pipeline current

Every action in the workflows is pinned to a full commit SHA, with the version in a comment.
Dependabot proposes updates weekly and waits seven days after a release before offering it.
CI runs `actionlint` and `zizmor` (medium severity and above) on every workflow.

## What has not been exercised

- The four publishing jobs (`testpypi`, `testpypi-sdk`, `pypi`, `pypi-sdk`) have never run: they need the trusted publishers and the variables described above.
- The guard is tested against its own script (`tests/e2e/test_release_guard.py`).
- `zizmor` reports two low-severity suggestions to write `./.github/workflows/…` as `$/…`.
  The documented `./` form is kept deliberately.
- The container image is not published anywhere.
