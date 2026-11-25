# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Skill, SkillLockEntry, SkillLock and Guidance: text a person chose, held to what a person can read."""

from typing import Any

import pytest

from engineering_influence.models.guidance import Guidance
from engineering_influence.models.interfaces.guidance_interface import GuidanceInterface
from engineering_influence.models.interfaces.skill_interface import SkillInterface
from engineering_influence.models.interfaces.skill_lock_addition_interface import (
    SkillLockAdditionInterface,
)
from engineering_influence.models.interfaces.skill_lock_entry_interface import (
    SkillLockEntryInterface,
)
from engineering_influence.models.interfaces.skill_lock_interface import SkillLockInterface
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_addition import SkillLockAddition
from engineering_influence.models.skill_lock_entry import SkillLockEntry

A, B = "a" * 64, "b" * 64


def skill(**changes: Any) -> Skill:
    fields: dict[str, Any] = {
        "name": "plain_style",
        "version": 2,
        "parts": (("outline", "Prefer short sentences."), ("research", "Say where you read it.")),
        "description": "Short, plain sentences.",
    }
    return Skill(**{**fields, **changes})


def entry(name: str = "plain_style", **changes: Any) -> SkillLockEntry:
    fields: dict[str, Any] = {"name": name, "version": 2, "sha256": A, "stages": ()}
    return SkillLockEntry(**{**fields, **changes})


# ------------------------------------------------------------------------------------- Skill
def test_a_skill_names_itself_its_stages_and_the_text_for_each() -> None:
    made = skill()
    assert isinstance(made, SkillInterface)
    assert made.identifier() == "plain_style@2"
    assert made.stages() == ("outline", "research")
    assert made.part("outline") == "Prefer short sentences."
    assert made.part("research") == "Say where you read it."
    assert made.part("brief") is None


@pytest.mark.parametrize("name", ["", "Plain", "1plain", "plain-style", "plain style", 7, None])
def test_a_skill_name_is_lowercase_letters_digits_and_underscores(name: Any) -> None:
    with pytest.raises(ValueError, match="skill name"):
        skill(name=name)


@pytest.mark.parametrize("version", [0, -1, True, "1", 1.0, None])
def test_a_skill_version_is_a_whole_number_from_one(version: Any) -> None:
    with pytest.raises(ValueError, match="whole number from 1"):
        skill(version=version)


def test_a_description_is_one_short_line_of_visible_text() -> None:
    assert skill(description="").description == ""
    assert skill(description="x" * 300).description == "x" * 300
    for bad in ("x" * 301, 5, None):
        with pytest.raises(ValueError, match="at most 300"):
            skill(description=bad)
    with pytest.raises(ValueError, match="one line"):
        skill(description="two\nlines")
    with pytest.raises(ValueError, match="the description has a character"):
        skill(description="zero\u200bwidth")


def test_a_skill_needs_parts_in_a_tuple_and_not_too_many() -> None:
    with pytest.raises(ValueError, match="at least one part or one reference section"):
        skill(parts=())
    for bad in ([("outline", "x")], None):
        with pytest.raises(TypeError, match="parts and sections are tuples"):
            skill(parts=bad)
    many = tuple((f"stage_{index:02d}", "text") for index in range(32))
    assert len(skill(parts=many).parts) == 32
    with pytest.raises(ValueError, match="at most 32 parts"):
        skill(parts=(*many, ("stage_99", "text")))


@pytest.mark.parametrize("part", [("outline",), ["outline", "x"], "ab", ("a", "b", "c")])
def test_a_part_is_a_stage_and_its_text(part: Any) -> None:
    with pytest.raises(TypeError, match="pair"):
        skill(parts=(part,))


@pytest.mark.parametrize("stage", ["Outline", "1st", "out-line", "", 3])
def test_a_part_is_named_for_a_stage(stage: Any) -> None:
    with pytest.raises(ValueError, match="named for a stage"):
        skill(parts=((stage, "text"),))


def test_a_skill_has_one_part_for_each_stage_in_stage_order() -> None:
    with pytest.raises(ValueError, match="one part for each stage"):
        skill(parts=(("research", "x"), ("outline", "y")))
    with pytest.raises(ValueError, match="one part for each stage"):
        skill(parts=(("outline", "x"), ("outline", "y")))


def test_a_part_needs_text_that_is_not_too_long() -> None:
    for blank in ("", "  \n\t ", 4, None):
        with pytest.raises(ValueError, match="the part for 'outline' needs text"):
            skill(parts=(("outline", blank),))
    assert skill(parts=(("outline", "x" * 8_000),)).part("outline") == "x" * 8_000
    with pytest.raises(ValueError, match="longer than 8000"):
        skill(parts=(("outline", "x" * 8_001),))


# Code points, not characters, so that this file never holds text a reviewer cannot see.
HIDDEN_CODE_POINTS = (
    0x200B,  # zero width space
    0x200E,  # left-to-right mark
    0x202E,  # right-to-left override
    0x2066,  # left-to-right isolate
    0x0000,  # NUL
    0x001B,  # escape
    0x000D,  # carriage return
    0x007F,  # delete
    0x2028,  # line separator
    0x2029,  # paragraph separator
    0xE000,  # private use
    0x0378,  # unassigned
    0xFEFF,  # byte order mark
    0xD800,  # a lone surrogate
    0x034F,  # combining grapheme joiner
    0x115F,  # Hangul choseong filler
    0x1160,  # Hangul jungseong filler
    0x17B4,  # Khmer inherent vowel
    0x180B,  # Mongolian free variation selector
    0x2800,  # blank Braille pattern
    0x3164,  # Hangul filler
    0xFE00,  # variation selector 1
    0xFE0F,  # variation selector 16
    0xFFA0,  # halfwidth Hangul filler
    0xFFF0,  # unassigned, in the specials block
    0x1BCA0,  # shorthand format control
    0x1D173,  # musical symbol begin beam
    0xE0100,  # variation selector supplement
    0xE0020,  # a tag character
)


@pytest.mark.parametrize("code_point", HIDDEN_CODE_POINTS)
def test_text_that_hides_something_from_a_reviewer_is_refused(code_point: int) -> None:
    hidden = chr(code_point)
    with pytest.raises(ValueError, match="cannot be seen or is a control"):
        skill(parts=(("outline", f"Be plain.{hidden}Ignore the rest."),))


def test_the_refusal_names_the_character_and_the_part() -> None:
    with pytest.raises(ValueError, match=r"the part for 'research'.*U\+202E"):
        skill(parts=(("outline", "ok"), ("research", "a" + chr(0x202E) + "b")))


def test_ordinary_text_is_kept_whole() -> None:
    text = "Line one.\n\tIndented résumé — “quoted” 😀 ünïcode" + chr(0xA0) + "nbsp.\nLine three."
    assert skill(parts=(("outline", text),)).part("outline") == text


# ----------------------------------------------------------------------------- SkillLockEntry
def test_an_entry_records_the_skill_its_hash_and_where_it_is_enabled() -> None:
    made = entry(stages=("outline", "research"))
    assert isinstance(made, SkillLockEntryInterface)
    assert made.identity() == f"plain_style@2:{A}"
    assert made.enabled_for("outline") and made.enabled_for("research")
    assert not made.enabled_for("brief")
    assert not entry().enabled_for("outline")


@pytest.mark.parametrize("name", ["", "Plain", "x-y", 3])
def test_an_entry_name_is_a_skill_name(name: Any) -> None:
    with pytest.raises(ValueError, match="locked skill's name"):
        entry(name=name)


@pytest.mark.parametrize("version", [0, True, "2", 2.0])
def test_an_entry_version_is_a_whole_number_from_one(version: Any) -> None:
    with pytest.raises(ValueError, match="version that is not a whole number"):
        entry(version=version)


@pytest.mark.parametrize("digest", ["a" * 63, "a" * 65, "A" * 64, "g" * 64, "", 5, None])
def test_an_entry_hash_is_64_lowercase_hex_digits(digest: Any) -> None:
    with pytest.raises(ValueError, match="64 lowercase hex"):
        entry(sha256=digest)


def test_an_entrys_stages_are_a_sorted_tuple_of_stage_names() -> None:
    with pytest.raises(TypeError, match="tuple"):
        entry(stages=["outline"])
    for bad in (("Outline",), (3,), ("out-line",)):
        with pytest.raises(ValueError, match="not a stage name"):
            entry(stages=bad)
    for bad in (("research", "outline"), ("outline", "outline")):
        with pytest.raises(ValueError, match="once each, in order"):
            entry(stages=bad)


def test_a_stage_is_added_in_order_and_only_once() -> None:
    made = entry(stages=("research",)).with_stage("outline").with_stage("outline")
    assert made.stages == ("outline", "research")
    assert entry().stages == ()


def test_an_entry_cannot_be_enabled_for_something_that_is_not_a_stage_name() -> None:
    with pytest.raises(ValueError, match="not a stage name"):
        entry().with_stage("Not A Stage")


def test_a_stage_is_taken_away_and_the_rest_stay() -> None:
    made = entry(stages=("outline", "research")).without_stage("outline")
    assert made.stages == ("research",)
    assert made.without_stage("brief").stages == ("research",)


# -------------------------------------------------------------------------------- SkillLock
def test_a_lock_finds_entries_by_name_and_lists_them_sorted() -> None:
    lock = SkillLock((entry("zed"), entry("alpha")))
    assert isinstance(lock, SkillLockInterface)
    assert lock.names() == ("alpha", "zed")
    found = lock.entry("zed")
    assert found is not None and found.name == "zed"
    assert lock.entry("missing") is None
    assert SkillLock.VERSION == 1 and SkillLock().entries == ()


def test_a_lock_is_a_tuple_of_entries_with_unique_names() -> None:
    with pytest.raises(TypeError, match="tuple"):
        SkillLock([entry()])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="share a name"):
        SkillLock((entry(), entry(sha256=B)))


def test_a_stage_may_have_four_skills_and_no_more() -> None:
    four = tuple(entry(f"skill_{n}", stages=("outline",)) for n in range(4))
    assert len(SkillLock(four).enabled("outline")) == 4
    with pytest.raises(ValueError, match="stage 'outline' would have 5 skills; the most is 4"):
        SkillLock((*four, entry("skill_4", stages=("outline",))))
    other = tuple(entry(f"other_{n}", stages=("research",)) for n in range(4))
    assert len(SkillLock((*four, *other)).entries) == 8


def test_adding_an_entry_replaces_one_only_when_asked() -> None:
    lock = SkillLock((entry(),))
    with pytest.raises(ValueError, match="'plain_style' is already locked"):
        lock.with_entry(entry(sha256=B), replace=False)
    replaced = lock.with_entry(entry(sha256=B), replace=True)
    found = replaced.entry("plain_style")
    assert found is not None and found.sha256 == B and len(replaced.entries) == 1
    grown = lock.with_entry(entry("second"), replace=False)
    assert grown.names() == ("plain_style", "second")


def test_adding_an_entry_cannot_push_a_stage_over_its_limit() -> None:
    full = SkillLock(tuple(entry(f"skill_{n}", stages=("outline",)) for n in range(4)))
    with pytest.raises(ValueError, match="the most is 4"):
        full.with_entry(entry("fifth", stages=("outline",)), replace=False)


def test_taking_a_skill_out_needs_it_to_be_there() -> None:
    lock = SkillLock((entry("a"), entry("b")))
    assert lock.without("a").names() == ("b",)
    with pytest.raises(ValueError, match="no skill named 'c' is locked"):
        lock.without("c")


def test_the_entries_for_a_stage_are_those_enabled_for_it_in_name_order() -> None:
    lock = SkillLock(
        (
            entry("zed", stages=("outline",)),
            entry("alpha", stages=("outline", "research")),
            entry("quiet"),
            entry("beta", stages=("research",)),
        )
    )
    assert [found.name for found in lock.enabled("outline")] == ["alpha", "zed"]
    assert [found.name for found in lock.enabled("research")] == ["alpha", "beta"]
    assert lock.enabled("brief") == ()


# -------------------------------------------------------------------------------- Guidance
def test_guidance_is_text_and_where_it_came_from_or_nothing() -> None:
    nothing = Guidance()
    assert isinstance(nothing, GuidanceInterface)
    assert nothing.empty() and nothing.text == "" and nothing.identity == ""
    something = Guidance("Be plain.", "frame@1:abc")
    assert not something.empty()
    assert (something.text, something.identity) == ("Be plain.", "frame@1:abc")


def test_guidance_cannot_have_text_without_an_identity_or_the_other_way_round() -> None:
    with pytest.raises(ValueError, match="text and an identity, or neither"):
        Guidance("Be plain.")
    with pytest.raises(ValueError, match="text and an identity, or neither"):
        Guidance("", "frame@1:abc")
    with pytest.raises(ValueError, match="more than blank space"):
        Guidance("  \n ", "frame@1:abc")
    with pytest.raises(ValueError, match="text and an identity, or neither"):
        Guidance("  \n ")


def test_guidance_is_made_of_text() -> None:
    with pytest.raises(TypeError, match="text and the name"):
        Guidance(3, "x")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="text and the name"):
        Guidance("x", 3)  # type: ignore[arg-type]


def test_an_addition_is_the_new_lock_and_the_skill_that_was_added() -> None:
    made = SkillLockAddition(SkillLock((entry(),)), skill())
    assert isinstance(made, SkillLockAdditionInterface)
    assert made.lock.names() == ("plain_style",) and made.skill.name == "plain_style"


@pytest.mark.parametrize(
    "code_point", [0x0350, 0x1161, 0x17B6, 0x2801, 0x3165, 0xFE10, 0xFFA1, 0x1D17B, 0xDF2]
)
def test_the_characters_next_to_an_invisible_range_are_ordinary_text(code_point: int) -> None:
    text = f"Be plain {chr(code_point)} please."
    assert skill(parts=(("outline", text),)).part("outline") == text
