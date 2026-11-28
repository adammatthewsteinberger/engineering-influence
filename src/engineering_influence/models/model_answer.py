# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a stage gets back from asking a model: an answer, or the best it could get and why not."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_answer_interface import ModelAnswerInterface
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.tool_call import ToolCall


@dataclass(frozen=True, slots=True)
class ModelAnswer(ModelAnswerInterface):
    """The text, whether it is a complete answer, and the issues recorded if it is not.

    A complete answer carries no issues. An incomplete one always carries at least one: the text
    may be cut off, or empty because the model declined, and a stage must be able to see that and
    record it. ``calls`` counts live model calls and ``cost_micro_usd`` is what they cost together;
    a replayed answer made no call and cost nothing this time. A complete answer may ask for tools
    (``tool_calls``), in which case its text may be empty.
    """

    text: str
    complete: bool
    issues: tuple[QualityIssue, ...]
    cost_micro_usd: int
    calls: int
    replayed: bool
    tool_calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        """Validate that an incomplete answer records its issues."""
        if self.complete and self.issues:
            raise ValueError("a complete answer has no issues")
        if not self.complete and not self.issues:
            raise ValueError("an incomplete answer must say what is wrong with it")
        if self.cost_micro_usd < 0 or self.calls < 0:
            raise ValueError("cost and calls cannot be negative")
        if self.tool_calls and not self.complete:
            raise ValueError("only a complete answer can ask for tools")
        if self.replayed and (not self.complete or self.cost_micro_usd or self.calls):
            raise ValueError("a replayed answer is complete, free and made no call")
