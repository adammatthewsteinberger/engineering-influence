"""Judging, the bar, the report and the runner."""

import json

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.book_maker_interface import BookMakerInterface
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_score import BookScore
from engineering_influence.models.budget import Budget
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.evaluation_report import EvaluationReport
from engineering_influence.models.evaluation_verdict import EvaluationVerdict
from engineering_influence.models.made_book import MadeBook
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.rubric import Rubric
from engineering_influence.models.rubric_dimension import RubricDimension
from engineering_influence.services.book_judge import BookJudge
from engineering_influence.services.evaluation_reporter import EvaluationReporter
from engineering_influence.services.evaluation_runner import EvaluationRunner
from engineering_influence.services.interfaces.book_judge_interface import BookJudgeInterface
from engineering_influence.services.release_gate import ReleaseGate
from engineering_influence.services.score_parser import ScoreParser
from engineering_influence.services.spend_guard import SpendGuard

ANCHORS = ((1, "bad"), (3, "fine"), (5, "great"))
RUBRIC = Rubric(
    1,
    3.5,
    0.2,
    (
        RubricDimension("voice", "Is the voice its own?", ANCHORS, ("nonfiction", "novel")),
        RubricDimension("plot", "Does it move?", ANCHORS, ("novel",)),
    ),
)
# 1 micro-USD per input token, 5 per output token; cache write 1.25.
DESCRIPTOR = ProviderDescriptor(
    provider="fake",
    model="judge-1",
    family="fake",
    context_window=10_000,
    max_output_tokens=2_000,
    input_micro_usd_per_mtok=1_000_000,
    output_micro_usd_per_mtok=5_000_000,
    cache_read_micro_usd_per_mtok=100_000,
    cache_write_micro_usd_per_mtok=1_250_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)


def verdict_json(voice: int = 4, plot: int | None = None) -> str:
    scores = {"voice": {"score": voice, "reason": "its own"}}
    if plot is not None:
        scores["plot"] = {"score": plot, "reason": "it moves"}
    return json.dumps({"scores": scores})


def said(text: str, stop: str = "end_turn", usage: ModelUsage | None = None) -> ModelResponse:
    return ModelResponse(text, usage or ModelUsage(100, 20), "judge-1-snap", stop)


class ScriptedJudgeModel(ModelInterface):
    def __init__(self, *script: ModelResponse | BaseException, counted: int = 100) -> None:
        self.script = list(script)
        self.counted = counted
        self.calls: list[ModelRequest] = []

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return self.counted

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def made(case: str = "a", kind: BookKind = BookKind.NOVEL, finished: bool = True) -> MadeBook:
    return MadeBook(
        case,
        kind,
        "completed" if finished else "failed",
        finished,
        "The Road",
        ("It began.", "It ended.") if finished else (),
        100,
        100,
    )


def judge_with(model: ScriptedJudgeModel, cap: int = 100_000) -> tuple[BookJudge, SpendGuard]:
    guard = SpendGuard(Budget(cap=cap))
    return BookJudge(model, TomlPromptLibrary(), ScoreParser(), RUBRIC, guard), guard


# ---------------------------------------------------------------- ScoreParser


def parse(text: str, names: tuple[str, ...] = ("voice",)) -> tuple[tuple[str, int, str], ...]:
    return ScoreParser().parse(text, names)


def invalid(text: str, names: tuple[str, ...] = ("voice",)) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        parse(text, names)
    assert error.value.code == "JUDGE_ANSWER_INVALID" and error.value.http_status == 502
    return error.value


def test_the_parser_reads_every_score_in_the_order_the_rubric_gives() -> None:
    text = json.dumps(
        {
            "scores": {
                "plot": {"score": 2, "reason": "slow\n  middle"},
                "voice": {"score": 5, "reason": "its own"},
            }
        }
    )
    assert parse(text, ("voice", "plot")) == (("voice", 5, "its own"), ("plot", 2, "slow middle"))


def test_the_parser_ignores_a_preamble_and_a_code_fence() -> None:
    text = f"Here you go:\n```json\n{verdict_json(3)}\n```\nHope that helps {{x}}"
    assert parse(text) == (("voice", 3, "its own"),)


@pytest.mark.parametrize("score", [1, 5])
def test_the_ends_of_the_scale_are_accepted(score: int) -> None:
    assert parse(verdict_json(score))[0][1] == score


@pytest.mark.parametrize("score", [0, 6, 4.5, "4", True, None, -1])
def test_a_score_off_the_scale_or_not_whole_is_refused(score: object) -> None:
    text = json.dumps({"scores": {"voice": {"score": score, "reason": "r"}}})
    assert "voice" in invalid(text).message


@pytest.mark.parametrize("reason", ["", "   ", None, 3])
def test_a_score_without_its_reason_is_refused(reason: object) -> None:
    text = json.dumps({"scores": {"voice": {"score": 4, "reason": reason}}})
    assert "reason" in invalid(text).message


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("no json here", "no JSON object"),
        ("{not json", "not valid JSON"),
        (json.dumps({"other": 1}), "no ``scores`` object"),
        (json.dumps({"scores": [1]}), "no ``scores`` object"),
        (json.dumps({"scores": {"voice": 4}}), "not an object"),
        (json.dumps({"scores": {}}), "missing ['voice']"),
        (
            json.dumps({"scores": {"voice": {"score": 4, "reason": "r"}, "extra": {}}}),
            "unknown ['extra']",
        ),
    ],
)
def test_an_answer_that_cannot_be_used_says_why(text: str, why: str) -> None:
    assert why in invalid(text).message


# ------------------------------------------------------------------ BookJudge


def test_the_judge_scores_a_book_on_the_dimensions_of_its_kind_and_pays_for_it() -> None:
    model = ScriptedJudgeModel(said(verdict_json(4, 2)))
    judge, guard = judge_with(model)
    score = judge.judge(made(kind=BookKind.NOVEL))
    assert isinstance(judge, BookJudgeInterface)
    assert score == BookScore("a", (("voice", 4, "its own"), ("plot", 2, "it moves")), 200)
    (request,) = model.calls
    assert request.prompt_version == "eval_judge@1"
    assert request.max_output_tokens == 300 + 150 * 2
    assert "novel" in request.prompt and "plot: Does it move?" in request.prompt
    assert (
        "<untrusted" in request.prompt
        and "# The Road" in request.prompt
        and "It ended." in request.prompt
    )
    assert "accuracy" not in request.prompt
    assert guard.budget().spent == 200 and guard.budget().reserved == 0


def test_a_nonfiction_book_is_not_asked_about_plot() -> None:
    model = ScriptedJudgeModel(said(verdict_json(4)))
    judge, _ = judge_with(model)
    judge.judge(made(kind=BookKind.NONFICTION))
    assert "plot" not in model.calls[0].prompt and "non-fiction book" in model.calls[0].prompt


def test_an_unreadable_answer_is_asked_for_once_more_and_both_calls_are_paid() -> None:
    model = ScriptedJudgeModel(said("I think it is good."), said(verdict_json(5)))
    judge, guard = judge_with(model)
    score = judge.judge(made(kind=BookKind.NONFICTION))
    assert score.by_name() == {"voice": 5} and score.judge_micro_usd == 400
    assert len(model.calls) == 2 and guard.budget().spent == 400


def test_two_unreadable_answers_fail_with_the_parsers_reason() -> None:
    model = ScriptedJudgeModel(said("nope"), said("still nope"))
    judge, _ = judge_with(model)
    with pytest.raises(ApplicationError) as error:
        judge.judge(made(kind=BookKind.NONFICTION))
    assert error.value.code == "JUDGE_ANSWER_INVALID" and len(model.calls) == 2


def test_an_answer_cut_off_is_not_read_and_two_of_them_fail() -> None:
    model = ScriptedJudgeModel(
        said(verdict_json(4), "max_tokens"), said(verdict_json(4), "max_tokens")
    )
    judge, _ = judge_with(model)
    with pytest.raises(ApplicationError) as error:
        judge.judge(made(kind=BookKind.NONFICTION))
    assert error.value.code == "JUDGE_ANSWER_UNUSABLE" and "max_tokens" in error.value.message
    assert len(model.calls) == 2


def test_a_cut_off_answer_followed_by_a_good_one_is_scored() -> None:
    model = ScriptedJudgeModel(said("{", "max_tokens"), said(verdict_json(2)))
    judge, _ = judge_with(model)
    assert judge.judge(made(kind=BookKind.NONFICTION)).by_name() == {"voice": 2}


def test_a_book_too_big_for_the_judges_window_is_refused_before_anything_is_sent() -> None:
    # 100 + max output (300 + 150) just over a window of 10,000 once the book takes 9,551 tokens.
    model = ScriptedJudgeModel(counted=10_000 - 450 + 1)
    judge, guard = judge_with(model)
    with pytest.raises(ApplicationError) as error:
        judge.judge(made(kind=BookKind.NONFICTION))
    assert error.value.code == "JUDGE_INPUT_TOO_LARGE" and error.value.http_status == 422
    assert model.calls == [] and guard.budget().spent == 0


def test_a_book_that_exactly_fits_the_window_is_judged() -> None:
    model = ScriptedJudgeModel(said(verdict_json(3)), counted=10_000 - 450)
    judge, _ = judge_with(model, cap=100_000)
    assert judge.judge(made(kind=BookKind.NONFICTION)).by_name() == {"voice": 3}


def test_judging_never_spends_past_its_budget_and_sends_nothing_it_cannot_afford() -> None:
    model = ScriptedJudgeModel()
    judge, guard = judge_with(model, cap=100)
    with pytest.raises(ApplicationError) as error:
        judge.judge(made(kind=BookKind.NONFICTION))
    assert error.value.code == "JUDGE_BUDGET_EXHAUSTED" and error.value.http_status == 422
    assert model.calls == [] and guard.budget().spent == 0


def test_a_retry_that_does_not_fit_the_budget_stops_there() -> None:
    # A call reserves 100 * 1.25 + 450 * 5 = 2,375 and the first really costs 200; 2,575 does not fit in 2,500.
    model = ScriptedJudgeModel(said("nope"))
    judge, guard = judge_with(model, cap=2_500)
    with pytest.raises(ApplicationError) as error:
        judge.judge(made(kind=BookKind.NONFICTION))
    assert error.value.code == "JUDGE_BUDGET_EXHAUSTED"
    assert len(model.calls) == 1 and guard.budget().reserved == 0


def test_a_call_that_fails_releases_what_it_reserved() -> None:
    model = ScriptedJudgeModel(RuntimeError("network"))
    judge, guard = judge_with(model)
    with pytest.raises(RuntimeError):
        judge.judge(made(kind=BookKind.NONFICTION))
    assert guard.budget().reserved == 0 and guard.budget().spent == 0


# ---------------------------------------------------------------- ReleaseGate


def report(
    *scores: int,
    spent: int = 100,
    estimated: int | None = 100,
    unfinished: bool = False,
) -> EvaluationReport:
    results: list[tuple[MadeBook, BookScore | None]] = []
    for index, value in enumerate(scores):
        case = f"c{index}"
        book = MadeBook(case, BookKind.NONFICTION, "completed", True, "T", ("x",), spent, estimated)
        results.append((book, BookScore(case, (("voice", value, "r"),), 1)))
    if unfinished:
        results.append(
            (MadeBook("late", BookKind.NONFICTION, "failed", False, "T", (), 0, 0), None)
        )
    return EvaluationReport("r", tuple(results))


def check(result: EvaluationReport, baseline: dict[str, float] | None = None) -> EvaluationVerdict:
    return ReleaseGate().verdict(result, RUBRIC, baseline)


def test_a_release_that_clears_every_bar_passes() -> None:
    assert check(report(4, 4), {"voice": 4.0}).failures == ()


def test_the_pass_mark_is_inclusive() -> None:
    assert check(report(3, 4)).passed() is True
    below = check(report(3, 3, 4))  # mean 3.33
    assert below.failures == ("voice: the mean 3.33 is below the pass mark 3.5",)


def test_a_book_that_did_not_finish_fails_the_release_even_if_the_rest_are_good() -> None:
    result = check(report(5, 5, unfinished=True))
    assert result.failures == ("late: the book was not finished (failed)",)


def test_a_drop_of_exactly_the_allowed_amount_is_tolerated_and_more_is_not() -> None:
    assert check(report(4), {"voice": 4.2}).passed() is True
    worse = check(report(4), {"voice": 4.25})
    assert worse.failures == ("voice: the mean fell from 4.25 to 4.0, more than the allowed 0.2",)


def test_a_rise_against_the_baseline_is_not_a_failure() -> None:
    assert check(report(5), {"voice": 3.6}).passed() is True


def test_a_dimension_the_baseline_had_and_this_evaluation_did_not_measure_fails() -> None:
    assert check(report(4), {"voice": 4.0, "plot": 4.0}).failures == (
        "plot: the baseline measured it and this evaluation did not",
    )


def test_no_baseline_means_only_the_pass_mark_applies() -> None:
    assert check(report(4), None).passed() is True
    assert check(report(4), {}).passed() is True


def test_the_estimate_may_be_off_by_the_tolerance_and_no_more() -> None:
    assert ReleaseGate.ESTIMATE_TOLERANCE_PERCENT == 30
    assert check(report(4, spent=100, estimated=70)).passed() is True
    assert check(report(4, spent=100, estimated=130)).passed() is True
    low = check(report(4, spent=100, estimated=69)).failures
    high = check(report(4, spent=100, estimated=131)).failures
    assert len(low) == len(high) == 1 and "31% off" in low[0] and "31% off" in high[0]
    assert "69 micro-USD against 100 spent" in low[0]


def test_an_estimate_is_judged_over_the_whole_set_not_book_by_book() -> None:
    result = EvaluationReport(
        "r",
        (
            (
                MadeBook("a", BookKind.NONFICTION, "completed", True, "T", ("x",), 100, 50),
                BookScore("a", (("voice", 4, "r"),), 0),
            ),
            (
                MadeBook("b", BookKind.NONFICTION, "completed", True, "T", ("x",), 100, 150),
                BookScore("b", (("voice", 4, "r"),), 0),
            ),
        ),
    )
    assert check(result).passed() is True


def test_money_spent_without_an_estimate_cannot_be_checked_and_fails() -> None:
    assert check(report(4, spent=10, estimated=None)).failures == (
        "no cost estimate was recorded for some book, so its accuracy cannot be checked",
    )


def test_nothing_spent_means_nothing_to_compare() -> None:
    assert check(report(4, spent=0, estimated=None)).passed() is True


# ---------------------------------------------------------- EvaluationReporter


def test_the_report_is_stable_json_that_is_its_own_baseline() -> None:
    result = EvaluationReport(
        "1.0.0",
        (
            (made("a", BookKind.NONFICTION), BookScore("a", (("voice", 4, "own"),), 9)),
            (made("b", BookKind.NONFICTION, finished=False), None),
        ),
    )
    gate = EvaluationVerdict(("b: the book was not finished (failed)",))
    rendered = EvaluationReporter().render(result, gate, RUBRIC)
    assert rendered == EvaluationReporter().render(result, gate, RUBRIC) and rendered.endswith(
        b"\n"
    )
    data = json.loads(rendered)
    assert data["schema_version"] == 1 and data["release"] == "1.0.0"
    assert (data["rubric_version"], data["pass_mean"], data["max_drop"]) == (1, 3.5, 0.2)
    assert data["dimension_means"] == {"voice": 4.0}
    assert data["spend"] == {
        "making_micro_usd": 200,
        "estimated_micro_usd": 200,
        "estimate_error_percent": 0.0,
        "judging_micro_usd": 9,
    }
    assert data["verdict"] == {"passed": False, "failures": list(gate.failures)}
    first, second = data["cases"]
    assert first["scores"] == [{"dimension": "voice", "score": 4, "reason": "own"}]
    assert (first["chapters"], first["words"], first["finished"]) == (2, 4, True)
    assert (second["scores"], second["finished"], second["chapters"]) == ([], False, 0)
    assert list(data) == sorted(data)


def test_the_estimate_error_is_unknown_without_an_estimate_or_spend() -> None:
    def error_of(spent: int, estimated: int | None) -> object:
        book = MadeBook("a", BookKind.NONFICTION, "completed", True, "T", ("x",), spent, estimated)
        result = EvaluationReport("r", ((book, BookScore("a", (("voice", 4, "r"),), 0)),))
        return json.loads(EvaluationReporter().render(result, EvaluationVerdict(()), RUBRIC))[
            "spend"
        ]["estimate_error_percent"]

    assert error_of(100, None) is None
    assert error_of(0, 0) is None
    assert error_of(100, 125) == 25.0
    assert error_of(3, 4) == 33.3


def test_non_ascii_is_written_as_it_is() -> None:
    book = MadeBook("a", BookKind.NONFICTION, "completed", True, "Café", ("x",), 1, 1)
    result = EvaluationReport("r", ((book, BookScore("a", (("voice", 4, "r"),), 0)),))
    assert "Café".encode() in EvaluationReporter().render(result, EvaluationVerdict(()), RUBRIC)


# ----------------------------------------------------------- EvaluationRunner


class ScriptedMaker(BookMakerInterface):
    def __init__(self, books: dict[str, MadeBook]) -> None:
        self.books = books
        self.made: list[tuple[str, int]] = []

    def make(self, case: EvaluationCase, budget_micro_usd: int) -> MadeBook:
        self.made.append((case.name, budget_micro_usd))
        return self.books[case.name]


class ScriptedJudge(BookJudgeInterface):
    def __init__(self, fail_on: str | None = None) -> None:
        self.seen: list[str] = []
        self.fail_on = fail_on

    def judge(self, book: MadeBook) -> BookScore:
        self.seen.append(book.case)
        if book.case == self.fail_on:
            raise ApplicationError(code="JUDGE_ANSWER_INVALID", message="no", http_status=502)
        return BookScore(book.case, (("voice", 4, "r"), ("plot", 3, "r")), 2)


def cases(*names: str) -> tuple[EvaluationCase, ...]:
    return tuple(EvaluationCase(name, BookKind.NOVEL, f"idea {name}") for name in names)


def test_the_runner_makes_each_case_in_order_judges_the_finished_ones_and_narrates() -> None:
    maker = ScriptedMaker({"a": made("a"), "b": made("b", finished=False)})
    judge = ScriptedJudge()
    lines: list[str] = []
    result = EvaluationRunner(maker, judge).run("rel", cases("a", "b"), 7_000_000, lines.append)
    assert maker.made == [("a", 7_000_000), ("b", 7_000_000)] and judge.seen == ["a"]
    assert [(book.case, score is not None) for book, score in result.results] == [
        ("a", True),
        ("b", False),
    ]
    assert result.release == "rel"
    assert lines == [
        "a: making",
        "a: judging",
        "a: voice 4, plot 3",
        "b: making",
        "b: not finished (failed)",
    ]


def test_a_judge_that_fails_stops_the_evaluation_rather_than_skip_a_book() -> None:
    maker = ScriptedMaker({"a": made("a"), "b": made("b")})
    with pytest.raises(ApplicationError):
        EvaluationRunner(maker, ScriptedJudge(fail_on="a")).run("r", cases("a", "b"), 1, print)
    assert maker.made == [("a", 1)]
