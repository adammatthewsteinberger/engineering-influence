# ADR 0005: Release flow and changelog fragments

Status: accepted

## Context

ADR 0003 said that the vibey release flow derives versions. That is not how this repository
releases. `docs/RELEASING.md` describes what exists and works: a person sets `__version__` by
hand, renames the changelog section, merges to `main`, and tags `v<version>`; the `release.yml` guard
refuses a tag that disagrees with the code, the changelog or the branch. The ADR 0004 pre-release
tiers (`a`, `b`, `rc`) depend on that hand-set version, because a derived version cannot express them.

Every pull request also edits the one `## Unreleased` section of `CHANGELOG.md`. Concurrent pull
requests conflict on it, and the conflicts are noise.

## Decision

1. **The version is set by hand, in the release commit.** `develop` carries the version of the last
   release until the commit that prepares the next one. Documents that name the current alpha
   (`README.md`, `llms.txt`, `docs/GETTING_STARTED.md`) change in that same commit. This is
   deliberate: `develop` must not claim a version that has not been released.
2. **The tag guard stays authoritative.** `release.yml` keeps refusing a tag whose version
   disagrees with the code, with the changelog, or with `main`. It also refuses a tag while unfolded
   fragments remain (point 3).
3. **Changes are recorded as fragments.** A pull request that changes behaviour adds a file
   `changelog.d/<short-slug>.md` holding one paragraph, the text of one changelog bullet. It does
   not edit `CHANGELOG.md`. Before tagging, `scripts/fold_changelog.py <version>` moves every fragment
   into a `## <version>` section, in file-name order, and deletes the fragment files.
4. **Breaking changes follow ADR 0004.** The fragment says what broke and what to do. The vibey
   claim about deriving major versions from `BREAKING CHANGE:` footers is not used here: footers
   stay required by the conventional-commit check, but the version is still chosen by a person.
5. **Releases remain gated.** Tagging, publishing to PyPI and pushing images need an explicit
   approval, as `docs/RELEASING.md` states. Nothing in this ADR automates them.

## Consequences

- Concurrent pull requests no longer conflict on the changelog.
- A release is one reviewable commit that sets the version, folds the fragments and updates the
  status text.
- A contributor who forgets a fragment is caught in review, not by tooling; the guard only
  catches fragments left behind.
- ADR 0003's wording is corrected to match.
