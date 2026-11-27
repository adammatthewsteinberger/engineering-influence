# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayToneRatioCheck: warm scenes must outnumber conflict scenes five to one, when the cards carry tones."""

from engineering_influence.services.screenplay_tone_ratio_check import ScreenplayToneRatioCheck

RATIO_MESSAGE = "the cards hold {warm} warm scenes to {conflict} conflict scenes; warm must be at least 5 times conflict"


def card(number: int, tone: str | None = None) -> str:
    text = (
        f"## S{number:02d} · a scene\n**What changes:** it changes.\n**Therefore:** next.\n"
        f"**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n"
    )
    return text + (f"**Tone:** {tone}\n" if tone is not None else "") + "\n"


def cards(*tones: str | None) -> str:
    return "".join(card(number, tone) for number, tone in enumerate(tones, 1))


def check(text: str) -> tuple[str, ...]:
    return ScreenplayToneRatioCheck().problems(text)


def test_cards_with_no_tone_are_not_checked() -> None:
    assert check(cards(None, None)) == ()


def test_five_warm_scenes_for_each_conflict_scene_pass() -> None:
    assert check(cards(*["warm"] * 5, "conflict")) == ()


def test_fewer_than_five_warm_scenes_for_a_conflict_scene_is_a_problem() -> None:
    assert check(cards(*["warm"] * 4, "conflict")) == (RATIO_MESSAGE.format(warm=4, conflict=1),)


def test_a_screenplay_with_warm_scenes_and_no_conflict_passes() -> None:
    assert check(cards("warm", "warm")) == ()


def test_neutral_and_untagged_cards_do_not_count() -> None:
    assert check(cards(*["warm"] * 5, "conflict", "neutral", None)) == ()


def test_an_unknown_tone_is_named_and_not_counted() -> None:
    assert check(cards("angry", *["warm"] * 5)) == (
        "card S01: tone 'angry' is not warm, conflict or neutral",
    )


def test_an_empty_tone_is_named() -> None:
    assert check(cards("")) == ("card S01: tone '' is not warm, conflict or neutral",)
