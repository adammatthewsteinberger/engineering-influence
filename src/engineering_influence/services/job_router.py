# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Routes a queued job to the service for its kind, such as ``pipeline.*`` or ``run.*``."""

from collections.abc import Mapping

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface


class JobRouter(ProcessJobInterface):
    """The prefix before the first dot picks the handler; a kind nobody handles is refused.

    The router is itself a ``ProcessJobInterface``, so the message handler does not know
    whether it talks to one service or to several.
    """

    def __init__(self, routes: Mapping[str, ProcessJobInterface]) -> None:
        """Remember the handler for each kind of job."""
        self._routes = dict(routes)

    async def process(self, message: JobMessage) -> JobOutcome:
        """Hand the job to the service registered for its kind prefix."""
        route = self._routes.get(message.kind.split(".", 1)[0])
        if route is None:
            raise ApplicationError(
                code="UNKNOWN_JOB_KIND",
                message=f"cannot process job kind {message.kind!r}",
                http_status=422,
            )
        return await route.process(message)
