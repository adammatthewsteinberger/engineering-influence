# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainParser: title page, elements and scenes, with notes and boneyard taken out where Fountain says."""

from engineering_influence.services.fountain_parser import FountainParser


def kinds(text: str) -> list[str]:
    return [block.kind for block in FountainParser().blocks(text)]


def test_the_title_page_keeps_its_pairs_and_continuation_lines() -> None:
    script = "Title: LIVING WATERS\n  MURKY WATER\nAuthor: Adam\n\nFADE IN:"
    assert FountainParser().title_page(script) == (
        ("Title", "LIVING WATERS\nMURKY WATER"),
        ("Author", "Adam"),
    )


def test_a_script_without_a_title_page_has_no_pairs() -> None:
    assert FountainParser().title_page("FADE IN:") == ()


def test_the_title_page_is_not_an_element() -> None:
    assert kinds("Title: X\n\nFADE IN:") == ["transition"]


def test_a_standard_script_splits_into_its_elements() -> None:
    script = "FADE IN:\n\nINT. ROOM - DAY\n\nAction line.\n\nMARA\n(quietly)\nHi there.\n\nCUT TO:"
    assert kinds(script) == [
        "transition",
        "heading",
        "action",
        "cue",
        "parenthetical",
        "dialogue",
        "transition",
    ]


def test_a_boneyard_comment_is_removed() -> None:
    assert kinds("/* a note to the writer */\n\nAction.") == ["action"]


def test_a_note_is_removed_from_action_but_kept_on_the_heading() -> None:
    blocks = FountainParser().blocks("Mara sits. [[beat: midpoint]]")
    assert blocks[0].text() == "Mara sits."


def test_a_paragraph_that_is_only_a_note_has_no_element() -> None:
    assert kinds("[[beat: midpoint]]") == []


def test_a_cue_is_all_capitals_with_speech_after_it() -> None:
    assert kinds("MARA\nLine one.\nLine two.") == ["cue", "dialogue"]
    assert FountainParser().blocks("MARA\nLine one.\nLine two.")[1].lines == (
        "Line one.",
        "Line two.",
    )


def test_an_at_sign_forces_a_cue() -> None:
    assert kinds("@mara\nHi.") == ["cue", "dialogue"]


def test_a_single_capitalised_line_is_action() -> None:
    assert kinds("THE HAB IS SILENT.") == ["action"]


def test_centred_and_forced_transitions_are_read() -> None:
    blocks = FountainParser().blocks(">THE END<\n\n>CUT TO BLACK")
    assert [(b.kind, b.text()) for b in blocks] == [
        ("centered", "THE END"),
        ("transition", "CUT TO BLACK"),
    ]


def test_a_heading_with_a_leading_dot_is_a_heading() -> None:
    assert kinds(".OPENING TITLES") == ["heading"]


def test_scenes_are_numbered_and_carry_their_notes() -> None:
    script = (
        "Preface action before any scene.\n\n"
        "INT. HAB-1, BUNK ROOM - NIGHT [[set: hab1-bunk-room]] [[sol: 4]]\n\nMara sits.\n\n"
        "EXT. ARCADIA PLANITIA - DAY [[ev-first-log]]\n\nThe dust settles."
    )
    scenes = FountainParser().scenes(script)
    assert [s.number for s in scenes] == [1, 2]
    assert scenes[0].heading == "INT. HAB-1, BUNK ROOM - NIGHT"
    assert scenes[0].note("set") == "hab1-bunk-room"
    assert scenes[0].note("sol") == "4"
    assert scenes[1].note("ref") == "ev-first-log"
    assert [b.kind for b in scenes[1].blocks] == ["action"]


def test_no_scenes_when_there_is_no_heading() -> None:
    assert FountainParser().scenes("Just action, no heading.") == ()


def test_a_title_line_without_a_colon_is_skipped() -> None:
    assert FountainParser().title_page("Title: X\nnot a pair\n\nFADE IN:") == (("Title", "X"),)


def test_an_empty_script_has_no_elements() -> None:
    assert FountainParser().blocks("") == ()
