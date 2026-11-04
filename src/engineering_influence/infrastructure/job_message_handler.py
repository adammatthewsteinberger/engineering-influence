# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Settle one broker delivery: process it, then acknowledge or dead-letter it."""

import logging
from typing import Any

from pydantic import ValidationError

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.interfaces.alert_port import AlertPort
from engineering_influence.interfaces.correlation_port import CorrelationPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface

_LOGGER = logging.getLogger(__name__)


class JobMessageHandler:
    """Acknowledge a processed job; send a malformed or failing one to the dead-letter queue.

    A job is never requeued: a failure that is not the job's fault (a database outage) and
    one that is look the same here, so both stop in the dead-letter queue for a person to
    inspect and replay, with an alert, rather than retrying forever.
    """

    def __init__(
        self,
        process_job: ProcessJobInterface,
        metrics: MetricsPort,
        alerts: AlertPort,
        correlation: CorrelationPort,
    ) -> None:
        self._process_job = process_job
        self._metrics = metrics
        self._alerts = alerts
        self._correlation = correlation

    async def handle(self, message: Any) -> None:
        """``message`` needs ``body``, ``ack()`` and ``reject(requeue=...)``."""
        try:
            job = JobMessage.parse(message.body)
        except ValidationError:
            self._metrics.increment("jobs.rejected")
            _LOGGER.warning("malformed job message rejected", extra={"size": len(message.body)})
            await message.reject(requeue=False)
            return
        queued = job.payload.get("correlation_id")
        with self._correlation.scope(queued if isinstance(queued, str) else None):
            try:
                outcome = await self._process_job.process(job)
            except Exception as error:  # noqa: BLE001 - any failure must settle the delivery
                await self._fail(message, job, type(error).__name__)
                return
            self._metrics.increment("jobs.processed")
            self._metrics.increment(f"jobs.outcome.{outcome.value}")
            _LOGGER.info(
                "job processed",
                extra={"job_id": job.job_id, "kind": job.kind, "outcome": outcome.value},
            )
            await message.ack()

    async def _fail(self, message: Any, job: JobMessage, error_type: str) -> None:
        self._metrics.increment("jobs.failed")
        _LOGGER.error(
            "job failed",
            extra={"job_id": job.job_id, "kind": job.kind, "error": error_type},
        )
        self._alerts.raise_alert(
            "error",
            f"job {job.kind} failed and was dead-lettered",
            {"job_id": job.job_id, "kind": job.kind, "error": error_type},
            f"job_failed:{job.job_id}",
        )
        await message.reject(requeue=False)
