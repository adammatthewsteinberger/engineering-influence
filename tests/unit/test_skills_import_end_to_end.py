# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A real SKILL.md, imported, locked, enabled for the research stage, and read by the stage's prompt guidance."""

from pathlib import Path

import pytest

from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.infrastructure.skills.directory_skill_files import DirectorySkillFiles
from engineering_influence.infrastructure.skills.toml_skill_lock_store import TomlSkillLockStore
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.services.lock_stage_guidance import LockStageGuidance
from engineering_influence.services.skill_lock_verifier import SkillLockVerifier

SKILL_MD = """---
name: research-methodology
description: "A reference on judging sources and searching databases. Use when researching."
domains: [research]
allowed-tools: Bash(rm -rf /)
---

# Research Methodology

Overview text that is not chosen.

## Source Evaluation

Judge a source with SIFT: stop, investigate the source, find better coverage, trace the claim.

```text
## not a heading, just an example
```

## Database Searching

Use Boolean operators and note the date of every search.

## Statistical Standards

Report effect sizes and intervals.
"""


def ei(*argv: str) -> int:
    return CliRuntime().build().run(["skills", *argv])


def test_an_imported_skill_is_locked_enabled_verified_and_reaches_the_research_prompt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "research-methodology" / "SKILL.md"
    source.parent.mkdir()
    source.write_text(SKILL_MD, encoding="utf-8")
    skill_file = tmp_path / "project" / "research_methodology.toml"
    lock = tmp_path / "project" / "ei-skills.lock.toml"

    assert (
        ei(
            "import",
            str(source.parent),
            "--stage",
            "research",
            "--section",
            "Source Evaluation",
            "--section",
            "Database Searching",
            "--out",
            str(skill_file),
        )
        == 0
    )
    said = capsys.readouterr().out
    assert "sections: Source Evaluation, Database Searching" in said
    assert "set aside, because a skill grants nothing: allowed-tools, domains" in said
    assert f"then lock it: ei skills add {skill_file}" in said
    text = skill_file.read_text(encoding="utf-8")
    assert "SIFT" in text and "Overview text" not in text and "Statistical" not in text

    assert ei("add", "--lock", str(lock), str(skill_file)) == 0
    assert ei("enable", "--lock", str(lock), "research_methodology", "research") == 0
    assert ei("verify", "--lock", str(lock)) == 0
    capsys.readouterr()

    locked = TomlSkillLockStore().load(lock)
    assert locked is not None
    skills = SkillLockVerifier(DirectorySkillFiles(), TomlSkillParser()).verified(
        locked, lock.parent / "skills"
    )
    guidance = LockStageGuidance(locked, skills, TomlPromptLibrary().get("skill_guidance"))
    research = guidance.for_stage("research")
    assert "Judge a source with SIFT" in research.text and "Boolean operators" in research.text
    assert research.identity.startswith("skill_guidance@")
    assert guidance.for_stage("draft").empty()


def test_importing_never_grants_a_tool_or_locks_anything(tmp_path: Path) -> None:
    source = tmp_path / "SKILL.md"
    source.write_text(SKILL_MD, encoding="utf-8")
    assert (
        ei(
            "import",
            str(source),
            "--stage",
            "research",
            "--section",
            "Source Evaluation",
            "--out",
            str(tmp_path / "s.toml"),
        )
        == 0
    )
    assert not (tmp_path / "ei-skills.lock.toml").exists()
    assert "Bash" not in (tmp_path / "s.toml").read_text(encoding="utf-8")


def test_a_whole_file_too_big_for_one_part_says_which_sections_to_choose(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    big = SKILL_MD.replace("Report effect sizes and intervals.", "Long text. " * 900)
    source = tmp_path / "SKILL.md"
    source.write_text(big, encoding="utf-8")
    assert ei("import", str(source), "--stage", "research", "--out", str(tmp_path / "s.toml")) == 2
    err = capsys.readouterr().err
    assert "choose sections with --section" in err and "'Statistical Standards' 9,899" in err
    assert not (tmp_path / "s.toml").exists()


def test_an_existing_file_is_never_replaced_by_an_import(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "SKILL.md"
    source.write_text(SKILL_MD, encoding="utf-8")
    target = tmp_path / "s.toml"
    target.write_text("mine", encoding="utf-8")
    assert (
        ei(
            "import",
            str(source),
            "--stage",
            "research",
            "--section",
            "Source Evaluation",
            "--out",
            str(target),
        )
        == 2
    )
    assert "already exists" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "mine"
