# Changelog fragments

A pull request that changes behaviour adds one file here, `<short-slug>.md`, holding one paragraph:
the text of one changelog bullet, with no leading `- `. Do not edit `CHANGELOG.md` in the pull request.

Before tagging, `uv run python scripts/fold_changelog.py <version>` moves every fragment into a
`## <version>` section of `CHANGELOG.md` and deletes the fragment files. The release guard refuses a
tag while fragments remain. See `docs/adr/0005-release-flow-and-changelog-fragments.md`.
