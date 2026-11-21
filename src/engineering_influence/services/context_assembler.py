# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fit one drafting call's context into a token budget."""

from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.assembled_context import AssembledContext
from engineering_influence.models.context_plan import ContextPlan
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.services.interfaces.context_assembler_interface import (
    ContextAssemblerInterface,
)


class ContextAssembler(ContextAssemblerInterface):
    """Keep everything that must be there, then spend what is left on history.

    Policy, in order: the style, the grounding, the beats and the instruction are never cut.
    Then as many of the *newest* prior-chapter summaries as fit (plot facts outrank prose), then
    the end of the previous chapter in whatever room remains, up to ``max_tail_characters``.
    The stable prefix (style and grounding) goes in ``system``, so the adapter can cache it; the
    parts that change from call to call go in the prompt. When no summary is kept the section
    is left out altogether, so a budget that fits the fixed parts always fits; the omission is
    reported in ``omitted_summaries`` instead. Fitting binary-searches the model's own
    token counter, so a draft costs a few dozen counting calls however long the book is.
    """

    OMITTED_NOTE = "({count} earlier chapter summaries left out to fit.)"

    def __init__(
        self, model: ModelInterface, prompt_version: str, max_tail_characters: int = 4000
    ) -> None:
        if not prompt_version.strip():
            raise ValueError("a context assembler needs a prompt version")
        if max_tail_characters < 0:
            raise ValueError("the tail limit cannot be negative")
        self._model = model
        self._prompt_version = prompt_version
        self._max_tail = max_tail_characters

    def assemble(self, plan: ContextPlan, max_input_tokens: int) -> AssembledContext:
        """The fullest prompt that fits, or an ApplicationError when the fixed parts do not."""
        system = self._system(plan)
        base = self._count(system, self._prompt(plan, 0, ""))
        if base > max_input_tokens:
            raise ApplicationError(
                code="CONTEXT_TOO_LARGE",
                message=(
                    f"the style, grounding, beats and instruction alone need {base} input tokens "
                    f"and only {max_input_tokens} are available; shorten them or use a model "
                    "with a larger window"
                ),
                http_status=422,
            )
        total = len(plan.prior_summaries)
        # Dropping any summary adds the "left out" note, so cost is not monotone in the count
        # kept: all of them may fit where all but one do not. Test "all" first, then search the rest.
        if self._fits(plan, system, total, "", max_input_tokens):
            kept = total
        else:
            kept = self._largest(
                0, total - 1, lambda n: self._fits(plan, system, n, "", max_input_tokens)
            )
        tail_limit = min(len(plan.previous_tail), self._max_tail)
        chars = self._largest(
            0,
            tail_limit,
            lambda c: self._fits(
                plan, system, kept, self._tail(plan.previous_tail, c), max_input_tokens
            ),
        )
        tail = self._tail(plan.previous_tail, chars)
        prompt = self._prompt(plan, kept, tail)
        return AssembledContext(
            system=system,
            prompt=prompt,
            input_tokens=self._count(system, prompt),
            kept_summaries=kept,
            omitted_summaries=total - kept,
            tail_characters=len(tail),
        )

    @staticmethod
    def _largest(low: int, high: int, ok: Callable[[int], bool]) -> int:
        """The largest n in [low, high] for which ``ok(n)`` holds, given that ok(low) does."""
        while low < high:
            middle = (low + high + 1) // 2
            if ok(middle):
                low = middle
            else:
                high = middle - 1
        return low

    def _fits(self, plan: ContextPlan, system: str, summaries: int, tail: str, limit: int) -> bool:
        return self._count(system, self._prompt(plan, summaries, tail)) <= limit

    def _count(self, system: str, prompt: str) -> int:
        request = ModelRequest(
            system=system, prompt=prompt, max_output_tokens=1, prompt_version=self._prompt_version
        )
        return self._model.count_tokens(request)

    @staticmethod
    def _system(plan: ContextPlan) -> str:
        parts = [plan.style.strip(), plan.grounding.strip()]
        return "\n\n".join(part for part in parts if part)

    def _prompt(self, plan: ContextPlan, summaries: int, tail: str) -> str:
        total = len(plan.prior_summaries)
        sections: list[str] = []
        if summaries:
            lines = [self.OMITTED_NOTE.format(count=total - summaries)] if summaries < total else []
            lines += [
                f"- {summary.strip()}" for summary in plan.prior_summaries[total - summaries :]
            ]
            sections.append("## Earlier chapters\n" + "\n".join(lines))
        if tail:
            sections.append("## End of the previous chapter\n" + tail)
        sections.append("## Beats for this chapter\n" + plan.beats.strip())
        sections.append(plan.instruction.strip())
        return "\n\n".join(sections)

    @staticmethod
    def _tail(text: str, characters: int) -> str:
        """The last ``characters`` of the text, moved forward to start on a clean boundary."""
        if characters <= 0:
            return ""
        if characters >= len(text):
            return text.strip()
        piece = text[-characters:]
        paragraph = piece.find("\n\n")
        if paragraph != -1:
            return piece[paragraph:].strip()
        space = next((i for i, ch in enumerate(piece) if ch.isspace()), -1)
        return piece[space:].strip() if space != -1 else ""
