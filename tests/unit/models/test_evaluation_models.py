"""The evaluation's value objects refuse what would make a comparison meaningless."""

import pytest

from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_score import BookScore
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.evaluation_report import EvaluationReport
from engineering_influence.models.evaluation_verdict import EvaluationVerdict
from engineering_influence.models.made_book import MadeBook
from engineering_influence.models.rubric import Rubric
from engineering_influence.models.rubric_dimension import RubricDimension

ANCHORS = ((1, "bad"), (3, "fine"), (5, "great"))


def dimension(name: str = "voice", kinds: tuple[str, ...] = ("nonfiction", "novel")):  # type: ignore[no-untyped-def]
    return RubricDimension(name, "Is it good?", ANCHORS, kinds)


def book(case: str = "a", finished: bool = True, spent: int = 10, estimated: int | None = 10):  # type: ignore[no-untyped-def]
    return MadeBook(
        case,
        BookKind.NONFICTION,
        "completed" if finished else "failed",
        finished,
        "T",
        ("one two three",) if finished else (),
        spent,
        estimated,
    )


def score(case: str = "a", value: int = 4, judge: int = 3) -> BookScore:
    return BookScore(case, (("voice", value, "because"),), judge)


@pytest.mark.parametrize(
    "build",
    [
        lambda: RubricDimension("Voice", "q", ANCHORS, ("novel",)),
        lambda: RubricDimension("voice", " ", ANCHORS, ("novel",)),
        lambda: RubricDimension("voice", "q", ((1, "a"), (3, "b")), ("novel",)),
        lambda: RubricDimension("voice", "q", ((1, "a"), (3, " "), (5, "c")), ("novel",)),
        lambda: RubricDimension("voice", "q", ((5, "a"), (3, "b"), (1, "c")), ("novel",)),
        lambda: RubricDimension("voice", "q", ANCHORS, ()),
        lambda: RubricDimension("voice", "q", ANCHORS, ("poem",)),
        lambda: RubricDimension("voice", "q", ANCHORS, ("novel", "novel")),
        lambda: Rubric(0, 3.5, 0.2, (dimension(),)),
        lambda: Rubric(True, 3.5, 0.2, (dimension(),)),  # type: ignore[arg-type]
        lambda: Rubric(1, 0.9, 0.2, (dimension(),)),
        lambda: Rubric(1, 5.1, 0.2, (dimension(),)),
        lambda: Rubric(1, 3.5, -0.1, (dimension(),)),
        lambda: Rubric(1, 3.5, 4.0, (dimension(),)),
        lambda: Rubric(1, 3.5, 0.2, ()),
        lambda: Rubric(1, 3.5, 0.2, (dimension(), dimension())),
        lambda: Rubric(1, 3.5, 0.2, (dimension(kinds=("novel",)),)),
        lambda: Rubric(1, 3.5, 0.2, (dimension(kinds=("nonfiction",)),)),
        lambda: EvaluationCase("Bad Name", BookKind.NOVEL, "idea"),
        lambda: EvaluationCase("ok", BookKind.NOVEL, "  "),
        lambda: EvaluationCase("ok", BookKind.NOVEL, "idea", target_words=0),
        lambda: EvaluationCase("ok", BookKind.NOVEL, "idea", target_words=5.5),  # type: ignore[arg-type]
        lambda: BookScore("a", (), 0),
        lambda: BookScore("a", (("voice", 4, "r"), ("voice", 3, "r")), 0),
        lambda: BookScore("a", (("voice", 0, "r"),), 0),
        lambda: BookScore("a", (("voice", 6, "r"),), 0),
        lambda: BookScore("a", (("voice", 4.5, "r"),), 0),  # type: ignore[arg-type]
        lambda: BookScore("a", (("voice", True, "r"),), 0),  # type: ignore[arg-type]
        lambda: BookScore("a", (("voice", 4, " "),), 0),
        lambda: BookScore("a", (("voice", 4, "r"),), -1),
        lambda: BookScore("a", (("voice", 4, "r"),), 1.5),  # type: ignore[arg-type]
        lambda: MadeBook(" ", BookKind.NOVEL, "completed", False, "T", (), 0, None),
        lambda: MadeBook("a", BookKind.NOVEL, " ", False, "T", (), 0, None),
        lambda: MadeBook("a", BookKind.NOVEL, "completed", True, "T", (), 0, None),
        lambda: MadeBook("a", BookKind.NOVEL, "failed", False, "T", (), -1, None),
        lambda: MadeBook("a", BookKind.NOVEL, "failed", False, "T", (), 0, -1),
        lambda: MadeBook("a", BookKind.NOVEL, "failed", False, "T", (), 0.5, None),  # type: ignore[arg-type]
        lambda: EvaluationReport(" ", ((book(), score()),)),
        lambda: EvaluationReport("r", ()),
        lambda: EvaluationReport("r", ((book(), score()), (book(), score()))),
        lambda: EvaluationReport("r", ((book(), None),)),
        lambda: EvaluationReport("r", ((book(finished=False), score()),)),
        lambda: EvaluationReport("r", ((book("a"), score("b")),)),
    ],
)
def test_a_value_that_would_corrupt_a_comparison_is_refused(build) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        build()


def test_a_rubric_selects_and_renders_the_dimensions_of_a_kind() -> None:
    both = dimension("voice")
    only_novel = RubricDimension("plot", "Does it move?", ANCHORS, ("novel",))
    only_fact = RubricDimension("accuracy", "Is it true?", ANCHORS, ("nonfiction",))
    rubric = Rubric(1, 3.5, 0.2, (both, only_novel, only_fact))
    assert [d.name for d in rubric.for_kind("novel")] == ["voice", "plot"]
    assert [d.name for d in rubric.for_kind("nonfiction")] == ["voice", "accuracy"]
    assert rubric.render("novel") == (
        "voice: Is it good?\n  1: bad\n  3: fine\n  5: great\n\n"
        "plot: Does it move?\n  1: bad\n  3: fine\n  5: great"
    )


def test_a_case_makes_the_brief_with_the_budget_it_is_given() -> None:
    case = EvaluationCase("herbs", BookKind.NONFICTION, "Herbs indoors", "Herbs", 10000, "6x9")
    brief = case.brief(2_000_000)
    assert (brief.kind, brief.idea, brief.budget_micro_usd) == (
        BookKind.NONFICTION,
        "Herbs indoors",
        2_000_000,
    )
    assert (brief.title_hint, brief.target_words, brief.trim_size) == ("Herbs", 10000, "6x9")


def test_a_book_reads_as_its_title_then_every_chapter() -> None:
    made = MadeBook("a", BookKind.NOVEL, "completed", True, "The Road", ("One.", "Two."), 1, 1)
    assert made.text() == "# The Road\n\nOne.\n\nTwo."


def test_a_score_by_name() -> None:
    assert BookScore("a", (("voice", 4, "r"), ("plot", 2, "r")), 0).by_name() == {
        "voice": 4,
        "plot": 2,
    }


def test_the_report_adds_up_means_spend_and_judging() -> None:
    report = EvaluationReport(
        "r",
        (
            (book("a", spent=100, estimated=90), score("a", 4, judge=7)),
            (book("b", spent=50, estimated=60), score("b", 3, judge=5)),
            (book("c", finished=False, spent=25, estimated=25), None),
        ),
    )
    assert report.means() == {"voice": 3.5}
    assert (report.spent(), report.estimated(), report.judged()) == (175, 175, 12)


def test_the_means_round_to_two_places_and_there_are_none_without_a_scored_book() -> None:
    thirds = EvaluationReport(
        "r",
        tuple((book(c), score(c, v)) for c, v in (("a", 4), ("b", 4), ("c", 5))),
    )
    assert thirds.means() == {"voice": 4.33}
    assert EvaluationReport("r", ((book(finished=False), None),)).means() == {}


def test_the_expected_cost_is_unknown_when_any_book_has_no_estimate() -> None:
    report = EvaluationReport(
        "r", ((book("a", estimated=5), score("a")), (book("b", estimated=None), score("b")))
    )
    assert report.estimated() is None


def test_a_verdict_passes_when_it_has_no_reasons() -> None:
    assert EvaluationVerdict(()).passed() is True
    assert EvaluationVerdict(("x",)).passed() is False
