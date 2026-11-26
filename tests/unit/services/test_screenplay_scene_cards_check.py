# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplaySceneCardsCheck: numbered cards with their fields, a link to the next card, beats in order, and All Is
Lost about three-quarters through."""

from engineering_influence.services.screenplay_scene_cards_check import ScreenplaySceneCardsCheck

BEATS = [
    "Opening Image",
    "Theme Stated",
    "Set-Up",
    "Catalyst",
    "Debate",
    "Break into Two",
    "All Is Lost",
    "Dark Night of the Soul",
    "Break into Three",
    "Finale",
]


def card(
    number: int, beat: str, link: bool = True, storyline: str = "A", changes: bool = True
) -> str:
    lines = [f"## S{number:02d} · a scene"]
    if changes:
        lines.append("**What changes:** the crew learns something.")
    if link:
        lines.append("**Therefore:** the next scene follows.")
    lines.append(f"**Beat:** {beat}")
    lines.append(f"**Storyline:** {storyline}")
    return "\n".join(lines) + "\n\n"


def cards(beats: list[str] = BEATS, **overrides: object) -> str:
    text = ""
    for number, beat in enumerate(beats, 1):
        text += card(number, beat, **overrides) if number == 1 else card(number, beat)
    return text


def check(text: str) -> tuple[str, ...]:
    return ScreenplaySceneCardsCheck().problems(text)


def test_complete_cards_have_no_problems() -> None:
    assert check(cards()) == ()


def test_no_cards_is_a_problem() -> None:
    assert "at least one" in check("# Cards\n")[0]


def test_a_skipped_number_is_a_problem() -> None:
    text = card(1, "Opening Image") + card(3, "Theme Stated")
    assert any("should be S02" in p for p in check(text))


def test_a_missing_field_is_a_problem() -> None:
    text = card(1, "Opening Image", changes=False) + card(2, "Theme Stated")
    assert any("no '**What changes:**' field" in p for p in check(text))


def test_a_card_without_a_link_is_a_problem_unless_it_is_last() -> None:
    text = card(1, "Opening Image", link=False) + card(2, "Theme Stated")
    assert any("no **Therefore:** or **But:** link" in p for p in check(text))
    assert check(card(1, "Opening Image") + card(2, "Theme Stated", link=False)) == ()


def test_a_storyline_outside_the_set_is_a_problem() -> None:
    assert any("storyline 'Z'" in p for p in check(card(1, "Opening Image", storyline="Z")))


def test_an_unknown_beat_is_a_problem() -> None:
    assert any(
        "'Vibes' is not one of the fifteen beats" in p for p in check(cards(["Vibes", *BEATS[1:]]))
    )


def test_beats_out_of_order_are_a_problem() -> None:
    swapped = BEATS[:3] + [BEATS[4], BEATS[3]] + BEATS[5:]
    assert any("out of order" in p for p in check(cards(swapped)))


def test_all_is_lost_not_near_three_quarters_is_a_problem() -> None:
    late = [
        *BEATS[:6],
        "Break into Two",
        "Break into Two",
        "Break into Two",
        "All Is Lost",
        "Dark Night of the Soul",
    ]
    assert any("three-quarters" in p for p in check(cards(late)))


def test_a_card_without_a_beat_is_reported_and_left_out_of_the_order() -> None:
    no_beat = "\n".join(
        line for line in card(2, "Theme Stated").splitlines() if "**Beat:**" not in line
    )
    problems = check(card(1, "Opening Image") + no_beat + "\n\n" + card(3, "Set-Up"))
    assert any("no '**Beat:**' field" in p for p in problems)
    assert not any("out of order" in p for p in problems)
