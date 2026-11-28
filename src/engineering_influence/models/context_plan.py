# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Everything that could go into one drafting call, before it is fitted to a token budget."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.context_plan_interface import ContextPlanInterface


@dataclass(frozen=True, slots=True)
class ContextPlan(ContextPlanInterface):
    """The parts of a prompt, split by how much they can give up.

    ``style`` and ``grounding`` (the story bible, or the outline and research of a non-fiction book) hardly
    change from chapter to chapter, so they come first in the prompt and the start of every request is the
    same. ``beats`` and ``instruction`` are what this call is for and are never cut. All of it except the
    ``instruction`` came from a model or the web, and the assembler puts it in the prompt as untrusted
    blocks; the ``instruction`` is the caller's own text and holds none of that. ``prior_summaries`` run oldest first and are dropped
    oldest first; ``previous_tail`` is the end of the last chapter and is cut from its start.
    """

    style: str
    grounding: str
    beats: str
    instruction: str
    prior_summaries: tuple[str, ...] = ()
    previous_tail: str = ""

    def __post_init__(self) -> None:
        """Validate the prompt's parts when the plan is built."""
        for name in ("style", "beats", "instruction"):
            if not getattr(self, name).strip():
                raise ValueError(f"a context plan needs {name}")
        if any(not summary.strip() for summary in self.prior_summaries):
            raise ValueError("a prior chapter summary cannot be blank")
