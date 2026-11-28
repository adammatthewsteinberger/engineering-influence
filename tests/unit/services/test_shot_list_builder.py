# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ShotListBuilder: each scene becomes shots routed by ADR 0015, split into lengths its model can make."""

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.shot_list_builder import ShotListBuilder

WAN = "alibaba/wan-3.0"
H3 = "minimax/hailuo-3"
GEMINI = "google/gemini-omni-1.2-flash"

HERO = "INT. ROOM - DAY [[hero]]\n\n" + "word " * 100 + "\n"
SHORT = "INT. HALL - DAY\n\nA door shuts.\n"
TALK = "INT. KITCHEN - NIGHT\n\nANNA\nHi.\n\nBEN\nHey.\n\nANNA\nYes.\n"
LONG = "EXT. FIELD - DAY\n\n" + "grass " * 60 + "\n"


def builder() -> ShotListBuilder:
    return ShotListBuilder(FountainParser())


def test_a_hero_scene_goes_to_wan_in_shots_of_up_to_thirty_seconds() -> None:
    shots = builder().build(HERO)
    assert {shot.model() for shot in shots} == {WAN}
    assert [shot.seconds() for shot in shots] == [20, 20]


def test_a_scene_with_several_speeches_goes_to_gemini_in_shots_of_up_to_fifteen() -> None:
    shots = builder().build(TALK)
    assert [shot.model() for shot in shots] == [GEMINI]
    assert shots[0].seconds() == ShotListBuilder.MIN_SCENE_SECONDS


def test_a_long_scene_without_a_hero_or_speeches_goes_to_wan() -> None:
    shots = builder().build(LONG)
    assert [(shot.model(), shot.seconds()) for shot in shots] == [(WAN, 24)]


def test_a_short_scene_goes_to_hailuo_h3() -> None:
    shots = builder().build(SHORT)
    assert [(shot.model(), shot.seconds()) for shot in shots] == [(H3, 4)]


def test_shots_are_numbered_in_order_and_carry_their_scene() -> None:
    shots = builder().build(f"{HERO}\n\n{SHORT}\n\n{TALK}\n\n{LONG}")
    assert [shot.number for shot in shots] == [1, 2, 3, 4, 5]
    assert [shot.scene for shot in shots] == [1, 1, 2, 3, 4]


def test_a_scene_longer_than_one_shot_is_split_evenly_with_the_remainder_first() -> None:
    script = "INT. ROOM - DAY [[hero]]\n\n" + "word " * 153 + "\n"
    shots = builder().build(script)
    assert [shot.seconds() for shot in shots] == [21, 20, 20]


def test_the_prompt_is_the_scene_text_cut_to_the_prompt_limit() -> None:
    script = "INT. ROOM - DAY\n\n" + "lorem " * 500 + "\n"
    shots = builder().build(script)
    assert len(shots[0].prompt) == ShotListBuilder.PROMPT_CHARACTERS


def test_a_script_with_no_scenes_has_no_shots() -> None:
    assert builder().build("") == ()
