# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Editing a prompt without bumping its version is refused.

The version is in the run journal's key, so a changed prompt under an old version would replay
answers that were written for the old text. ``tests/fixtures/prompt_templates.lock.toml`` pins each
shipped template's version to a fingerprint of its text. After a deliberate change, bump the
template's ``version`` and run ``EI_UPDATE_PROMPT_LOCK=1 uv run pytest tests/unit/test_prompt_template_lock.py``.
"""

import os
import tomllib
from pathlib import Path

from engineering_influence.infrastructure.prompts.toml_prompt_library import TomlPromptLibrary

LOCK = Path(__file__).resolve().parents[1] / "fixtures" / "prompt_templates.lock.toml"
Entries = dict[str, tuple[int, str]]


def shipped() -> Entries:
    library = TomlPromptLibrary()
    found = {name: library.get(name) for name in library.names()}
    return {name: (t.version, t.fingerprint()) for name, t in found.items()}


def locked() -> Entries:
    if not LOCK.exists():
        return {}
    data = tomllib.loads(LOCK.read_text(encoding="utf-8"))
    return {name: (entry["version"], entry["fingerprint"]) for name, entry in data.items()}


def edited_without_a_bump(now: Entries, then: Entries) -> list[str]:
    return [
        name
        for name in sorted(now.keys() & then.keys())
        if now[name][0] == then[name][0] and now[name][1] != then[name][1]
    ]


def problems(now: Entries, then: Entries) -> list[str]:
    found = [
        f"{name}: its text changed but the version is still {now[name][0]}; bump it"
        for name in edited_without_a_bump(now, then)
    ]
    for name in sorted(now.keys() | then.keys()):
        if name not in then:
            found.append(f"{name}: a new template that is not in the lock")
        elif name not in now:
            found.append(f"{name}: in the lock, but there is no such template")
        elif now[name][0] != then[name][0]:
            found.append(
                f"{name}: the version changed ({then[name][0]} -> {now[name][0]}), so the lock is stale"
            )
    return found


def write(entries: Entries) -> None:
    lines = [
        "# Pins each shipped prompt template's version to a fingerprint of its text.",
        "# Regenerate with EI_UPDATE_PROMPT_LOCK=1 (see tests/unit/test_prompt_template_lock.py).",
    ]
    for name in sorted(entries):
        version, fingerprint = entries[name]
        lines += ["", f"[{name}]", f"version = {version}", f'fingerprint = "{fingerprint}"']
    LOCK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_every_shipped_template_matches_the_lock() -> None:
    now, then = shipped(), locked()
    if os.environ.get("EI_UPDATE_PROMPT_LOCK"):
        assert not edited_without_a_bump(now, then), "bump the version of the edited template first"
        write(now)
        return
    found = problems(now, then)
    assert not found, "\n".join(found) + "\nSee the docstring of this test file."


def test_an_edit_without_a_version_bump_is_reported() -> None:
    then = {"a": (1, "x"), "b": (2, "y")}
    assert problems({"a": (1, "CHANGED"), "b": (2, "y")}, then) == [
        "a: its text changed but the version is still 1; bump it"
    ]


def test_a_bump_that_is_not_in_the_lock_a_new_template_and_a_removed_one_are_reported() -> None:
    then = {"a": (1, "x"), "gone": (1, "z")}
    found = problems({"a": (2, "x2"), "new": (1, "n")}, then)
    assert found == [
        "a: the version changed (1 -> 2), so the lock is stale",
        "gone: in the lock, but there is no such template",
        "new: a new template that is not in the lock",
    ]


def test_nothing_to_report_when_everything_matches() -> None:
    assert problems({"a": (1, "x")}, {"a": (1, "x")}) == []
