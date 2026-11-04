"""Table-of-contents verification against printed folios."""

from engineering_influence.publishing.contents_check import ContentsCheck

TITLE = "The Book"
FRONT = "Contents\nIntroduction 1\nA Long Chapter\nName Continues 5\nContents ix\nThe Book vi\niv\n"


def test_reads_wrapped_entries_and_skips_running_heads() -> None:
    texts = [FRONT, "1\nIntroduction\nbody text", "5\nA Long Chapter Name Continues\nbody"]
    problems, checked = ContentsCheck().run(texts, [None, "1", "5"], TITLE)
    assert (problems, checked) == ([], 2)


def test_missing_contents_page() -> None:
    assert ContentsCheck().run(["Nothing"], [None], TITLE) == (["no Contents page found"], None)


def test_contents_without_entries() -> None:
    problems, checked = ContentsCheck().run(["Contents"], [None], TITLE)
    assert problems == ["could not read any table-of-contents entries"]
    assert checked == 0


def test_continuation_page_is_read_until_entries_stop() -> None:
    texts = [
        "Contents\nIntroduction 1",
        "vi\nChapter Two 2",
        "Body\nplain words",
        "1\nIntroduction\nx",
        "2\nChapter Two\ny",
    ]
    problems, checked = ContentsCheck().run(texts, [None, "vi", None, "1", "2"], TITLE)
    assert (problems, checked) == ([], 2)


def test_numbered_page_ends_contents() -> None:
    texts = ["Contents\nIntroduction 1", "Heading\nOther 9", "1\nIntroduction"]
    problems, checked = ContentsCheck().run(texts, [None, "3", "1"], TITLE)
    assert (problems, checked) == ([], 1)


def test_entry_pointing_nowhere_and_wrong_page_are_reported() -> None:
    texts = ["Contents\nGhost 40\nElsewhere 1", "1\nSomething else"]
    problems, _ = ContentsCheck().run(texts, [None, "1"], TITLE)
    assert "ToC entry 'Ghost' points at page 40, which does not exist" in problems
    assert any("ToC entry 'Elsewhere' says page 1" in item for item in problems)


def test_part_page_without_folio_is_inferred_from_next_numbered_page() -> None:
    texts = ["Contents\nPart One 2", "1\nx", "Part One", "3\ny"]
    problems, _ = ContentsCheck().run(texts, [None, "1", None, "3"], TITLE)
    assert problems == []


def test_inference_gives_up_when_candidate_is_invalid_or_numbered() -> None:
    contents = ContentsCheck()
    assert contents._physical(["3", "4"], "2") is None  # candidate before the first page
    assert contents._physical(["1", "2", "5"], "4") is None  # candidate page has a folio
    assert contents._physical(["i", "ii", None, "5"], "9") is None  # no larger folio
    assert contents._physical(["1"], "9") is None
    assert contents._physical(["i"], "xi") is None  # roman labels are never inferred
