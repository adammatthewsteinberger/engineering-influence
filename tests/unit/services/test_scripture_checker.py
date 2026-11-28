# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScriptureChecker: a quotation is right, close, wrong or uncheckable, against the verses it cites, and never blocks."""

from engineering_influence.infrastructure.bundled_scripture import BundledScripture
from engineering_influence.interfaces.scripture_index_interface import ScriptureIndexInterface
from engineering_influence.models.verse_ref import VerseRef
from engineering_influence.services.reference_parser import ReferenceParser
from engineering_influence.services.scripture_checker import ScriptureChecker
from engineering_influence.services.scripture_draft_checks import ScriptureDraftChecks

JOHN = "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."
CHECKER = ScriptureChecker(BundledScripture(), ReferenceParser())


class Nowhere(ScriptureIndexInterface):
    """A scripture with no translation that holds the verses."""

    def translations(self) -> tuple[str, ...]:
        return ("kjv",)

    def text(self, translation: str, refs: tuple[VerseRef, ...]) -> str | None:
        return None


def codes(text: str, chapter: int = 1) -> list[str]:
    return [issue.code for issue in CHECKER.check(chapter, text)]


def test_a_word_for_word_quotation_with_its_citation_is_right() -> None:
    assert codes(f"He wrote “{JOHN}” (John 3:16).") == []


def test_the_comparison_ignores_case_punctuation_and_quotation_marks() -> None:
    assert (
        codes(
            'He wrote, "for god so loved the world; that he gave his ONLY begotten son!" (John 3:16).'
        )
        == []
    )


def test_a_quotation_close_to_a_translation_is_reported_as_near() -> None:
    near = JOHN.replace("everlasting", "eternal")
    (issue,) = CHECKER.check(2, f"He wrote “{near}” (John 3:16).")
    assert issue.code == "SCRIPTURE_NEAR" and not issue.blocking
    assert issue.stage == "draft" and issue.detail.startswith(
        "chapter 2: the quotation cited as JHN 3:16"
    )


def test_a_paraphrase_presented_as_a_quotation_is_misquoted() -> None:
    assert codes("He wrote “God loved the world so much that he sent his Son” (John 3:16).") == [
        "SCRIPTURE_MISQUOTED"
    ]


def test_a_range_is_labelled_by_its_first_and_last_verse() -> None:
    quoted = (
        "Love is patient, love is kind, and it does not envy, it does not boast, it is not proud."
    )
    (issue,) = CHECKER.check(1, f"He wrote “{quoted}” (1 Corinthians 13:4-7).")
    assert issue.code == "SCRIPTURE_NEAR"
    assert issue.detail.startswith("chapter 1: the quotation cited as 1CO 13:4-7 is close to the ")


def test_a_quotation_with_no_citation_nearby_is_not_checked() -> None:
    assert (
        codes(
            f"He wrote “{JOHN}”, and then, much later and far away from any book, said nothing more."
        )
        == []
    )


def test_a_citation_that_comes_long_after_the_quotation_is_not_its_citation() -> None:
    far = "x" * 60
    assert codes(f"He wrote “{JOHN}” {far} (John 3:16).") == []


def test_a_short_quotation_is_not_checked() -> None:
    assert codes("He wrote “Be still now” (Psalm 46:10).") == []


def test_quotation_marks_with_no_words_in_them_are_misquoted_rather_than_passing() -> None:
    assert codes("He wrote “—— —— —— ——————” (John 3:16).") == ["SCRIPTURE_MISQUOTED"]


def test_verses_no_translation_holds_are_reported_as_unchecked() -> None:
    checker = ScriptureChecker(Nowhere(), ReferenceParser())
    (issue,) = checker.check(1, f"He wrote “{JOHN}” (John 3:16).")
    assert issue.code == "SCRIPTURE_UNCHECKED" and "could not be checked" in issue.detail


def test_the_draft_checks_number_the_chapters_from_one() -> None:
    checks = ScriptureDraftChecks(CHECKER)
    issues = checks.issues(
        {}, ("No quotes here.", f"He wrote “{JOHN.replace('everlasting', 'eternal')}” (John 3:16).")
    )
    assert [issue.detail.split(":")[0] for issue in issues] == ["chapter 2"]
    assert checks.issues({}, ("Nothing at all.",)) == ()
