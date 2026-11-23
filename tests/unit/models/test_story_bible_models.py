"""The story bible and its parts: one-line, bounded, distinct, and in the order things happen."""

import pytest

from engineering_influence.models.continuity_finding import ContinuityFinding
from engineering_influence.models.story_bible import StoryBible
from engineering_influence.models.story_character import StoryCharacter
from engineering_influence.models.story_event import StoryEvent
from engineering_influence.models.story_text import StoryText


def finding(**changes: object) -> ContinuityFinding:
    fields: dict[str, object] = {
        "chapter": 3,
        "kind": "name",
        "expected": "Katherine",
        "found": "Katharine",
        "message": "the chapter writes Katharine; the bible has Katherine",
    }
    fields.update(changes)
    return ContinuityFinding(**fields)  # type: ignore[arg-type]


def test_a_story_text_is_one_printable_line_within_its_limit() -> None:
    StoryText.line("a name", "Katherine Marsh", 15)


@pytest.mark.parametrize("text", ["", "   ", None, 3])
def test_a_story_text_needs_words(text: object) -> None:
    with pytest.raises(ValueError, match="a name needs text"):
        StoryText.line("a name", text, 10)  # type: ignore[arg-type]


def test_a_story_text_is_held_to_its_limit() -> None:
    with pytest.raises(ValueError, match="a name is longer than 5 characters"):
        StoryText.line("a name", "abcdef", 5)


@pytest.mark.parametrize(
    "text", [" Ana", "Ana ", "An\na", "An\x07a", "An" + chr(0x202E) + "a", "An\ta"]
)
def test_a_story_text_is_not_padded_or_multi_line_or_hidden(text: str) -> None:
    with pytest.raises(ValueError, match="one line of printable text"):
        StoryText.line("a name", text, 50)


def test_a_character_lists_its_name_then_its_aliases() -> None:
    assert StoryCharacter("Katherine Marsh", ("Kit", "Kate"), 34).forms() == (
        "Katherine Marsh",
        "Kit",
        "Kate",
    )


def test_a_character_needs_only_a_name() -> None:
    character = StoryCharacter("Ana")
    assert (character.aliases, character.age) == ((), None)


def test_a_character_name_is_one_line() -> None:
    with pytest.raises(ValueError, match="a character's name needs text"):
        StoryCharacter(" ")


def test_a_character_name_has_a_limit() -> None:
    StoryCharacter("a" * StoryCharacter.MAX_NAME)
    with pytest.raises(ValueError, match="longer than 80"):
        StoryCharacter("a" * (StoryCharacter.MAX_NAME + 1))


def test_aliases_are_a_tuple_of_at_most_ten() -> None:
    StoryCharacter("Ana", tuple(f"alias{n}" for n in range(StoryCharacter.MAX_ALIASES)))
    with pytest.raises(ValueError, match="at most 10 aliases"):
        StoryCharacter("Ana", tuple(f"alias{n}" for n in range(StoryCharacter.MAX_ALIASES + 1)))
    with pytest.raises(ValueError, match="at most 10 aliases"):
        StoryCharacter("Ana", ["Nan"])  # type: ignore[arg-type]


def test_an_alias_is_one_line() -> None:
    with pytest.raises(ValueError, match="an alias needs text"):
        StoryCharacter("Ana", ("",))


def test_a_name_and_its_aliases_are_each_different_whatever_the_case() -> None:
    with pytest.raises(ValueError, match="each different"):
        StoryCharacter("Ana", ("ANA",))
    with pytest.raises(ValueError, match="each different"):
        StoryCharacter("Ana", ("Nan", "nan"))


@pytest.mark.parametrize("age", [0, 150])
def test_an_age_may_be_zero_or_one_hundred_and_fifty(age: int) -> None:
    assert StoryCharacter("Ana", age=age).age == age


@pytest.mark.parametrize("age", [-1, 151, True, 3.5, "34"])
def test_an_age_is_a_whole_number_in_range(age: object) -> None:
    with pytest.raises(ValueError, match="whole number from 0 to 150"):
        StoryCharacter("Ana", age=age)  # type: ignore[arg-type]


@pytest.mark.parametrize("when", [0, 1_000_000])
def test_an_event_time_may_be_at_either_end(when: int) -> None:
    assert StoryEvent(when, "the fire").when == when


@pytest.mark.parametrize("when", [-1, 1_000_001, True, 2.5, "3"])
def test_an_event_time_is_a_whole_number_in_range(when: object) -> None:
    with pytest.raises(ValueError, match="whole number from 0 to 1,000,000"):
        StoryEvent(when, "the fire")  # type: ignore[arg-type]


def test_an_event_label_is_one_line_with_a_limit() -> None:
    StoryEvent(1, "a" * StoryEvent.MAX_LABEL)
    with pytest.raises(ValueError, match="an event's label needs text"):
        StoryEvent(1, "")
    with pytest.raises(ValueError, match="longer than 120"):
        StoryEvent(1, "a" * (StoryEvent.MAX_LABEL + 1))


def test_a_finding_renders_as_one_line() -> None:
    assert (
        finding().render()
        == "chapter 3 (name): the chapter writes Katharine; the bible has Katherine"
    )


@pytest.mark.parametrize("kind", ContinuityFinding.KINDS)
def test_a_finding_may_be_of_each_kind(kind: str) -> None:
    assert finding(kind=kind).kind == kind


def test_the_kinds_of_finding_are_these_four() -> None:
    assert ContinuityFinding.KINDS == ("name", "place", "age", "timeline")


@pytest.mark.parametrize("chapter", [0, -1, True, 1.5])
def test_a_finding_names_a_chapter_from_one(chapter: object) -> None:
    with pytest.raises(ValueError, match="names a chapter from 1"):
        finding(chapter=chapter)


def test_a_finding_has_a_known_kind() -> None:
    with pytest.raises(ValueError, match="kind is one of name, place, age, timeline"):
        finding(kind="mood")


@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("expected", "what the bible has"),
        ("found", "what the chapter wrote"),
        ("message", "a finding's message"),
    ],
)
def test_a_finding_texts_are_one_line_with_a_limit(field: str, label: str) -> None:
    finding(**{field: "a" * ContinuityFinding.MAX_TEXT})
    with pytest.raises(ValueError, match=f"{label} needs text"):
        finding(**{field: ""})
    with pytest.raises(ValueError, match="longer than 300"):
        finding(**{field: "a" * (ContinuityFinding.MAX_TEXT + 1)})


def bible(**changes: object) -> StoryBible:
    fields: dict[str, object] = {"premise": "a heist in a harbour town"}
    fields.update(changes)
    return StoryBible(**fields)  # type: ignore[arg-type]


def test_a_bible_lists_every_written_form_of_every_character_in_one_case() -> None:
    value = bible(
        characters=(StoryCharacter("Katherine Marsh", ("Kit",)), StoryCharacter("Daniel Okafor"))
    )
    assert value.names() == ("katherine marsh", "kit", "daniel okafor")


def test_a_bible_may_be_full() -> None:
    bible(
        characters=tuple(StoryCharacter(f"Person {n}") for n in range(StoryBible.MAX_CHARACTERS)),
        places=tuple(f"Place {n}" for n in range(StoryBible.MAX_PLACES)),
        timeline=tuple(StoryEvent(n, f"event {n}") for n in range(StoryBible.MAX_EVENTS)),
        span_years=StoryBible.MAX_SPAN,
    )


def test_a_bible_premise_is_one_line_with_a_limit() -> None:
    bible(premise="a" * StoryBible.MAX_PREMISE)
    with pytest.raises(ValueError, match="the premise needs text"):
        bible(premise=" ")
    with pytest.raises(ValueError, match="longer than 2000"):
        bible(premise="a" * (StoryBible.MAX_PREMISE + 1))


def test_a_bible_has_at_most_sixty_characters_in_a_tuple() -> None:
    with pytest.raises(ValueError, match="at most 60 characters"):
        bible(
            characters=tuple(
                StoryCharacter(f"Person {n}") for n in range(StoryBible.MAX_CHARACTERS + 1)
            )
        )
    with pytest.raises(ValueError, match="at most 60 characters"):
        bible(characters=[StoryCharacter("Ana")])


def test_a_bibles_characters_are_story_characters() -> None:
    with pytest.raises(TypeError, match="story characters"):
        bible(characters=("Ana",))


@pytest.mark.parametrize(
    "characters",
    [
        (StoryCharacter("Ana"), StoryCharacter("ANA")),
        (StoryCharacter("Ana", ("Nan",)), StoryCharacter("Nan")),
        (StoryCharacter("Ana", ("Nan",)), StoryCharacter("Bo", ("nan",))),
    ],
)
def test_two_characters_may_not_share_a_name_or_an_alias_whatever_the_case(
    characters: tuple[StoryCharacter, ...],
) -> None:
    with pytest.raises(ValueError, match="character names must be distinct"):
        bible(characters=characters)


def test_two_characters_may_share_a_word() -> None:
    bible(characters=(StoryCharacter("Ana Marsh"), StoryCharacter("Bo Marsh")))


def test_a_bible_has_at_most_sixty_places_in_a_tuple() -> None:
    with pytest.raises(ValueError, match="at most 60 places"):
        bible(places=tuple(f"Place {n}" for n in range(StoryBible.MAX_PLACES + 1)))
    with pytest.raises(ValueError, match="at most 60 places"):
        bible(places=["Harborough"])


def test_a_place_is_one_line_with_a_limit() -> None:
    bible(places=("a" * StoryBible.MAX_PLACE,))
    with pytest.raises(ValueError, match="a place needs text"):
        bible(places=("",))
    with pytest.raises(ValueError, match="longer than 80"):
        bible(places=("a" * (StoryBible.MAX_PLACE + 1),))


def test_places_are_distinct_whatever_the_case() -> None:
    with pytest.raises(ValueError, match="places must be distinct"):
        bible(places=("Harborough", "HARBOROUGH"))


def test_a_place_may_not_be_a_characters_name() -> None:
    with pytest.raises(ValueError, match="cannot share a name with a character"):
        bible(characters=(StoryCharacter("Marsh"),), places=("marsh",))
    with pytest.raises(ValueError, match="cannot share a name with a character"):
        bible(characters=(StoryCharacter("Ana", ("Harborough",)),), places=("Harborough",))


def test_a_place_may_share_a_word_with_a_character() -> None:
    bible(characters=(StoryCharacter("Elena Marsh"),), places=("Marsh",))


def test_a_bible_has_at_most_a_hundred_events_in_a_tuple() -> None:
    with pytest.raises(ValueError, match="at most 100 events"):
        bible(timeline=tuple(StoryEvent(n, f"event {n}") for n in range(StoryBible.MAX_EVENTS + 1)))
    with pytest.raises(ValueError, match="at most 100 events"):
        bible(timeline=[StoryEvent(1, "the fire")])


def test_a_bibles_timeline_is_story_events() -> None:
    with pytest.raises(TypeError, match="story events"):
        bible(timeline=("the fire",))


def test_event_labels_are_distinct_whatever_the_case() -> None:
    with pytest.raises(ValueError, match="event labels must be distinct"):
        bible(timeline=(StoryEvent(1, "the fire"), StoryEvent(2, "The Fire")))


def test_the_timeline_is_listed_in_the_order_things_happen() -> None:
    with pytest.raises(ValueError, match="in the order things happen"):
        bible(timeline=(StoryEvent(5, "the trial"), StoryEvent(1, "the fire")))


def test_two_events_may_happen_together() -> None:
    bible(timeline=(StoryEvent(1, "the fire"), StoryEvent(1, "the flood")))


@pytest.mark.parametrize("span", [-1, 201, True, 1.5])
def test_the_span_is_a_whole_number_of_years_in_range(span: object) -> None:
    with pytest.raises(ValueError, match="whole number of years from 0 to 200"):
        bible(span_years=span)
