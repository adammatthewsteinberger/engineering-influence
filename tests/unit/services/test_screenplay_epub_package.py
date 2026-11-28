# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayEpubPackage: the EPUB members, the mimetype first and stored, the page's element classes, and every value escaped."""

from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_epub_package import ScreenplayEpubPackage

SCRIPT = "Title: TEST FILM\nCredit: Written by\n\nFADE IN:\n\nINT. HIVE - DAY\n\nJOHN\n(quietly)\nIs she gone?\n\nFADE OUT.\n"


def members(script: str = SCRIPT) -> dict[str, bytes]:
    return {name: data for name, data, _ in ScreenplayEpubPackage(FountainParser()).entries(script)}


def test_the_mimetype_is_the_first_member_and_is_stored() -> None:
    first = ScreenplayEpubPackage(FountainParser()).entries(SCRIPT)[0]
    assert first == ("mimetype", b"application/epub+zip", True)


def test_the_container_points_at_the_package() -> None:
    assert b'full-path="OEBPS/content.opf"' in members()["META-INF/container.xml"]


def test_the_package_names_the_title_and_its_identifier() -> None:
    package = members()["OEBPS/content.opf"].decode("utf-8")
    assert "<dc:title>TEST FILM</dc:title>" in package
    assert "urn:engineering-influence:screenplay:test-film" in package
    assert 'properties="nav"' in package


def test_the_page_marks_each_element_with_its_kind() -> None:
    page = members()["OEBPS/screenplay.xhtml"].decode("utf-8")
    assert '<p class="heading">INT. HIVE - DAY</p>' in page
    assert '<p class="cue">JOHN</p>' in page
    assert '<p class="parenthetical">(quietly)</p>' in page
    assert '<p class="dialogue">Is she gone?</p>' in page
    assert '<p class="title">Title: TEST FILM</p>' in page


def test_the_title_page_is_on_the_page_and_the_nav_links_to_it() -> None:
    assert '<a href="screenplay.xhtml">TEST FILM</a>' in members()["OEBPS/nav.xhtml"].decode(
        "utf-8"
    )


def test_values_from_the_script_are_escaped() -> None:
    script = 'Title: Fish & <Chips>\n\nAction with "quotes" & <b>tags</b>.\n'
    page = members(script)["OEBPS/screenplay.xhtml"].decode("utf-8")
    assert "Fish &amp; &lt;Chips&gt;" in page
    assert "&lt;b&gt;tags&lt;/b&gt;" in page
    assert "<b>" not in page


def test_a_script_with_no_title_is_untitled() -> None:
    package = members("FADE IN:\n\nINT. HIVE - DAY\n")["OEBPS/content.opf"].decode("utf-8")
    assert "<dc:title>Untitled screenplay</dc:title>" in package
    assert "urn:engineering-influence:screenplay:untitled" in package


def test_the_same_script_gives_the_same_members() -> None:
    assert ScreenplayEpubPackage(FountainParser()).entries(SCRIPT) == ScreenplayEpubPackage(
        FountainParser()
    ).entries(SCRIPT)


class TitlePageParser(FountainParser):
    """Gives the title page keys in the order the test names, so the lookup sees a non-title key first."""

    def title_page(self, text: str) -> tuple[tuple[str, str], ...]:
        return (("Credit", "Written by"), ("Title", "LATE TITLE"))

    def blocks(self, text: str):  # type: ignore[no-untyped-def]
        return ()


def test_the_title_is_found_after_other_title_page_keys() -> None:
    entries = ScreenplayEpubPackage(TitlePageParser()).entries("anything")
    package = {name: data for name, data, _ in entries}["OEBPS/content.opf"].decode("utf-8")
    assert "<dc:title>LATE TITLE</dc:title>" in package


def test_a_blank_title_value_is_untitled() -> None:
    package = members("Title:   \n\nFADE IN:\n")["OEBPS/content.opf"].decode("utf-8")
    assert "<dc:title>Untitled screenplay</dc:title>" in package
