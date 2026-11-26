# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The title page is read whatever key comes first, and a first paragraph without a Title key is not a title page."""

from engineering_influence.services.fountain_parser import FountainParser

PARSER = FountainParser()


def test_a_title_page_with_a_credit_before_the_title_is_read() -> None:
    text = "Credit: Written by\nTitle: FILM\n\nINT. ROOM - DAY\n\nOne.\n"
    assert PARSER.title_page(text) == (("Credit", "Written by"), ("Title", "FILM"))


def test_the_script_after_a_credit_first_title_page_is_not_read_as_title_page() -> None:
    text = "Credit: Written by\nTitle: FILM\n\nINT. ROOM - DAY\n\nOne.\n"
    assert [block.kind for block in PARSER.blocks(text)] == ["heading", "action"]
    front, chunks = PARSER.scene_chunks(text)
    assert front == "Credit: Written by\nTitle: FILM\n\n"
    assert chunks == ("INT. ROOM - DAY\n\nOne.",)


def test_a_first_paragraph_without_a_title_key_is_not_a_title_page() -> None:
    text = "Credit: Written by\n\nINT. ROOM - DAY\n\nOne.\n"
    assert PARSER.title_page(text) == ()
    assert next(block.kind for block in PARSER.blocks(text)) == "action"
