# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillsCli: install, enable, list and check prompt skills, with everything a skill says shown safely."""

import argparse
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.skills_cli_interface import (
    SkillsCliInterface,
)
from engineering_influence.interactions.cli.skills_cli import SkillsCli
from engineering_influence.interfaces.skill_lock_store_interface import SkillLockStoreInterface
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_import_result import SkillImportResult
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_addition import SkillLockAddition
from engineering_influence.models.skill_lock_entry import SkillLockEntry
from engineering_influence.services.interfaces.skill_importer_interface import (
    SkillImporterInterface,
)
from engineering_influence.services.interfaces.skill_lock_editor_interface import (
    SkillLockEditorInterface,
)
from engineering_influence.services.interfaces.skill_lock_verifier_interface import (
    SkillLockVerifierInterface,
)

A = "a" * 64


def skill(**changes: object) -> Skill:
    fields: dict[str, object] = {
        "name": "plain_style",
        "version": 2,
        "parts": (("outline", "Prefer short sentences."), ("research", "Say where you read it.")),
        "description": "Short, plain sentences.",
    }
    return Skill(**{**fields, **changes})  # type: ignore[arg-type]


def entry(name: str = "plain_style", stages: tuple[str, ...] = ()) -> SkillLockEntry:
    return SkillLockEntry(name, 2, A, stages)


class Editor(SkillLockEditorInterface):
    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[tuple[object, ...]] = []

    def _go(self, *call: object) -> None:
        self.calls.append(call)
        if self.fail:
            raise self.fail

    def add(self, lock: SkillLock, folder: Path, source: Path, replace: bool) -> SkillLockAddition:
        self._go("add", folder, source, replace)
        return SkillLockAddition(lock.with_entry(entry(), replace), skill())

    def add_bytes(
        self, lock: SkillLock, folder: Path, name: str, data: bytes, replace: bool
    ) -> SkillLockAddition:
        self._go("add_bytes", folder, name, data, replace)
        return SkillLockAddition(lock.with_entry(entry(name), replace), skill(name=name))

    def enable(self, lock: SkillLock, folder: Path, name: str, stage: str) -> SkillLock:
        self._go("enable", folder, name, stage)
        return lock.with_entry(entry(name, (stage,)), True)

    def disable(self, lock: SkillLock, name: str, stage: str) -> SkillLock:
        self._go("disable", name, stage)
        return lock.with_entry(entry(name), True)

    def remove(self, lock: SkillLock, folder: Path, name: str) -> SkillLock:
        self._go("remove", folder, name)
        return lock.without(name)


class Importer(SkillImporterInterface):
    def __init__(self, fail: Exception | None = None, **changes: object) -> None:
        self.fail = fail
        self.changes = changes
        self.calls: list[tuple[object, ...]] = []

    def import_skill(
        self,
        source: Path,
        name: str | None,
        version: int,
        stages: tuple[str, ...],
        titles: tuple[str, ...],
        reference: bool,
        target: Path | None,
    ) -> SkillImportResult:
        self.calls.append((source, name, version, stages, titles, reference, target))
        if self.fail:
            raise self.fail
        fields: dict[str, object] = {
            "skill": skill(name="research_methodology", parts=(("research", "## One\n\ntext"),)),
            "path": "research_methodology.toml",
            "sections": ("One", "Two"),
            "ignored": (),
            "description_shortened": False,
        }
        return SkillImportResult(**{**fields, **self.changes})  # type: ignore[arg-type]


class Verifier(SkillLockVerifierInterface):
    def __init__(self, *problems: str) -> None:
        self.found = problems
        self.asked: list[tuple[SkillLock, Path]] = []

    def skill(self, entry: SkillLockEntry, folder: Path) -> Skill:
        raise AssertionError("the command line never loads a skill itself")

    def verified(self, lock: SkillLock, folder: Path) -> tuple[Skill, ...]:
        raise AssertionError("the command line never loads a skill itself")

    def problems(self, lock: SkillLock, folder: Path) -> tuple[str, ...]:
        self.asked.append((lock, folder))
        return self.found


class Store(SkillLockStoreInterface):
    def __init__(self, lock: SkillLock | None = None, fail: Exception | None = None) -> None:
        self.lock = lock
        self.fail = fail
        self.loaded: list[Path] = []
        self.saved: list[tuple[Path, SkillLock]] = []

    def load(self, path: Path) -> SkillLock | None:
        self.loaded.append(path)
        if self.fail:
            raise self.fail
        return self.lock

    def save(self, path: Path, lock: SkillLock) -> None:
        self.saved.append((path, lock))


def cli(
    store: Store | None = None,
    editor: Editor | None = None,
    verifier: Verifier | None = None,
    environment: dict[str, str] | None = None,
    importer: Importer | None = None,
) -> tuple[SkillsCli, Store, Editor, Verifier]:
    made = (store or Store(), editor or Editor(), verifier or Verifier())
    return SkillsCli(made[1], made[2], made[0], environment or {}, importer or Importer()), *made


def run(skills: SkillsCli, *argv: str) -> int:
    parser = argparse.ArgumentParser()
    skills.register(parser.add_subparsers(dest="command"))
    return skills.run(parser.parse_args(["skills", *argv]))


def test_it_is_a_skills_cli() -> None:
    assert isinstance(cli()[0], SkillsCliInterface)


# ------------------------------------------------------------------------------------- add
def test_add_locks_the_file_keeps_a_copy_beside_the_lock_and_says_to_review(
    capsys: pytest.CaptureFixture[str],
) -> None:
    skills, store, editor, _ = cli()
    assert run(skills, "add", "--lock", "/x/proj/l.toml", "/tmp/plain_style.toml") == 0
    out = capsys.readouterr().out
    assert editor.calls == [("add", Path("/x/proj/skills"), Path("/tmp/plain_style.toml"), False)]
    assert store.saved[0][0] == Path("/x/proj/l.toml")
    assert store.saved[0][1].names() == ("plain_style",)
    assert "locked plain_style@2: 2 parts, 0 reference sections" in out
    assert "  Short, plain sentences." in out
    assert "read it before you commit this lock" in out
    assert "  outline (23 characters): Prefer short sentences." in out
    assert "  research (22 characters): Say where you read it." in out
    assert "copy kept at /x/proj/skills/plain_style.toml" in out
    assert "enabled for no stage yet: ei skills enable plain_style STAGE" in out
    assert "(it has text for outline, research)" in out
    assert "wrote /x/proj/l.toml; review the change like any other commit" in out


def test_add_passes_replace_through_and_extends_the_lock_that_is_there(
    capsys: pytest.CaptureFixture[str],
) -> None:
    skills, store, editor, _ = cli(Store(SkillLock((entry("other_one"),))))
    assert run(skills, "add", "--lock", "/p/l.toml", "--replace", "x/plain_style.toml") == 0
    assert editor.calls[0][3] is True
    assert store.saved[0][1].names() == ("other_one", "plain_style")


def test_add_without_a_description_prints_no_blank_description_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Plain(Editor):
        def add(self, lock: SkillLock, folder: Path, source: Path, replace: bool):  # type: ignore[no-untyped-def]
            return SkillLockAddition(lock.with_entry(entry(), replace), skill(description=""))

    assert run(cli(editor=Plain())[0], "add", "--lock", "/p/l.toml", "x.toml") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "locked plain_style@2: 2 parts, 0 reference sections" and lines[
        1
    ].startswith("this text will be")


def test_the_lock_is_the_flag_then_the_environment_then_the_default() -> None:
    skills, store, _, _ = cli(environment={"EI_SKILL_LOCK": "/env/l.toml"})
    run(skills, "list")
    run(skills, "list", "--lock", "/flag/l.toml")
    assert store.loaded == [Path("/env/l.toml"), Path("/flag/l.toml")]
    default, default_store, _, _ = cli()
    run(default, "list")
    assert default_store.loaded == [Path("ei-skills.lock.toml")]
    blank, blank_store, _, _ = cli(environment={"EI_SKILL_LOCK": "   "})
    run(blank, "list")
    assert blank_store.loaded == [Path("ei-skills.lock.toml")]


def test_the_skills_live_in_a_folder_beside_the_default_lock() -> None:
    skills, _, editor, _ = cli()
    run(skills, "add", "plain_style.toml")
    assert editor.calls[0][1] == Path("skills")


def test_add_that_the_editor_refuses_is_a_setup_error_and_nothing_is_saved(
    capsys: pytest.CaptureFixture[str],
) -> None:
    refusal = ApplicationError(code="SKILL_INVALID", message="it has unknown keys", http_status=422)
    skills, store, _, _ = cli(editor=Editor(fail=refusal))
    assert run(skills, "add", "--lock", "/p/l.toml", "x.toml") == 2
    assert "error: it has unknown keys" in capsys.readouterr().err
    assert store.saved == []


def test_a_value_error_and_an_os_error_are_setup_errors_too(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        run(cli(editor=Editor(fail=ValueError("not good")))[0], "add", "--lock", "/p/l", "x") == 2
    )
    assert "error: not good" in capsys.readouterr().err
    full = OSError(28, "No space left on device")
    assert run(cli(store=Store(fail=full))[0], "list", "--lock", "/p/l") == 2
    assert "error: No space left on device" in capsys.readouterr().err
    assert run(cli(store=Store(fail=OSError()))[0], "list", "--lock", "/p/l") == 2
    assert "error: OSError" in capsys.readouterr().err


# --------------------------------------------------------------------- enable/disable/remove
def test_enable_and_disable_change_one_stage_and_save(capsys: pytest.CaptureFixture[str]) -> None:
    skills, store, editor, _ = cli(Store(SkillLock((entry(),))))
    assert run(skills, "enable", "--lock", "/p/l.toml", "plain_style", "outline") == 0
    assert editor.calls == [("enable", Path("/p/skills"), "plain_style", "outline")]
    saved = store.saved[0][1].entry("plain_style")
    assert saved is not None and saved.stages == ("outline",)
    out = capsys.readouterr().out
    assert "enabled plain_style for stage outline" in out
    assert "wrote /p/l.toml; review the change like any other commit" in out
    assert run(skills, "disable", "--lock", "/p/l.toml", "plain_style", "outline") == 0
    assert editor.calls[1] == ("disable", "plain_style", "outline")
    assert "disabled plain_style for stage outline" in capsys.readouterr().out


def test_remove_unlocks_the_skill_and_names_where_its_copy_was(
    capsys: pytest.CaptureFixture[str],
) -> None:
    skills, store, editor, _ = cli(Store(SkillLock((entry(),))))
    assert run(skills, "remove", "--lock", "/p/l.toml", "plain_style") == 0
    assert editor.calls == [("remove", Path("/p/skills"), "plain_style")]
    assert store.saved[0][1].entries == ()
    assert "removed plain_style and its copy in /p/skills" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [("enable", "x", "outline"), ("disable", "x", "outline"), ("remove", "x"), ("verify",)],
)
def test_changing_or_checking_with_no_lock_file_is_a_setup_error(
    argv: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    skills, store, editor, _ = cli()
    assert run(skills, *argv, "--lock", "/p/none.toml") == 2
    assert "error: no skill lock at /p/none.toml" in capsys.readouterr().err
    assert editor.calls == [] and store.saved == []


def test_a_change_the_editor_refuses_saves_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    refusal = ApplicationError(code="SKILL_UNKNOWN", message="no skill named 'x'", http_status=422)
    skills, store, _, _ = cli(Store(SkillLock()), Editor(fail=refusal))
    assert run(skills, "enable", "--lock", "/p/l.toml", "x", "outline") == 2
    assert "error: no skill named 'x'" in capsys.readouterr().err and store.saved == []


# ----------------------------------------------------------------------------------- list
def test_list_with_no_lock_says_so_and_is_not_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli()[0], "list", "--lock", "/p/none.toml") == 0
    assert capsys.readouterr().out == "no skill lock at /p/none.toml\n"


def test_list_of_an_empty_lock_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli(Store(SkillLock()))[0], "list", "--lock", "/p/l.toml") == 0
    assert capsys.readouterr().out == "/p/l.toml locks no skills\n"


def test_list_shows_each_skill_with_its_short_hash_and_stages_in_name_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock = SkillLock((entry("zed_one", ("outline", "research")), entry("alpha_one")))
    assert run(cli(Store(lock))[0], "list", "--lock", "/p/l.toml") == 0
    assert capsys.readouterr().out == (
        f"alpha_one@2  {A[:12]}  enabled for no stage\n"
        f"zed_one@2  {A[:12]}  enabled for outline research\n"
    )


# --------------------------------------------------------------------------------- verify
def test_verify_when_everything_matches_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    lock = SkillLock((entry("a_one"), entry("b_one")))
    skills, _, _, verifier = cli(Store(lock))
    assert run(skills, "verify", "--lock", "/p/l.toml") == 0
    assert capsys.readouterr().out == "all 2 skills match the lock\n"
    assert verifier.asked == [(lock, Path("/p/skills"))]


def test_verify_lists_each_problem_and_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    lock = SkillLock((entry("a_one"), entry("b_one"), entry("c_one")))
    skills = cli(Store(lock), verifier=Verifier("skill 'a_one': changed", "skill 'b_one': gone"))[0]
    assert run(skills, "verify", "--lock", "/p/l.toml") == 1
    assert capsys.readouterr().out == (
        "skill 'a_one': changed\nskill 'b_one': gone\n2 of 3 skills no longer match the lock\n"
    )


def test_verify_of_an_empty_lock_has_nothing_to_do(capsys: pytest.CaptureFixture[str]) -> None:
    skills, _, _, verifier = cli(Store(SkillLock()))
    assert run(skills, "verify", "--lock", "/p/l.toml") == 0
    assert capsys.readouterr().out == "/p/l.toml locks no skills; nothing to verify\n"
    assert verifier.asked == []


# ------------------------------------------------------------------- what a skill says is data
def test_what_a_skill_says_is_printed_on_one_line_with_controls_replaced_and_long_text_cut(
    capsys: pytest.CaptureFixture[str],
) -> None:
    text = "Line one.\nLine two.\t" + "x" * 300

    class Wordy(Editor):
        def add(self, lock: SkillLock, folder: Path, source: Path, replace: bool):  # type: ignore[no-untyped-def]
            made = skill(parts=(("outline", text),), description="Fine\tdescription")
            return SkillLockAddition(lock.with_entry(entry(), replace), made)

    assert run(cli(editor=Wordy())[0], "add", "--lock", "/p/l.toml", "x.toml") == 0
    out = capsys.readouterr().out
    assert "  Fine description\n" in out
    [part] = [line for line in out.splitlines() if line.startswith("  outline (")]
    assert part.startswith("  outline (320 characters): Line one. Line two. xxx")
    assert part.endswith("…") and len(part.split(": ", 1)[1]) == 100


def test_a_problem_text_from_a_file_is_cleaned_and_cut_too(
    capsys: pytest.CaptureFixture[str],
) -> None:
    nasty = "skill 'a_one': line\x1b[31mred\nnext " + "y" * 600
    lock = SkillLock((entry("a_one"),))
    assert run(cli(Store(lock), verifier=Verifier(nasty))[0], "verify", "--lock", "/p/l.toml") == 1
    first = capsys.readouterr().out.splitlines()[0]
    assert "\x1b" not in first and first.startswith("skill 'a_one': line [31mred next")
    assert len(first) == 400 and first.endswith("…")


# ----------------------------------------------------------------------------------- import
def test_import_passes_everything_on_and_says_what_it_wrote_and_how_to_lock_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    importer = Importer()
    skills = cli(importer=importer)[0]
    code = run(
        skills,
        "import",
        "refs/research-methodology",
        "--stage",
        "research",
        "--stage",
        "outline",
        "--section",
        "One",
        "--section",
        "Two",
        "--name",
        "mine",
        "--version",
        "3",
        "--out",
        "out/mine.toml",
    )
    assert code == 0
    assert importer.calls == [
        (
            Path("refs/research-methodology"),
            "mine",
            3,
            ("research", "outline"),
            ("One", "Two"),
            False,
            Path("out/mine.toml"),
        )
    ]
    out = capsys.readouterr().out
    assert "wrote research_methodology.toml: research_methodology@2" in out
    assert "sections: One, Two" in out and "research: 12 characters" in out
    assert "read the file before you lock it" in out
    assert "then lock it: ei skills add research_methodology.toml" in out
    assert "shortened" not in out and "set aside" not in out


def test_import_defaults_are_no_name_version_one_every_section_and_the_default_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    importer = Importer()
    assert run(cli(importer=importer)[0], "import", "SKILL.md", "--stage", "research") == 0
    assert importer.calls == [(Path("SKILL.md"), None, 1, ("research",), (), False, None)]
    capsys.readouterr()


def test_import_says_when_it_shortened_the_description_and_what_it_set_aside(
    capsys: pytest.CaptureFixture[str],
) -> None:
    importer = Importer(ignored=("allowed-tools", "domains"), description_shortened=True)
    run(cli(importer=importer)[0], "import", "SKILL.md", "--stage", "research")
    out = capsys.readouterr().out
    assert "the description was shortened to fit its limit" in out
    assert "set aside, because a skill grants nothing: allowed-tools, domains" in out


def test_import_shows_what_the_file_said_safely(capsys: pytest.CaptureFixture[str]) -> None:
    importer = Importer(sections=("Bad\x1b[31m title",), ignored=("k\x07ey",))
    run(cli(importer=importer)[0], "import", "SKILL.md", "--stage", "research")
    out = capsys.readouterr().out
    assert "\x1b" not in out and "\x07" not in out


def test_import_that_cannot_be_done_exits_2_with_one_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = ApplicationError("SKILL_IMPORT_TOO_LARGE", "choose sections with --section", 422)
    assert run(cli(importer=Importer(failure))[0], "import", "SKILL.md", "--stage", "research") == 2
    assert capsys.readouterr().err.strip() == "error: choose sections with --section"


def test_import_without_a_stage_leaves_the_refusal_to_the_importer_and_shows_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = ApplicationError("SKILL_IMPORT_INVALID", "name at least one stage", 422)
    importer = Importer(failure)
    assert run(cli(importer=importer)[0], "import", "SKILL.md") == 2
    assert importer.calls == [(Path("SKILL.md"), None, 1, (), (), False, None)]
    assert capsys.readouterr().err.strip() == "error: name at least one stage"


def test_import_with_reference_passes_the_flag_and_shows_each_reference_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reference = skill(
        name="research_methodology",
        parts=(),
        sections=(("Source Evaluation", "Use SIFT."), ("Database Searching", "Use Boolean.")),
    )
    importer = Importer(skill=reference, sections=("Source Evaluation", "Database Searching"))
    assert run(cli(importer=importer)[0], "import", "SKILL.md", "--reference") == 0
    assert importer.calls == [(Path("SKILL.md"), None, 1, (), (), True, None)]
    out = capsys.readouterr().out
    assert "reference Source Evaluation: 9 characters" in out
    assert "reference Database Searching: 12 characters" in out


def test_import_never_touches_the_lock() -> None:
    skills, store, editor, _ = cli()
    run(skills, "import", "SKILL.md", "--stage", "research")
    assert store.loaded == [] and store.saved == [] and editor.calls == []


def test_add_shows_each_reference_section_and_says_it_may_be_enabled_for_any_stage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reference = skill(
        name="research_methodology",
        parts=(),
        sections=(("Source Evaluation", "Use SIFT."), ("Database Searching", "Use Boolean.")),
    )

    class ReferenceEditor(Editor):
        def add(
            self, lock: SkillLock, folder: Path, source: Path, replace: bool
        ) -> SkillLockAddition:
            return SkillLockAddition(
                lock.with_entry(entry("research_methodology"), replace), reference
            )

    skills = cli(editor=ReferenceEditor())[0]
    assert run(skills, "add", "--lock", "/x/l.toml", "/tmp/research_methodology.toml") == 0
    out = capsys.readouterr().out
    assert "locked research_methodology@2: 0 parts, 2 reference sections" in out
    assert "reference Source Evaluation (9 characters): Use SIFT." in out
    assert "reference Database Searching (12 characters): Use Boolean." in out
    assert "(it has text for any stage)" in out
