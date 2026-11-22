# Releasing

Publishing is driven by the branch a commit lands on, and a person approves every upload.

| Merge to | What happens | Where it goes |
|---|---|---|
| `develop` | a **development build**, `<version>.dev<run number>` | TestPyPI |
| `main` | a **release**: the guard, the full tests, a tag and GitHub release, then the upload | PyPI |

Nothing uploads until you turn each index on with a repository variable and approve its environments,
so merging is safe before that setup is done. ADR 0009 records why the release moved from a pushed tag
to a merge to `main`.

## Cutting a release

1. On `develop`, set `__version__` to the same new value in
   `src/engineering_influence/__init__.py` and
   `packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py`. Nothing
   else repeats the version: `pyproject.toml`, `ei --version` and the API all read it. It must be a
   plain release version such as `0.1.0` or `0.1.0a2`, never a `.dev` one.
2. Fold the changelog fragments into the new version's section and delete them:
   `uv run python scripts/fold_changelog.py <version>`. It turns every `changelog.d/*.md` into a
   bullet under a new `## <version>` heading (keeping a fresh empty `## Unreleased` above it). Update
   the status text that names the current alpha (`README.md`, `llms.txt`, `docs/GETTING_STARTED.md`)
   in the same commit. `develop` does not claim a version until its release commit.
3. Merge `develop` into `main` through a pull request. **That merge is the release.** The workflow
   starts by itself, the guard checks the version and the changelog, and the `pypi` environment waits
   for a reviewer.

A merge to `main` that does not carry a new version fails loudly: the guard refuses it if the changelog
has no section for the version or unfolded fragments remain, and PyPI refuses a version it already has.
`main` should receive releases only.

To run the pipeline again for the current tip of `develop` or `main`, for example after approving a
failed upload, start it by hand: `gh workflow run release.yml --ref main` (or `--ref develop`). Any other
branch is refused.

## What the pipeline does

| Job | Runs on | Does | Stops if |
|---|---|---|---|
| `guard` | both | Reads the branch. On `main`, checks the version against the changelog | the ref is not `develop` or `main`; core and SDK versions differ; the version is not a plain release version; on `main`: no changelog section for exactly this version, unfolded fragments remain in `changelog.d/`, or the commit is not on `main` |
| `build` | both | Builds both packages, installs the real artifacts in clean environments, writes `SHA256SUMS` and a CycloneDX SBOM. On `main` it also runs the whole test suite. On `develop` the packages are built from a copy of the commit with the version stamped as `<version>.dev<run number>` and checked to install and report that version | any test, `twine check --strict`, or an install check fails |
| `github-release` | `main` | Attests the build provenance, then creates the tag `v<version>` at the built commit and a GitHub release with the artifacts, a checksum file and the SBOM. A repeat run finds the release and leaves it | it cannot create the release |
| `testpypi` | `develop` | Uploads the core package to TestPyPI | `PUBLISH_TO_TESTPYPI` is not `true` (the job is skipped), or the `testpypi` environment is not approved |
| `testpypi-sdk` | `develop` | Uploads the SDK, after the core | the core upload did not succeed, or the `testpypi-sdk` environment is not approved |
| `pypi` | `main` | Uploads the core package to PyPI with attestations, after the GitHub release | `PUBLISH_TO_PYPI` is not `true` (the job is skipped), or the `pypi` environment is not approved |
| `pypi-sdk` | `main` | Uploads the SDK to PyPI with attestations, after the core | the core was not published, or the `pypi-sdk` environment is not approved |

The `build` job is the same reusable workflow that CI runs on every push (`distribution`). A release
therefore cannot fail on packaging for the first time at release time. Versions with `a`, `b` or `rc` are
marked as pre-releases.

Builds are reproducible: with the commit's timestamp fixed as `SOURCE_DATE_EPOCH`, two builds of the same
commit give byte-identical files.

## Development builds

A package index never accepts a version twice, and `develop` carries one version until the next release,
so each merge to `develop` is uploaded as `<version>.dev<run number>`, for example `0.1.0a2.dev57`. The
number is the workflow's run number, which only goes up, and a re-run of the same run keeps its number
(`skip-existing` lets it pass over files TestPyPI already has). The build is made from a copy of the
commit, so the checkout, `uv.lock` and the tests all see the real version.

Runs for one branch queue behind each other. If several merges land while one run is waiting for an
approval, GitHub keeps only the newest queued run and drops the older ones, so a development build can
be skipped. That is harmless for `develop`, where the latest build is the one that matters. For `main`,
merge one release at a time.

A development version sorts **before** the release it is named for. If `develop` still carries the version
of a release that is already on PyPI, its development builds sort below that release; bump the version
in `develop` right after a release if that matters.

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

## One-time setup for TestPyPI

Every merge to `develop` uploads a development build once this is done. Do it once, before setting
`PUBLISH_TO_TESTPYPI`:

1. On test.pypi.org, add a **pending trusted publisher** for each project, using the table above:
   owner `adammatthewsteinberger`, repository `engineering-influence`, workflow `release.yml`.
2. In the repository settings, create the environments `testpypi` and `testpypi-sdk`. A workflow that
   names an environment that does not exist creates it with no protection, so create them first.
   **Required reviewers on these two mean every merge to `develop` waits for an approval**; leave them
   off if you want development builds to upload on their own. Limiting each environment's deployment
   branches to `develop` is a good addition.
3. Set the repository variable `PUBLISH_TO_TESTPYPI` to `true`.

## One-time setup for PyPI

Do this once per repository, before setting the variable:

1. On PyPI, add a **pending trusted publisher** for each project, using the table above:
   owner `adammatthewsteinberger`, repository `engineering-influence`, workflow `release.yml`.
2. In the repository settings, create the environments `pypi` and `pypi-sdk`, add **required
   reviewers** to both so a person approves every PyPI upload, and limit their deployment branches to
   `main`.
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
- The `github-release` job has not run in its new form, which creates the tag itself instead of reading one.
- The guard is tested against its own script (`tests/e2e/test_release_guard.py`), and the development-build staging step against the real step (`tests/e2e/test_dev_build_stage.py`).
  The upload jobs are tested only by their shape.
- `zizmor` reports two low-severity suggestions to write `./.github/workflows/…` as `$/…`.
  The documented `./` form is kept deliberately.
- The container image is not published anywhere.
