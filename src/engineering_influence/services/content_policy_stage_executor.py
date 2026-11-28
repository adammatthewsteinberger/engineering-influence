# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Refuses a stage before anything is spent when the model is not recorded as allowing the brief's levels."""

from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.content_policy_interface import (
    ContentPolicyInterface,
)


class ContentPolicyStageExecutor(StageExecutorInterface):
    """Asks the content policy first, on every stage and every attempt, then hands over to the executor it wraps.

    The check is cheap and deterministic, so it is not remembered: a run resumed after the person changed the
    brief, or the model, is judged again. A refusal is an ApplicationError (CONTENT_LEVEL_NOT_ALLOWED) that ends the run
    before any call is made.
    """

    def __init__(
        self,
        inner: StageExecutorInterface,
        policy: ContentPolicyInterface,
        model: ProviderDescriptor,
    ) -> None:
        """Remember the stage executor it wraps, the content policy and the model's descriptor."""
        self._inner = inner
        self._policy = policy
        self._model = model

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Check the brief's levels against the model, then run the stage."""
        self._policy.require(run.brief, self._model)
        return await self._inner.execute(run, attempt)
