# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The operator's ceilings on spend, in whole micro-dollars; unset means no ceiling."""

from collections.abc import Mapping
from dataclasses import dataclass

from engineering_influence.models.interfaces.spend_limits_interface import SpendLimitsInterface


@dataclass(frozen=True, slots=True)
class SpendLimits(SpendLimitsInterface):
    """What the person who runs the stack allows, whoever asks.

    ``per_run`` is the most one run's cap may ever be, at its start and after every grant. ``outstanding`` is the
    most **unspent budget** (each unfinished run's cap less what it has spent) all runs may hold together, so a client
    that starts many runs, or is granted more again and again, runs out of room instead of out of money. A ceiling
    that is not set is not enforced. A cap is a promise not to spend more; these are the promise about the promises.
    """

    PER_RUN = "EI_MAX_RUN_BUDGET_MICRO_USD"
    OUTSTANDING = "EI_MAX_OUTSTANDING_BUDGET_MICRO_USD"

    per_run: int | None = None
    outstanding: int | None = None

    def __post_init__(self) -> None:
        """Validate the limits the stack's operator allows when they are built."""
        for label, value in (("per_run", self.per_run), ("outstanding", self.outstanding)):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError(f"{label} is a whole number of micro-dollars above zero")
        if (
            self.per_run is not None
            and self.outstanding is not None
            and self.per_run > self.outstanding
        ):
            raise ValueError("one run may not be allowed more than all runs together")

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "SpendLimits":
        """The limits the environment sets; a variable that is blank or absent sets none, one that is not a whole number is refused."""
        found: dict[str, int | None] = {}
        for key, name in (("per_run", cls.PER_RUN), ("outstanding", cls.OUTSTANDING)):
            raw = environ.get(name, "").strip()
            if raw and not (raw.isdigit() and int(raw) >= 1):
                raise ValueError(f"{name} must be a whole number of micro-dollars above zero")
            found[key] = int(raw) if raw else None
        try:
            return cls(**found)
        except ValueError as error:
            raise ValueError(f"{cls.PER_RUN} and {cls.OUTSTANDING}: {error}") from error
