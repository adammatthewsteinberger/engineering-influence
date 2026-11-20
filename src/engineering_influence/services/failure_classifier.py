# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sorts a stage failure into retry, park or stop."""

from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.models.failure_kind import FailureKind
from engineering_influence.services.interfaces.failure_classifier_interface import (
    FailureClassifierInterface,
)


class FailureClassifier(FailureClassifierInterface):
    """Capacity beats transient; anything not known to be recoverable stops the run.

    A timeout or a dropped connection is transient even when no adapter wrapped it, because
    retrying is the right response to both.
    """

    def classify(self, error: BaseException) -> FailureKind:
        """Retry, park for credit, or stop."""
        if isinstance(error, CapacityExhaustedError):
            return FailureKind.CAPACITY
        if isinstance(error, TransientStageError | TimeoutError | ConnectionError):
            return FailureKind.TRANSIENT
        return FailureKind.UNRECOVERABLE
