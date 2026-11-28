# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Scores a finished book with a model, inside a budget."""

from collections.abc import Mapping
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.models.book_score import BookScore
from engineering_influence.models.made_book import MadeBook
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.rubric import Rubric
from engineering_influence.services.interfaces.book_judge_interface import BookJudgeInterface
from engineering_influence.services.interfaces.score_parser_interface import ScoreParserInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class BookJudge(BookJudgeInterface):
    """One call per book, with the whole book in it; a second call only if the first answer cannot be read.

    Every call reserves its worst case from the evaluation's judging budget before it is made (the same
    ``SpendGuard`` the writing stages use), so judging can never spend past the limit it was given: a call that does
    not fit is refused (``JUDGE_BUDGET_EXHAUSTED``) having sent nothing. A book too long for the judge's window is
    refused (``JUDGE_INPUT_TOO_LARGE``) rather than cut, because a judge that read half a book scores half a book.
    The judge sees only the text: not the brief, the run's cost, or any earlier score.
    """

    ATTEMPTS = 2
    ANSWER_BASE_TOKENS = 300
    ANSWER_TOKENS_PER_DIMENSION = 150
    LABELS: ClassVar[Mapping[str, str]] = {
        "nonfiction": "non-fiction book",
        "novel": "novel",
        "screenplay": "screenplay",
    }

    def __init__(
        self,
        model: ModelInterface,
        prompts: PromptLibraryInterface,
        parser: ScoreParserInterface,
        rubric: Rubric,
        guard: SpendGuardInterface,
    ) -> None:
        self._model = model
        self._prompts = prompts
        self._parser = parser
        self._rubric = rubric
        self._guard = guard

    def judge(self, book: MadeBook) -> BookScore:
        """The book's score on every dimension that applies to its kind, and what judging it cost."""
        kind = book.kind.value
        names = tuple(dimension.name for dimension in self._rubric.for_kind(kind))
        template = self._prompts.get("eval_judge")
        request = ModelRequest(
            system=template.render("system"),
            prompt=template.render(
                "user",
                {
                    "kind": self.LABELS[kind],
                    "rubric": self._rubric.render(kind),
                    "book": book.text(),
                },
            ),
            max_output_tokens=self.ANSWER_BASE_TOKENS
            + self.ANSWER_TOKENS_PER_DIMENSION * len(names),
            prompt_version=template.identifier(),
        )
        descriptor = self._model.describe()
        tokens = self._model.count_tokens(request)
        if tokens + request.max_output_tokens > descriptor.context_window:
            raise ApplicationError(
                code="JUDGE_INPUT_TOO_LARGE",
                message=f"{book.case}: the book is {tokens} tokens and the judge's window is "
                f"{descriptor.context_window}; use a judge with a larger window",
                http_status=422,
            )
        spent = 0
        failure = ApplicationError(
            code="JUDGE_ANSWER_UNUSABLE",
            message=f"{book.case}: no answer was obtained",
            http_status=502,
        )
        for _ in range(self.ATTEMPTS):
            reserved = descriptor.worst_case_micro_usd(tokens, request.max_output_tokens)
            try:
                self._guard.reserve(reserved)
            except BudgetExceededError as error:
                raise ApplicationError(
                    code="JUDGE_BUDGET_EXHAUSTED",
                    message=f"{book.case}: judging needs up to {reserved} micro-USD more than the judging budget has left",
                    http_status=422,
                ) from error
            try:
                response = self._model.complete(request)
            except BaseException:
                self._guard.release(reserved)
                raise
            actual = descriptor.cost_micro_usd(response.usage)
            self._guard.settle(reserved, actual)
            spent += actual
            if response.stop_reason != "end_turn":
                failure = ApplicationError(
                    code="JUDGE_ANSWER_UNUSABLE",
                    message=f"{book.case}: the judge stopped with {response.stop_reason!r} before it finished",
                    http_status=502,
                )
                continue
            try:
                return BookScore(book.case, self._parser.parse(response.text, names), spent)
            except ApplicationError as error:
                failure = error
        raise failure
