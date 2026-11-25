"""The continuity checker: near-miss names and places, ages outside the bible, events out of order."""

import pytest

from engineering_influence.models.continuity_finding import ContinuityFinding
from engineering_influence.models.story_bible import StoryBible
from engineering_influence.models.story_character import StoryCharacter
from engineering_influence.models.story_event import StoryEvent
from engineering_influence.services.continuity_checker import ContinuityChecker


def bible(**changes: object) -> StoryBible:
    fields: dict[str, object] = {
        "premise": "a heist in a harbour town",
        "characters": (
            StoryCharacter("Katherine Marsh", ("Kit",), 34),
            StoryCharacter("Daniel Okafor", (), 41),
        ),
        "places": ("Harborough", "Saint Brannock"),
        "timeline": (StoryEvent(1, "the fire"), StoryEvent(5, "the trial")),
    }
    fields.update(changes)
    return StoryBible(**fields)  # type: ignore[arg-type]


def check(*chapters: str, **changes: object) -> tuple[ContinuityFinding, ...]:
    return ContinuityChecker().check(bible(**changes), chapters)


def lines(*chapters: str, **changes: object) -> list[str]:
    return [item.render() for item in check(*chapters, **changes)]


def test_a_chapter_that_agrees_with_the_bible_has_no_findings() -> None:
    text = (
        "Katherine Marsh walked to Harborough. Kit, 34, met Daniel Okafor at Saint Brannock. "
        "After the fire came the trial."
    )
    assert check(text) == ()


def test_a_name_one_letter_off_is_reported() -> None:
    assert lines("Katharine Marsh came in.") == [
        "chapter 1 (name): the chapter writes Katharine; the bible has Katherine"
    ]


def test_the_finding_carries_the_bible_word_and_the_chapters_word() -> None:
    (item,) = check("Katharine Marsh came in.")
    assert (item.chapter, item.kind, item.expected, item.found) == (
        1,
        "name",
        "Katherine",
        "Katharine",
    )


def test_a_place_one_letter_off_is_reported_as_a_place() -> None:
    (item,) = check("They reached Harborogh at dusk.")
    assert (item.kind, item.expected, item.found) == ("place", "Harborough", "Harborogh")


@pytest.mark.parametrize(
    "written",
    ["Katherin", "Katherinne", "Katherien", "Katherane"],
    ids=["dropped", "added", "swapped", "changed"],
)
def test_a_dropped_added_swapped_or_changed_letter_is_one_edit(written: str) -> None:
    (item,) = check(f"{written} sat down.")
    assert item.found == written


@pytest.mark.parametrize("written", ["Katherxxe", "Katherinexx", "Kathrn"])
def test_two_edits_are_a_different_word(written: str) -> None:
    assert check(f"{written} sat down.") == ()


def test_a_swap_of_two_letters_that_are_not_neighbours_is_two_edits() -> None:
    assert check("Ketharina sat down.") == ()
    assert check("Karherite sat down.") == ()


def test_two_neighbouring_letters_changed_without_a_swap_is_two_edits() -> None:
    assert check("Katherxz sat down.") == ()


def test_a_word_that_is_a_known_form_is_never_reported() -> None:
    assert check("Katherine, Marsh, Kit, Daniel, Okafor, Harborough, Saint, Brannock.") == ()


def test_the_other_words_of_a_name_and_a_place_are_known_too() -> None:
    assert [item.found for item in check("Okafer and Marsch and Brannok.")] == [
        "Okafer",
        "Marsch",
        "Brannok",
    ]


def test_a_word_the_chapter_also_writes_in_lower_case_is_a_common_word() -> None:
    assert [item.found for item in check("Marsha laughed.")] == ["Marsha"]
    assert check("Marsha laughed. A marsha is a word.") == ()


def test_a_common_word_is_skipped_in_the_chapter_it_appears_in_only() -> None:
    assert [item.chapter for item in check("Okafer ran.", "okafer is a word. Okafer ran.")] == [1]


def test_a_word_that_starts_in_lower_case_is_not_reported() -> None:
    assert check("katharine sat down.") == ()


def test_words_shorter_than_four_letters_are_not_compared() -> None:
    assert check("Kat and Kitt and Kim sat down.", characters=(StoryCharacter("Kit"),)) == ()


def test_a_short_known_word_is_never_matched_by_a_longer_one() -> None:
    assert check("Kitty sat down.", characters=(StoryCharacter("Kit"),)) == ()
    assert check("Anna sat down.", characters=(StoryCharacter("Ana"),)) == ()


def test_a_misspelling_is_reported_once_for_a_chapter_however_often_it_appears() -> None:
    assert len(check("Katharine came. Katharine went. Katharine slept.")) == 1


def test_a_misspelling_is_reported_in_each_chapter_it_appears_in() -> None:
    assert [item.chapter for item in check("Katharine came.", "No one.", "Katharine went.")] == [
        1,
        3,
    ]


def test_two_misspellings_in_a_chapter_are_two_findings_in_reading_order() -> None:
    assert [item.found for item in check("Daniel Okafer met Katharine.")] == ["Okafer", "Katharine"]


def test_a_possessive_is_read_as_the_name() -> None:
    assert check("Katherine's coat and Harborough's quay.") == ()
    assert [item.found for item in check("Katharine's coat.")] == ["Katharine"]


def test_a_hyphenated_word_is_one_word() -> None:
    assert [item.found for item in check("Saint-Brannok came.", places=("Saint-Brannock",))] == [
        "Saint-Brannok"
    ]


def test_an_alias_word_is_known() -> None:
    assert check("Kate sat down.", characters=(StoryCharacter("Katherine", ("Kate",)),)) == ()


def test_a_word_that_is_a_name_and_part_of_a_place_is_reported_as_a_name() -> None:
    value = bible(characters=(StoryCharacter("Elena Marsh"),), places=("Marsh",))
    (item,) = ContinuityChecker().check(value, ("Marsch came.",))
    assert item.kind == "name"


def test_a_bible_with_no_names_or_places_has_nothing_to_compare() -> None:
    assert check("Anything at all Happened.", characters=(), places=(), timeline=()) == ()


def test_the_first_known_word_one_edit_away_is_the_one_named() -> None:
    value = bible(characters=(StoryCharacter("Mara"), StoryCharacter("Mark")), places=())
    (item,) = ContinuityChecker().check(value, ("Marx came.",))
    assert item.expected == "Mara"


@pytest.mark.parametrize(
    "text",
    [
        "Katherine Marsh, 34, sat down.",
        "Katherine was 34 years old.",
        "Katherine is 34 year old.",
        "Katherine turned 34 years old.",
        "Katherine turns 34 years old.",
        "A 34-year-old Katherine sat down.",
        "A 34 year old Katherine sat down.",
        "Kit, 34, sat down.",
    ],
)
def test_each_way_of_stating_an_age_is_read_and_a_matching_age_passes(text: str) -> None:
    assert check(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "Katherine, 39, sat down.",
        "Katherine was 39 years old.",
        "A 39-year-old Katherine sat down.",
        "Kit, 39, sat down.",
        "Katherine Marsh, 39, sat down.",
    ],
)
def test_each_way_of_stating_an_age_is_checked(text: str) -> None:
    (item,) = check(text)
    assert (item.kind, item.expected, item.found) == ("age", "34", "39")
    assert item.message == "Katherine Marsh is 39 here; the bible has 34"


def test_an_age_may_grow_by_the_span_of_the_story() -> None:
    assert check("Katherine, 36,", span_years=2) == ()
    assert check("Katherine, 34,", span_years=2) == ()
    (item,) = check("Katherine, 37,", span_years=2)
    assert item.expected == "34 to 36"
    assert item.message == "Katherine Marsh is 37 here; the bible has 34 to 36"
    (younger,) = check("Katherine, 33,", span_years=2)
    assert younger.found == "33"


def test_a_character_with_no_age_is_not_checked() -> None:
    assert check("Ana, 99, sat.", characters=(StoryCharacter("Ana"),)) == ()


def test_a_number_that_is_not_an_age_is_not_read() -> None:
    assert check("Katherine was 3 minutes late. Katherine, 3 of them, ran.") == ()
    assert check("Katherine, 99 percent sure, ran.") == ()


def test_a_wrong_age_is_reported_once_for_a_chapter_however_often_it_is_said() -> None:
    assert len(check("Katherine, 39, sat. Kit, 39, stood. A 39-year-old Katherine ran.")) == 1


def test_two_different_wrong_ages_are_two_findings_in_reading_order() -> None:
    text = "A 20-year-old Katherine sat. Katherine, 50, stood."
    assert [item.found for item in check(text)] == ["20", "50"]
    text = "Katherine, 50, stood. A 20-year-old Katherine sat."
    assert [item.found for item in check(text)] == ["50", "20"]


def test_ages_are_checked_in_each_chapter() -> None:
    assert [item.chapter for item in check("Kit, 39,", "Kit, 34,", "Kit, 39,")] == [1, 3]


def test_another_characters_age_is_not_taken_for_this_ones() -> None:
    assert check("Daniel, 41, sat. Katherine, 34, stood.") == ()
    assert [item.found for item in check("Daniel, 34, sat.")] == ["34"]


def test_a_name_inside_a_longer_word_is_not_an_age_claim() -> None:
    assert [item.kind for item in check("Okafor, 41, sat. Nokafor, 99, ran.")] == ["name"]
    assert [item.kind for item in check("A 99-year-old Katherines sat.")] == ["name"]


def test_events_in_the_order_of_the_bible_pass() -> None:
    assert check("The fire came.", "Then the trial.") == ()
    assert check("The fire and the trial, in one breath.") == ()


def test_an_event_mentioned_after_a_later_one_is_reported() -> None:
    (item,) = check("The trial began.", "Years before, the fire.")
    assert (item.chapter, item.kind) == (2, "timeline")
    assert item.expected == "the fire before the trial"
    assert item.found == "the fire after the trial"
    assert (
        item.message
        == "'the fire' comes after 'the trial' in the chapters but before it in the bible"
    )


def test_an_inversion_inside_one_chapter_is_read_by_position() -> None:
    assert [item.chapter for item in check("The trial ended. The fire had started it.")] == [1]
    assert check("The fire started it. The trial ended.") == ()


def test_an_event_that_happens_together_with_another_is_not_out_of_order() -> None:
    value = {"timeline": (StoryEvent(1, "the fire"), StoryEvent(1, "the flood"))}
    assert check("The flood came. The fire came.", **value) == ()


def test_only_the_first_mention_of_an_event_counts() -> None:
    assert check("The fire came.", "The trial came.", "The fire again.") == ()


def test_an_event_is_found_whatever_its_case_and_only_as_whole_words() -> None:
    assert [item.chapter for item in check("THE TRIAL began.", "the FIRE.")] == [2]
    assert check("The trials began.", "The fire.") == ()
    assert check("The trial began.", "Backfire, the firefighters said.") == ()


def test_an_event_a_chapter_never_mentions_is_not_reported() -> None:
    assert check("Nothing happened.") == ()


def test_the_latest_event_is_kept_after_an_inversion() -> None:
    value = {
        "timeline": (
            StoryEvent(1, "the fire"),
            StoryEvent(3, "the move"),
            StoryEvent(5, "the trial"),
        )
    }
    found = check("The trial.", "The move.", "The fire.", **value)
    assert [(item.chapter, item.expected) for item in found] == [
        (2, "the move before the trial"),
        (3, "the fire before the trial"),
    ]


def test_an_event_label_with_punctuation_is_matched_literally() -> None:
    value = {"timeline": (StoryEvent(1, "the (first) fire"), StoryEvent(2, "the 2nd fire"))}
    assert check("The 2nd fire.", "The (first) fire.", **value) != ()
    assert check("The (first) fire.", "The 2nd fire.", **value) == ()


def test_findings_come_in_chapter_order_and_in_kind_order_within_a_chapter() -> None:
    found = check(
        "Katherine, 50, met Okafer in Harborogh.",
        "The trial. Katharine.",
        "The fire.",
    )
    assert [(item.chapter, item.kind) for item in found] == [
        (1, "name"),
        (1, "place"),
        (1, "age"),
        (2, "name"),
        (3, "timeline"),
    ]


def test_at_most_two_hundred_findings_are_returned() -> None:
    chapters = tuple("Katharine and Katherin." for _ in range(101))
    assert len(check(*chapters)) == 200


def test_two_hundred_findings_are_all_returned() -> None:
    chapters = tuple("Katharine." for _ in range(200))
    assert len(check(*chapters)) == 200


def test_from_one_to_two_hundred_chapters_are_checked() -> None:
    assert check(*("Nothing." for _ in range(ContinuityChecker.MAX_CHAPTERS))) == ()
    with pytest.raises(ValueError, match="one to 200 chapters"):
        check(*("Nothing." for _ in range(ContinuityChecker.MAX_CHAPTERS + 1)))
    with pytest.raises(ValueError, match="one to 200 chapters"):
        check()


def test_the_chapters_are_a_tuple_of_text() -> None:
    with pytest.raises(ValueError, match="one to 200 chapters"):
        ContinuityChecker().check(bible(), ["Nothing."])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="a chapter is text"):
        ContinuityChecker().check(bible(), ("Nothing.", 3))  # type: ignore[arg-type]


def test_a_timeline_finding_in_an_early_chapter_comes_before_a_later_chapters_spelling() -> None:
    found = check("The trial. The fire.", "Katharine.")
    assert [(item.chapter, item.kind) for item in found] == [(1, "timeline"), (2, "name")]


def test_within_a_chapter_names_come_before_places_whatever_the_reading_order() -> None:
    found = check("Harborogh and Okafer.")
    assert [item.kind for item in found] == ["name", "place"]


def test_a_script_without_capitals_is_not_compared() -> None:
    value = {"characters": (StoryCharacter("\u05e9\u05dc\u05d5\u05de\u05d9"),), "places": ()}
    assert check("\u05e9\u05dc\u05d5\u05de\u05d4 sat down.", **value) == ()


def test_a_capitalised_word_shorter_than_the_minimum_is_not_compared() -> None:
    assert check("Kat sat down.", characters=(StoryCharacter("Kate"),)) == ()
    assert [
        item.found for item in check("Kath sat down.", characters=(StoryCharacter("Kate"),))
    ] == ["Kath"]


def test_a_known_word_is_not_a_misspelling_of_another_known_word() -> None:
    value = {"characters": (StoryCharacter("Mara"), StoryCharacter("Mark")), "places": ()}
    assert check("Mara and Mark sat down.", **value) == ()


def test_the_bibles_first_spelling_of_a_shared_word_is_the_one_shown() -> None:
    value = {
        "characters": (StoryCharacter("Elena Marsh"), StoryCharacter("Bo MARSH")),
        "places": (),
    }
    (item,) = check("Marsch came.", **value)
    assert item.expected == "Marsh"


def test_an_alias_is_compared_like_a_name() -> None:
    value = {"characters": (StoryCharacter("Katherine", ("Katie",)),), "places": ()}
    (item,) = check("Katia sat down.", **value)
    assert (item.kind, item.expected, item.found) == ("name", "Katie", "Katia")


def test_three_differing_letters_are_not_a_swap() -> None:
    assert check("Nadera sat down.", characters=(StoryCharacter("Anders"),), places=()) == ()


def test_a_swap_of_letters_that_are_far_apart_is_not_a_neighbour_swap() -> None:
    assert check("Harsm sat down.", characters=(StoryCharacter("Marsh"),), places=()) == ()


@pytest.mark.parametrize("written", ["Mrysh", "Myash"])
def test_two_neighbouring_letters_that_are_not_swapped_are_two_edits(written: str) -> None:
    assert check(f"{written} sat down.", characters=(StoryCharacter("Marsh"),), places=()) == ()


@pytest.mark.parametrize("verb", ["is", "was", "turned", "turns"])
def test_each_verb_of_the_second_age_shape_is_checked(verb: str) -> None:
    (item,) = check(f"Katherine {verb} 39 years old.")
    assert item.found == "39"


def test_ages_of_up_to_three_digits_are_read() -> None:
    assert [item.found for item in check("Katherine, 120, sat.")] == ["120"]
    assert [item.found for item in check("Katherine was 120 years old.")] == ["120"]
    assert [item.found for item in check("A 120-year-old Katherine sat.")] == ["120"]
    assert check("Katherine, 1234, sat.") == ()


def test_a_name_that_ends_another_word_is_not_an_age_claim() -> None:
    assert [item.kind for item in check("XKatherine, 99, sat.")] == ["name"]
    assert [item.kind for item in check("XKatherine was 99 years old.")] == ["name"]


def test_an_event_inside_a_longer_word_is_not_a_mention() -> None:
    assert check("The trial began.", "They bathe fire in water.") == ()


def test_digits_and_underscores_belong_to_no_word() -> None:
    assert check("Katherine2 and Marsh_x sat down.") == ()
