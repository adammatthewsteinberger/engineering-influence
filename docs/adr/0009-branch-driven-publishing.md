# ADR 0009: Publishing follows the branch: develop to TestPyPI, main to PyPI

Status: accepted

## Context

ADR 0005 set a release as a tag, `v<version>`, pushed by a person from `main`, with the version set by
hand and the guard refusing a tag that disagrees with the code, the changelog or the branch. It also
said that tagging and publishing "need an explicit approval" and that nothing in that ADR automates them.

The maintainer has decided that a merge to `develop` should upload to TestPyPI and a merge to `main`
should upload to PyPI.

## Decision

1. **The trigger is a push to `develop` or `main`, not a tag.** `release.yml` runs on those two
   branches and by hand. A tag push does nothing, and a run from any other branch is refused by the
   guard.
2. **`develop` uploads development builds to TestPyPI.** A package index never accepts a version
   twice, and `develop` carries one version until the next release, so each build is stamped
   `<version>.dev<run number>`. The stamping is done to a copy of the commit by
   `scripts/stamp_dev_version.py`, so the checkout, the lock file and the tests see the real version.
3. **`main` is the release.** A merge to `main` runs the guard (a plain release version, a changelog
   section for exactly that version, no unfolded fragments, the commit on `main`) and the full tests,
   creates the tag `v<version>` and a GitHub release at the built commit, and uploads to PyPI. The
   version is still set by hand in the release commit (ADR 0005, point 1) and the fragments are still
   folded before it (point 3). `main` should receive releases only.
4. **The approval is the environment, not the tag.** Each upload runs from its own GitHub environment
   with required reviewers, and each index has a repository variable that switches it on
   (`PUBLISH_TO_TESTPYPI`, `PUBLISH_TO_PYPI`). Both are off by default. This replaces ADR 0005's
   point 5 for uploads: a person still approves each one, but the approval comes from the environment
   when the merge happens, not from the act of tagging.
5. **The core and the SDK are separate jobs and environments**, because PyPI tells pending trusted
   publishers apart by owner, repository, workflow and environment (see `docs/RELEASING.md`).

## Consequences

- A release is one merge, so the guard has to be strict: a merge to `main` without a version bump
  fails (the changelog has no section, or PyPI refuses a duplicate) and should be fixed forward.
- Every merge to `develop` can upload. If the `testpypi` environments require reviewers, each merge
  waits for an approval; the maintainer chooses whether that is wanted.
- A development version sorts before the release it is named for, so while `develop` carries an
  already released version, its builds sort below that release.
- A failure between the core and SDK uploads can publish one and not the other. A PyPI version can
  never be reused, so it is repaired with the next version.
- The tag now comes from the workflow, so the workflow must not trust one it did not make: it looks the tag up, accepts one that already names the built commit, and stops on one that names another or on any lookup it cannot read.
- The tag now comes from the workflow. Nothing reads a tag any more, so a person tagging by hand has
  no effect, and a release that failed after the GitHub release was created is repeated by running the
  workflow again, which finds the release and carries on.
- ADR 0005's points 2 (the tag guard) and 5 (releases remain gated) are replaced by points 1, 3 and 4
  above. Its points on fragments, hand-set versions and breaking changes stand.
