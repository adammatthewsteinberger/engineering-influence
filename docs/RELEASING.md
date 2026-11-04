# Releasing

A release is a tag named `v<version>` pushed from the `main` branch. Everything after the
push is automatic, and the only step that cannot be undone, publishing to PyPI, is off until
you turn it on and approve it.

## Cutting a release

1. On `develop`, set `__version__` to the same new value in
   `src/engineering_influence/__init__.py` and
   `packages/engineering-influence-sdk/src/engineering_influence_sdk/__init__.py`. Nothing
   else repeats the version: `pyproject.toml`, `ei --version` and the API all read it.
2. In `CHANGELOG.md`, rename `## Unreleased` to `## <version>` (a `## [<version>] - <date>`
   heading also works) and add a new empty `## Unreleased` above it.
3. Merge `develop` into `main` through a pull request.
4. Tag the merge commit and push the tag:

   ```bash
   git tag -a v0.1.0 -m "v0.1.0"
   git push origin v0.1.0
   ```

## What the pipeline does

| Job | Does | Stops the release if |
|---|---|---|
| `guard` | Compares the tag with the code | the tag is not `v<version>`; core and SDK versions differ; the changelog has no section for exactly this version; the commit is not on `main` |
| `build` | Runs the whole test suite, builds both packages, installs the real artifacts in clean environments, writes `SHA256SUMS` and a CycloneDX SBOM | any test, `twine check --strict`, or an install check fails |
| `github-release` | Attests the build provenance, then creates the GitHub release with the artifacts, a checksum file and the SBOM | it cannot create the release |
| `pypi` | Publishes both packages with PyPI attestations | `PUBLISH_TO_PYPI` is not `true`, or the `pypi` environment is not approved |

The `build` job is the same reusable workflow that CI runs on every push (`distribution`),
without the full test run. A release therefore cannot fail on packaging for the first time
at tag time. Versions with `a`, `b`, `rc` or `.dev` are marked as pre-releases.

Builds are reproducible: with the commit's timestamp fixed as `SOURCE_DATE_EPOCH`, two
builds of the same commit give byte-identical files.

## One-time setup for PyPI

Do this once per repository, before setting the variable:

1. On PyPI, add a **pending trusted publisher** for each project, `engineering-influence`
   and `engineering-influence-sdk`: owner `adammatthewsteinberger`, repository
   `engineering-influence`, workflow `release.yml`, environment `pypi`.
2. In the repository settings, create an environment named `pypi` and add **required
   reviewers**, so a person approves every PyPI upload.
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

- The `github-release` and `pypi` jobs have never run: they need a real tag on `main`.
- The guard is tested against its own script (`tests/e2e/test_release_guard.py`).
- `zizmor` reports two low-severity suggestions to write `./.github/workflows/…` as `$/…`.
  The documented `./` form is kept deliberately.
- The container image is not published anywhere.
