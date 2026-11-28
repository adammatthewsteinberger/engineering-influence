# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Handles ``run.advance`` jobs: checks the payload and hands it to the run advancer."""

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface


class ProcessRunJob(ProcessJobInterface):
    """Payload ``{run_id, stage, attempt}``; any other keys, such as a correlation id, are ignored.

    Every ``AdvanceOutcome`` has a ``JobOutcome`` named ``run_<outcome>``, which is what the
    worker's metrics count.
    """

    def __init__(self, advance: AdvanceRunInterface) -> None:
        """Remember the service that advances the run."""
        self._advance = advance

    async def process(self, message: JobMessage) -> JobOutcome:
        """Validate the message, advance the run and report what happened."""
        if message.kind != AdvanceRun.KIND:
            raise ApplicationError(
                code="UNKNOWN_JOB_KIND",
                message=f"cannot process job kind {message.kind!r}",
                http_status=422,
            )
        run_id, stage, attempt = self._payload(message)
        outcome = await self._advance.advance(run_id, stage, attempt)
        return JobOutcome(f"run_{outcome.value}")

    @staticmethod
    def _payload(message: JobMessage) -> tuple[str, str, int]:
        run_id = message.payload.get("run_id")
        stage = message.payload.get("stage")
        attempt = message.payload.get("attempt")
        valid = (
            isinstance(run_id, str)
            and bool(run_id.strip())
            and isinstance(stage, str)
            and bool(stage.strip())
            and isinstance(attempt, int)
            and not isinstance(attempt, bool)
            and attempt >= 1
        )
        if not valid:
            raise ApplicationError(
                code="INVALID_JOB_PAYLOAD",
                message="run.advance needs a run_id, a stage and an attempt of at least 1",
                http_status=422,
            )
        return str(run_id), str(stage), int(str(attempt))
