# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Job-processing service contract."""

from abc import ABC, abstractmethod

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome


class ProcessJobInterface(ABC):
    """Run one queued pipeline job and decide what follows it."""

    @abstractmethod
    async def process(self, message: JobMessage) -> JobOutcome:
        """Run the job's phase, record the result and enqueue the next stage."""
