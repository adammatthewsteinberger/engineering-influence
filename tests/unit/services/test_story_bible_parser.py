"""The story bible parser: one JSON object read strictly, with everything a model wrote treated as untrusted text."""

import json
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.interfaces.story_bible_parser_interface import (
    StoryBibleParserInterface,
)
from engineering_influence.services.story_bible_parser import StoryBibleParser

PARSER = StoryBibleParser()
BIBLE: dict[str, Any] = {
    "premise": "A night nurse's estranged brother returns.",
    "characters": [
        {"name": "Mara Vance", "aliases": ["Mar"], "age": 34},
        {"name": "Daniel Vance", "aliases": [], "age": None},
    ],
    "places": ["Saint Brannock Hospital", "Harborough"],
    "timeline": [{"when": 1, "label": "the car park"}, {"when": 9, "label": "the funeral"}],
    "span_years": 1,
}


def parse(value: Any = None, **changes: Any) -> Any:
    data = {**BIBLE, **changes} if value is None else value
    return PARSER.parse(json.dumps(data))


def refusal(text: str) -> str:
    with pytest.raises(ApplicationError) as caught:
        PARSER.parse(text)
    assert (caught.value.code, caught.value.http_status) == ("STORY_BIBLE_INVALID", 422)
    assert caught.value.message.startswith("the story bible cannot be read: ")
    return caught.value.message.removeprefix("the story bible cannot be read: ")


def why(**changes: Any) -> str:
    return refusal(json.dumps({**BIBLE, **changes}))


def test_it_is_a_story_bible_parser() -> None:
    assert isinstance(PARSER, StoryBibleParserInterface)


def test_a_complete_bible_is_read_into_the_model() -> None:
    bible = parse()
    assert bible.premise == "A night nurse's estranged brother returns."
    assert [(c.name, c.aliases, c.age) for c in bible.characters] == [
        ("Mara Vance", ("Mar",), 34),
        ("Daniel Vance", (), None),
    ]
    assert bible.places == ("Saint Brannock Hospital", "Harborough")
    assert [(e.when, e.label) for e in bible.timeline] == [(1, "the car park"), (9, "the funeral")]
    assert bible.span_years == 1


def test_only_the_premise_is_needed() -> None:
    bible = parse({"premise": "A heist."})
    assert (bible.characters, bible.places, bible.timeline, bible.span_years) == ((), (), (), 0)


def test_a_preamble_a_fence_and_a_postscript_do_no_harm() -> None:
    text = (
        "Here is the bible:\n```json\n" + json.dumps(BIBLE) + "\n```\nHope that helps. {not read}"
    )
    assert PARSER.parse(text).premise == BIBLE["premise"]


def test_only_the_first_object_is_read() -> None:
    other = {**BIBLE, "premise": "A second bible."}
    assert PARSER.parse(json.dumps(BIBLE) + json.dumps(other)).premise == BIBLE["premise"]


def test_a_key_that_is_not_known_is_ignored() -> None:
    bible = parse({**BIBLE, "mood": "grim", "characters": [{"name": "Ana", "nickname": "A"}]})
    assert bible.characters[0].name == "Ana"


def test_no_json_object_is_refused() -> None:
    assert refusal("I could not write one.") == "there is no JSON object in the answer"


def test_json_that_does_not_parse_is_refused_with_where() -> None:
    message = refusal('{"premise": "x",}')
    assert message.startswith("the JSON is not valid (")
    assert "at position" in message


def test_a_premise_is_needed_and_is_text() -> None:
    assert refusal('{"characters": []}') == "the premise is not text"
    assert refusal('{"premise": 4}') == "the premise is not text"
    assert refusal('{"premise": null}') == "the premise is not text"
    assert "the premise needs text" in refusal('{"premise": "   "}')


def test_a_text_is_collapsed_to_one_line_and_cleaned() -> None:
    text = "  A \n heist\t in a   harbour" + chr(0x200B) + chr(0x7) + chr(0x202E) + "  town  "
    assert parse({"premise": text}).premise == "A heist in a harbour town"


def test_a_line_separator_and_a_private_use_character_are_dropped_or_spaced() -> None:
    assert parse({"premise": "a b" + chr(0xE000) + "c"}).premise == "a bc"


@pytest.mark.parametrize("key", ["characters", "places", "timeline"])
def test_each_list_must_be_a_list(key: str) -> None:
    assert why(**{key: "x"}) == f"{key} is not a list"
    assert why(**{key: {"a": 1}}) == f"{key} is not a list"


def test_a_character_is_an_object_with_a_text_name() -> None:
    assert why(characters=["Ana"]) == "character 1 is not an object"
    assert why(characters=[{"name": "Ana"}, 5]) == "character 2 is not an object"
    assert why(characters=[{"name": 5}]) == "character 1's name is not text"
    assert why(characters=[{}]) == "character 1's name is not text"


def test_aliases_are_a_list_of_text() -> None:
    assert (
        why(characters=[{"name": "Ana", "aliases": "A"}]) == "character 1's aliases are not a list"
    )
    assert why(characters=[{"name": "Ana", "aliases": [3]}]) == "character 1's alias is not text"
    assert parse(characters=[{"name": "Ana"}]).characters[0].aliases == ()


@pytest.mark.parametrize("age", ["34", 34.5, True, [], {}])
def test_an_age_is_a_whole_number_or_null(age: Any) -> None:
    assert (
        why(characters=[{"name": "Ana", "age": age}]) == "character 1's age is not a whole number"
    )


def test_an_age_may_be_missing_null_or_zero() -> None:
    assert parse(characters=[{"name": "Ana"}]).characters[0].age is None
    assert parse(characters=[{"name": "Ana", "age": None}]).characters[0].age is None
    assert parse(characters=[{"name": "Ana", "age": 0}]).characters[0].age == 0


def test_a_place_is_text() -> None:
    assert why(places=["Harborough", 3]) == "place 2 is not text"


def test_the_timeline_is_put_in_the_order_things_happen() -> None:
    bible = parse(timeline=[{"when": 9, "label": "the funeral"}, {"when": 1, "label": "the fire"}])
    assert [e.label for e in bible.timeline] == ["the fire", "the funeral"]


def test_two_events_at_one_time_keep_the_order_they_were_written() -> None:
    bible = parse(
        timeline=[{"when": 2, "label": "b"}, {"when": 2, "label": "a"}, {"when": 1, "label": "c"}]
    )
    assert [e.label for e in bible.timeline] == ["c", "b", "a"]


def test_an_event_is_an_object_with_a_whole_time_and_a_text_label() -> None:
    assert why(timeline=["x"]) == "event 1 is not an object"
    assert why(timeline=[{"label": "a"}]) == "event 1's time is not a whole number"
    assert why(timeline=[{"when": 1.5, "label": "a"}]) == "event 1's time is not a whole number"
    assert why(timeline=[{"when": True, "label": "a"}]) == "event 1's time is not a whole number"
    assert why(timeline=[{"when": 1}]) == "event 1's label is not text"
    assert why(timeline=[{"when": 1, "label": 7}]) == "event 1's label is not text"


@pytest.mark.parametrize("span", ["2", 1.5, True, None])
def test_the_span_is_a_whole_number(span: Any) -> None:
    assert why(span_years=span) == "span_years is not a whole number"


def test_a_bible_that_breaks_its_own_rules_is_refused_and_says_which() -> None:
    assert "character names must be distinct" in why(characters=[{"name": "Ana"}, {"name": "ana"}])
    assert "a place cannot share a name with a character" in why(
        characters=[{"name": "Harborough"}], places=["Harborough"]
    )
    assert "at most 60 characters" in why(characters=[{"name": f"P{n}"} for n in range(61)])
    assert "event labels must be distinct" in why(
        timeline=[{"when": 1, "label": "x"}, {"when": 2, "label": "X"}]
    )
    assert "a character's name needs text" in why(characters=[{"name": " "}])


def test_an_unassigned_code_point_is_dropped() -> None:
    assert parse({"premise": "a" + chr(0x378) + "b"}).premise == "ab"


def test_a_control_character_that_counts_as_a_space_separates_words() -> None:
    assert parse({"premise": "a" + chr(0x1F) + "b" + chr(0x85) + "c"}).premise == "a b c"


def test_the_position_of_a_json_error_is_where_it_is_in_the_whole_answer() -> None:
    text = 'Here it is: {"premise" "x"}'
    assert refusal(text).endswith(f"at position {text.index(' "x"') + 1})")
