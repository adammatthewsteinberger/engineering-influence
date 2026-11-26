# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainParser.scene_chunks: the title page and the text before the first scene, then each scene's own text, in order."""

from engineering_influence.services.fountain_parser import FountainParser


def test_the_title_page_and_the_text_before_the_first_scene_come_first() -> None:
    front, _ = FountainParser().scene_chunks("Title: FILM\n\nFADE IN:\n\nINT. A - DAY\n\nOne.\n")
    assert front == "Title: FILM\n\nFADE IN:\n"


def test_each_scene_is_its_heading_and_the_lines_up_to_the_next_heading() -> None:
    text = (
        "Title: FILM\n\nINT. A - DAY\n\nOne.\n\n/* gone */\nEXT. B - NIGHT [[set: yard]]\n\nTwo.\n"
    )
    _, chunks = FountainParser().scene_chunks(text)
    assert chunks == ("INT. A - DAY\n\nOne.\n\n", "EXT. B - NIGHT [[set: yard]]\n\nTwo.")


def test_a_script_without_a_title_page_has_no_front() -> None:
    front, chunks = FountainParser().scene_chunks("INT. A - DAY\n\nOne.\n")
    assert front == ""
    assert chunks == ("INT. A - DAY\n\nOne.",)
