# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayBeatSheetCheck: fifteen beats in order, page ranges that move forward, a fixed function set, and All Is Lost
about three-quarters through."""

from engineering_influence.services.screenplay_beat_sheet_check import ScreenplayBeatSheetCheck

TARGET = 180
RANGES = [
    ("Opening Image", "1 to 1"),
    ("Theme Stated", "5 to 5"),
    ("Set-Up", "6 to 10"),
    ("Catalyst", "12 to 12"),
    ("Debate", "12 to 25"),
    ("Break into Two", "25 to 25"),
    ("B Story", "30 to 30"),
    ("Fun and Games", "30 to 55"),
    ("Midpoint", "55 to 55"),
    ("Bad Guys Close In", "55 to 75"),
    ("All Is Lost", "135 to 145"),
    ("Dark Night of the Soul", "146 to 155"),
    ("Break into Three", "156 to 165"),
    ("Finale", "166 to 175"),
    ("Closing Image", "180 to 180"),
]


def sheet(ranges: list[tuple[str, str]] = RANGES, function: str = "none") -> str:
    rows = [
        "| Beat | Pages | Scenes | Scene | Central character | Function |",
        "|---|---|---|---|---|---|",
    ]
    for name, pages in ranges:
        fn = "rupture" if name == "All Is Lost" else function
        rows.append(f"| {name} | {pages} | S1 | a scene | Adam | {fn} |")
    return "\n".join(rows) + "\n"


def check(text: str) -> tuple[str, ...]:
    return ScreenplayBeatSheetCheck(TARGET).problems(text)


def test_a_complete_beat_sheet_has_no_problems() -> None:
    assert check(sheet()) == ()


def test_a_missing_beat_is_a_problem() -> None:
    assert "fifteen beats in order" in check(sheet(RANGES[:-1]))[0]


def test_beats_out_of_order_are_a_problem() -> None:
    swapped = RANGES[:2] + [RANGES[3], RANGES[2]] + RANGES[4:]
    assert "fifteen beats in order" in check(sheet(swapped))[0]


def test_a_range_that_runs_backwards_is_a_problem() -> None:
    ranges = [*RANGES[:3], ("Catalyst", "12 to 9"), *RANGES[4:]]
    assert any("not a range" in p for p in check(sheet(ranges)))


def test_a_range_starting_before_the_beat_above_is_a_problem() -> None:
    ranges = [*RANGES[:4], ("Debate", "3 to 25"), *RANGES[5:]]
    assert any("before the beat above" in p for p in check(sheet(ranges)))


def test_a_range_past_the_last_page_is_a_problem() -> None:
    ranges = [*RANGES[:-1], ("Closing Image", "180 to 200")]
    assert any("past the film" in p for p in check(sheet(ranges)))


def test_a_function_outside_the_fixed_set_is_a_problem() -> None:
    assert any("not one of the fixed set" in p for p in check(sheet(function="vibes")))


def test_all_is_lost_outside_seventy_to_eighty_per_cent_is_a_problem() -> None:
    ranges = [*RANGES[:10], ("All Is Lost", "90 to 100"), *RANGES[11:]]
    assert any("three-quarters" in p for p in check(sheet(ranges)))


def test_a_target_must_have_pages() -> None:
    try:
        ScreenplayBeatSheetCheck(0)
    except ValueError as error:
        assert "positive number of pages" in str(error)
    else:
        raise AssertionError("expected a ValueError")


def test_a_range_without_to_is_a_problem() -> None:
    ranges = [*RANGES[:3], ("Catalyst", "12-14"), *RANGES[4:]]
    assert any("not a range" in p for p in check(sheet(ranges)))


def test_a_range_with_a_word_for_a_page_is_a_problem() -> None:
    ranges = [*RANGES[:3], ("Catalyst", "12 to soon"), *RANGES[4:]]
    assert any("not a range" in p for p in check(sheet(ranges)))


def test_prose_around_the_table_is_not_judged() -> None:
    assert check("# Beat sheet\n\nThe film in fifteen beats.\n\n" + sheet()) == ()
